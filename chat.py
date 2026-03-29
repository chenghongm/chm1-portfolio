import os
import json
import httpx
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except Exception:
            self._respond(400, {'error': 'Invalid JSON'})
            return

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            self._respond(500, {'error': 'API key not configured'})
            return

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'content-type': 'application/json',
                    },
                    json={
                        'model': 'claude-haiku-4-5-20251001',
                        'max_tokens': 500,
                        'system': data.get('system', ''),
                        'messages': data.get('messages', []),
                    }
                )
            self.send_response(response.status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response.content)

        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _respond(self, status, data):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
