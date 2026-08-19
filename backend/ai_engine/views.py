from rest_framework.views import APIView
from rest_framework import serializers
from common.response import ok, fail
from papers.models import Paper
from reader.models import GlossaryTerm
from .models import AIConversation, AIMessage


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ('id', 'role', 'content', 'created_at')


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = ('id', 'paper', 'title', 'messages', 'created_at', 'updated_at')


def _cfg(user):
    pref = getattr(user, 'preference', None)
    return pref.translate_config if pref else None


class SummarizePaperView(APIView):
    def post(self, request):
        from services.deepseek import summarize_paper
        paper_id = request.data.get('paper')
        paper = Paper.objects.filter(user=request.user, id=paper_id).first()
        if not paper:
            return fail('论文不存在')
        body = ''
        if paper.content_json:
            parts = []
            for para in paper.content_json[:40]:
                en = (para.get('en') or '').strip()
                zh = (para.get('zh') or '').strip()
                if en and zh:
                    parts.append(f'{en}\n{zh}')
                else:
                    parts.append(en or zh)
            body = '\n\n'.join(x for x in parts if x)
        abs_text = paper.abstract or ''
        if paper.abstract_zh:
            abs_text = f'{abs_text}\n中文摘要: {paper.abstract_zh}'
        result = summarize_paper(
            paper.title, abs_text, body, user_config=_cfg(request.user),
        )
        paper.ai_summary = result
        paper.save(update_fields=['ai_summary'])
        # persist glossary
        for g in result.get('glossary') or []:
            en = g.get('en') if isinstance(g, dict) else (g[0] if g else None)
            zh = g.get('zh') if isinstance(g, dict) else (g[1] if len(g) > 1 else '')
            desc = g.get('desc') if isinstance(g, dict) else (g[2] if len(g) > 2 else '')
            if en and zh:
                GlossaryTerm.objects.update_or_create(
                    user=request.user, term_en=en,
                    defaults={'term_zh': zh, 'description': desc, 'source_paper': paper},
                )
        return ok(result)


class AskView(APIView):
    def post(self, request):
        from services.deepseek import ask_paper
        paper_id = request.data.get('paper')
        question = (request.data.get('question') or '').strip()
        conversation_id = request.data.get('conversation_id')
        if not question:
            return fail('问题不能为空')
        paper = Paper.objects.filter(user=request.user, id=paper_id).first() if paper_id else None
        if conversation_id:
            conv = AIConversation.objects.filter(id=conversation_id, user=request.user).first()
        else:
            conv = AIConversation.objects.create(
                user=request.user, paper=paper, title=question[:50],
            )
        if not conv:
            return fail('会话不存在')
        AIMessage.objects.create(conversation=conv, role='user', content=question)
        msgs = list(conv.messages.order_by('created_at').values('role', 'content'))
        history = msgs[:-1] if len(msgs) > 1 else []
        context = ''
        if paper:
            context = f'{paper.title}\n{paper.abstract or ""}\n'
            if paper.content_json:
                context += '\n'.join(p.get('en', '') for p in paper.content_json[:30])
        answer = ask_paper(question, context, history=history, user_config=_cfg(request.user))
        AIMessage.objects.create(conversation=conv, role='assistant', content=answer)
        return ok({
            'conversation_id': conv.id,
            'answer': answer,
            'messages': MessageSerializer(conv.messages.all(), many=True).data,
        })


class GenerateIntroView(APIView):
    def post(self, request):
        from services.deepseek import generate_intro
        title = request.data.get('title', '')
        abstract = request.data.get('abstract', '')
        intro = generate_intro(title, abstract, user_config=_cfg(request.user))
        return ok({'intro': intro})


class TestEngineView(APIView):
    def post(self, request):
        engine = request.data.get('engine', 'translate')  # translate / ocr
        if engine == 'ocr':
            from services.ocr_service import test_ocr_connection
            url = request.data.get('url') or (request.user.preference.ocr_config or {}).get('url')
            return ok(test_ocr_connection(url))
        from services.deepseek import test_translate_connection
        cfg = request.data.get('config') or _cfg(request.user)
        return ok(test_translate_connection(cfg))


class ConversationListView(APIView):
    def get(self, request):
        paper_id = request.query_params.get('paper')
        qs = AIConversation.objects.filter(user=request.user)
        if paper_id:
            qs = qs.filter(paper_id=paper_id)
        return ok(ConversationSerializer(qs[:20], many=True).data)
