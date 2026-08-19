from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, UserPreference
from accounts.serializers import DEFAULT_SOURCES, DEFAULT_CATEGORIES
from papers.models import Category, UserSource, Paper
from graph.models import GraphNode, GraphEdge
from reader.models import GlossaryTerm, PaperNote


DEMO_PAPERS = [
    {
        'title': 'Attention Is All You Need',
        'title_zh': '注意力就是你所需要的一切',
        'authors': 'Ashish Vaswani, Noam Shazeer, Niki Parmar, et al.',
        'venue': 'NeurIPS 2017', 'year': 2017,
        'doi': '10.48550/arXiv.1706.03762', 'arxiv_id': '1706.03762',
        'intro': '提出纯注意力架构 Transformer，奠定现代大模型基础。',
        'tags': 'Transformer,NLP,深度学习', 'status': '在读', 'starred': True,
        'cites': 128000, 'read_progress': 60, 'cat': 'Transformer',
        'abstract': 'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms...',
        'ai_summary': {
            'core': '用纯注意力机制取代循环/卷积，实现并行化长程依赖建模。',
            'problem': 'RNN 无法并行、长距离依赖易丢失。',
            'method': ['多头自注意力', '位置编码', '残差+LayerNorm'],
            'result': 'WMT 英德 28.4 BLEU',
            'limit': '自注意力 O(n²) 复杂度',
            'insight': '开启预训练大模型时代',
        },
        'content_json': [
            {'en': 'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.', 'zh': '我们提出一种全新的简单网络架构——Transformer，完全基于注意力机制，彻底摒弃了循环与卷积结构。', 'section': 'Abstract', 'section_id': 's1'},
            {'en': 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder.', 'zh': '主流序列转换模型基于复杂的循环或卷积神经网络，包含编码器与解码器。', 'section': 'Introduction', 'section_id': 's2'},
            {'en': 'Attention mechanisms have become an integral part of compelling sequence modeling and transduction models in various tasks.', 'zh': '注意力机制已成为各类序列建模与转换任务中不可或缺的部分。', 'section': 'Background', 'section_id': 's3'},
        ],
        'outline': [
            {'id': 's1', 'title': 'Abstract', 'para_index': 0},
            {'id': 's2', 'title': 'Introduction', 'para_index': 1},
            {'id': 's3', 'title': 'Background', 'para_index': 2},
        ],
    },
    {
        'title': 'PP-OCR: A Practical Ultra Lightweight OCR System',
        'title_zh': 'PP-OCR：实用超轻量 OCR 系统',
        'authors': 'Yuning Du, Chenxia Li, Ruoyu Guo, et al.',
        'venue': 'arXiv 2020', 'year': 2020,
        'doi': '10.48550/arXiv.2009.09941', 'arxiv_id': '2009.09941',
        'intro': '超轻量三段式 OCR，模型仅 3.5M，CPU 实时。',
        'tags': 'OCR,PP-OCR,轻量', 'status': '在读', 'starred': True,
        'cites': 7200, 'read_progress': 80, 'cat': 'OCR',
        'abstract': 'We propose a practical ultra lightweight OCR system, i.e., PP-OCR...',
        'ai_summary': {
            'core': '面向真实场景的端到端轻量 OCR：检测+方向分类+识别。',
            'problem': '学术方案精度高但部署难。',
            'method': ['DB 检测', '方向分类', 'CRNN/SVTR 识别'],
            'result': '模型 3.5M，CPU 实时',
            'limit': '复杂版面支持有限',
            'insight': '工程化 OCR 的典范',
        },
        'content_json': [
            {'en': 'We propose a practical ultra lightweight OCR system composed of text detection, recognition and angle classification.', 'zh': '我们提出由文本检测、识别与方向分类组成的实用超轻量 OCR 系统。', 'section': 'Abstract', 'section_id': 's1'},
        ],
        'outline': [{'id': 's1', 'title': 'Abstract', 'para_index': 0}],
    },
]


class Command(BaseCommand):
    help = 'Seed demo user and sample papers'

    @transaction.atomic
    def handle(self, *args, **options):
        email = 'demo@papermind.local'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': '王工',
                'role': '技术负责人',
                'avatar': '🦉',
                'research_direction': 'AI视觉识别、OCR、考试防作弊',
                'id_card': '110101199001011234',
            },
        )
        if created:
            user.set_password('demo123456')
            user.is_staff = True
            user.save()
            UserPreference.objects.create(
                user=user,
                translate_engine='newapi',
                translate_config={
                    'provider': 'newapi',
                    '_type': 'newapi_channel_conn',
                    'url': 'https://llm.talkweb.com.cn',
                    'api_key': '',
                    'model': 'deepseek-v4-flash',
                    'timeout': 60,
                },
                ocr_engine='paddleocr',
                ocr_config={'provider': 'paddleocr', 'url': 'http://127.0.0.1:8866', 'timeout': 60},
            )
            for i, name in enumerate(DEFAULT_CATEGORIES):
                Category.objects.create(user=user, name=name, sort=i, is_system=True)
            for name, url, icon, sort in DEFAULT_SOURCES:
                UserSource.objects.create(
                    user=user, name=name, url=url, icon=icon,
                    source_type='builtin', is_default=True, sort=sort,
                )
            self.stdout.write(self.style.SUCCESS(f'Created demo user {email} / demo123456'))
        else:
            pref, _ = UserPreference.objects.get_or_create(user=user)
            pref.translate_engine = 'newapi'
            pref.translate_config = {
                'provider': 'newapi',
                '_type': 'newapi_channel_conn',
                'url': 'https://llm.talkweb.com.cn',
                'api_key': '',
                'model': 'deepseek-v4-flash',
                'timeout': 60,
            }
            pref.save()
            self.stdout.write('Demo user already exists (translate config synced)')
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])

        cats = {c.name: c for c in Category.objects.filter(user=user)}
        for item in DEMO_PAPERS:
            if Paper.objects.filter(user=user, arxiv_id=item['arxiv_id']).exists():
                continue
            cat = cats.get(item.pop('cat'))
            arxiv_id = item.get('arxiv_id')
            pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf' if arxiv_id else None
            paper = Paper.objects.create(
                user=user, category=cat, source_type='arxiv',
                pdf_url=pdf_url, cover_url=pdf_url, **item,
            )
            PaperNote.objects.create(
                user=user, paper=paper,
                note_text='演示公开笔记：这篇论文值得团队共读。',
                ai_summary=paper.ai_summary.get('core') if paper.ai_summary else '',
                visibility='public', source='selection', para_index=0,
                sel_text=(paper.content_json or [{}])[0].get('en', '')[:200],
            )
            if paper.tags:
                for tag in paper.tags.split(','):
                    GlossaryTerm.objects.get_or_create(
                        user=user, term_en=tag.strip(),
                        defaults={'term_zh': tag.strip(), 'source_paper': paper},
                    )
            node, _ = GraphNode.objects.get_or_create(
                user=user, paper=paper, node_type='paper',
                defaults={
                    'label': paper.title, 'year': paper.year, 'cites': paper.cites,
                    'tags': paper.tags, 'read_status': True, 'description': paper.intro,
                },
            )
            if paper.tags:
                for tag in [t.strip() for t in paper.tags.split(',')]:
                    concept, _ = GraphNode.objects.get_or_create(
                        user=user, node_type='concept', label=tag,
                        defaults={'description': f'概念：{tag}'},
                    )
                    GraphEdge.objects.get_or_create(
                        user=user, source_node=node, target_node=concept,
                        defaults={'relation_type': 'concept_of'},
                    )
        self.stdout.write(self.style.SUCCESS('Seed data ready'))
