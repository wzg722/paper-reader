# -*- coding: utf-8 -*-
"""
PaperMind 本地 arXiv 代理（解决浏览器 CORS 限制）
用法： python arxiv_proxy.py [端口]
启动后：http://127.0.0.1:8010/arxiv?q=transformer+attention
原型「收藏网站 → arXiv → 搜索」会自动降级到此代理，实现真实检索。
正式版：由 Django 后端实现同样转发（服务端无 CORS 限制）。
"""
import http.server, urllib.parse, urllib.request, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8010
ARXIV_API = 'https://export.arxiv.org/api/query'

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith('/arxiv'):
            self.send_error(404); return
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('q', [''])[0]
        if not q:
            self.send_error(400, 'missing q'); return
        url = ARXIV_API + '?search_query=all:' + urllib.parse.quote(q) + '&max_results=20&sortBy=relevance'
        req = urllib.request.Request(url, headers={'User-Agent': 'PaperMindProxy/1.0'})
        try:
            data = urllib.request.urlopen(req, timeout=20).read()
        except Exception as e:
            self.send_response(502); self.send_header('Content-Type', 'text/plain'); self.end_headers()
            self.wfile.write(str(e).encode()); return
        self.send_response(200)
        self.send_header('Content-Type', 'application/atom+xml; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')   # 关键：放开 CORS
        self.send_header('Cache-Control', 'max-age=300')
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    print('PaperMind arXiv 代理已启动: http://127.0.0.1:%d/arxiv?q=关键词' % PORT)
    http.server.HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
