"""LLM client (OpenAI / NewAPI compatible) for translation / summary / Q&A.
Default gateway: DEEPSEEK_BASE_URL (e.g. https://llm.talkweb.com.cn)
Supports user translate_config and NewAPI channel conn:
  {"_type":"newapi_channel_conn","key":"sk-...","url":"https://llm.talkweb.com.cn","model":"..."}
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Official DeepSeek host — treat as stale default; prefer server env gateway instead.
_LEGACY_HOSTS = {
    'https://api.deepseek.com',
    'api.deepseek.com',
}
_LEGACY_MODELS = {'', 'deepseek-chat', 'deepseek-v3', 'deepseek-v3-chat'}


def _normalize_base_url(url: str) -> str:
    url = (url or '').strip().rstrip('/')
    if url.endswith('/v1'):
        url = url[:-3]
    return url


def _is_legacy_deepseek(url: str) -> bool:
    base = _normalize_base_url(url).lower()
    return (not base) or base in _LEGACY_HOSTS or base.endswith('api.deepseek.com')


def _resolve_config(user_config: dict | None = None) -> dict:
    """Merge user preference with server NewAPI gateway settings.

    Server ``DEEPSEEK_*`` wins when user still has old DeepSeek defaults or no key.
    Accepts both ``api_key`` and NewAPI ``key`` fields.
    """
    cfg = dict(user_config or {})
    user_key = (cfg.get('api_key') or cfg.get('key') or '').strip()
    user_url = _normalize_base_url(cfg.get('url') or '')
    user_model = (cfg.get('model') or '').strip()

    server_key = (settings.DEEPSEEK_API_KEY or '').strip()
    server_url = _normalize_base_url(settings.DEEPSEEK_BASE_URL or 'https://llm.talkweb.com.cn')
    server_model = (settings.DEEPSEEK_MODEL or 'deepseek-v4-flash').strip()

    # Prefer server gateway unless user configured a non-legacy custom endpoint + key
    custom_endpoint = bool(user_key) and user_url and not _is_legacy_deepseek(user_url)
    if custom_endpoint:
        api_key, base_url = user_key, user_url
        model = user_model or server_model
    else:
        api_key = user_key or server_key
        base_url = server_url if _is_legacy_deepseek(user_url) else (user_url or server_url)
        # replace stale model names with server default
        model = server_model if (not user_model or user_model in _LEGACY_MODELS) else user_model
        # if still no key after merge, keep empty (offline placeholder)
        if not api_key:
            api_key = server_key

    return {
        'api_key': api_key,
        'base_url': base_url,
        'model': model or 'deepseek-v4-flash',
        'timeout': int(cfg.get('timeout') or 60),
    }


def chat(
    messages: list[dict],
    user_config: dict | None = None,
    temperature: float = 0.3,
) -> str:
    cfg = _resolve_config(user_config)
    if not cfg['api_key']:
        return _offline_reply(messages)

    url = f"{cfg['base_url']}/v1/chat/completions"
    headers = {
        'Authorization': f"Bearer {cfg['api_key']}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': cfg['model'],
        'messages': messages,
        'temperature': temperature,
        'stream': False,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=cfg['timeout'])
        if r.status_code >= 400:
            # surface gateway error body for debugging
            detail = ''
            try:
                detail = r.text[:300]
            except Exception:
                pass
            logger.warning('LLM HTTP %s: %s', r.status_code, detail)
            r.raise_for_status()
        data = r.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.warning('LLM call failed: %s', e)
        return _offline_reply(messages, error=str(e))


def translate(text: str, user_config: dict | None = None, glossary: list | None = None) -> str:
    glossary_hint = ''
    if glossary:
        pairs = '; '.join(f'{a}={b}' for a, b, *_ in glossary[:30])
        glossary_hint = f'\n术语表（请保持译名一致）：{pairs}'
    messages = [
        {
            'role': 'system',
            'content': (
                '你是学术论文翻译专家。将用户给出的英文论文段落翻译成准确、流畅的中文，'
                '保留专业术语与公式符号，不要添加额外解释。' + glossary_hint
            ),
        },
        {'role': 'user', 'content': text},
    ]
    return chat(messages, user_config=user_config)


def summarize_selection(text: str, user_config: dict | None = None) -> str:
    messages = [
        {
            'role': 'system',
            'content': '用1-3句中文总结下列学术文本的核心含义，简洁准确。',
        },
        {'role': 'user', 'content': text},
    ]
    return chat(messages, user_config=user_config)


def summarize_paper(title: str, abstract: str, body: str = '', user_config: dict | None = None) -> dict:
    content = f'标题: {title}\n摘要: {abstract}\n正文节选:\n{body[:8000]}'
    messages = [
        {
            'role': 'system',
            'content': (
                '你是论文精读助手。基于全文输出纯 JSON（不要 markdown、不要代码围栏）。'
                '每个段落必须中英对照，英文用论文原术语，与中文一一对应。结构：'
                '{"core":{"zh":"一句话核心","en":"..."},'
                '"problem":{"zh":"研究问题","en":"..."},'
                '"method":[{"zh":"方法要点","en":"..."}],'
                '"result":{"zh":"主要结果","en":"..."},'
                '"limit":{"zh":"结论与局限","en":"..."},'
                '"insight":{"zh":"领域启发","en":"..."},'
                '"glossary":[{"en":"Term","zh":"中文","desc":"简释"}]}。'
                'method 至少 2 条；glossary 至少 5 个术语。'
            ),
        },
        {'role': 'user', 'content': content},
    ]
    raw = chat(messages, user_config=user_config)
    import json
    try:
        # strip code fences if any
        s = raw.strip()
        if s.startswith('```'):
            s = s.strip('`')
            if s.startswith('json'):
                s = s[4:]
        return json.loads(s)
    except Exception:
        return {
            'core': raw[:200],
            'problem': '',
            'method': [],
            'result': '',
            'limit': '',
            'insight': '',
            'glossary': [],
        }


def ask_paper(question: str, context: str, history: list | None = None, user_config: dict | None = None) -> str:
    messages = [
        {
            'role': 'system',
            'content': (
                '你是论文问答助手。根据给定论文上下文回答问题，'
                '尽量引用原文关键句，用中文回答。\n\n论文上下文：\n' + context[:12000]
            ),
        },
    ]
    for h in (history or [])[-10:]:
        messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': question})
    return chat(messages, user_config=user_config)


def generate_intro(title: str, abstract: str = '', user_config: dict | None = None) -> str:
    messages = [
        {'role': 'system', 'content': '用一句中文（不超过80字）概括这篇论文的贡献与价值。'},
        {'role': 'user', 'content': f'{title}\n{abstract}'},
    ]
    return chat(messages, user_config=user_config)


def test_translate_connection(user_config: dict | None = None, timeout: int = 6) -> dict:
    cfg = _resolve_config(user_config)
    start = time.time()
    if not cfg['api_key']:
        return {'ok': False, 'error': '未配置 API Key', 'latency_ms': 0}
    url = f"{cfg['base_url']}/v1/models"
    try:
        r = requests.get(
            url,
            headers={'Authorization': f"Bearer {cfg['api_key']}"},
            timeout=timeout,
        )
        latency = int((time.time() - start) * 1000)
        if r.status_code < 500:
            models = []
            try:
                models = [m.get('id') for m in (r.json().get('data') or []) if m.get('id')]
            except Exception:
                pass
            return {
                'ok': True,
                'status_code': r.status_code,
                'latency_ms': latency,
                'models': models[:20],
                'base_url': cfg['base_url'],
            }
        return {'ok': False, 'status_code': r.status_code, 'latency_ms': latency, 'error': r.text[:200]}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'latency_ms': int((time.time() - start) * 1000)}


def _offline_reply(messages: list[dict], error: str = '') -> str:
    last = ''
    for m in reversed(messages):
        if m.get('role') == 'user':
            last = m.get('content', '')
            break
    tip = f' [离线占位{": " + error if error else ""}，请检查 DEEPSEEK_API_KEY / 网关地址]'
    if '翻译' in str(messages[0].get('content', '')) or 'translate' in str(messages[0].get('content', '')).lower():
        return f'【译文占位】{last[:120]}…{tip}'
    return f'【AI 占位回复】已收到请求（{len(last)} 字）。{tip}'
