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

        # api_key = os.environ.get('ASSISTANT_ID')
        api_key = os.environ.get('ASSISTANT_GEMINI_ID')
        if not api_key:
            self._respond(500, {'error': 'API key not configured'})
            return

        try:
            # 1. 适配 Gemini 的消息格式
            gemini_messages = []
            for msg in data.get('messages', []):
                # Claude 的 'assistant' 对应 Gemini 的 'model'
                role = "model" if msg['role'] == "assistant" else "user"
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": msg['content']}]
                })

            # 2. 构造 Gemini 特有的 Payload
            gemini_payload = {
                "contents": gemini_messages,
                "system_instruction": {
                    "parts": [{"text": data.get('system', '')}]
                },
                "generationConfig": {
                    "maxOutputTokens": 500,
                    "temperature": 0.1, # 既然要防幻觉，建议压低温度
                }
            }

            with httpx.Client(timeout=30) as client:
                # 3. URL 包含 API Key
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

                response = client.post(
                    gemini_url,
                    headers={'Content-Type': 'application/json'},
                    json=gemini_payload
                )
            # with httpx.Client(timeout=30) as client:
            #     response = client.post(
            #         'https://api.anthropic.com/v1/messages',
            #         headers={
            #             'x-api-key': api_key,
            #             'anthropic-version': '2023-06-01',
            #             'content-type': 'application/json',
            #         },
            #         json={
            #             'model': 'claude-haiku-4-5-20251001',
            #             'max_tokens': 500,
            #             'system': data.get('system', ''),
            #             'messages': data.get('messages', []),
            #         }
            #     )
            # 提取 Gemini 的核心文本
            gemini_res = response.json()
            answer_text = gemini_res['candidates'][0]['content']['parts'][0]['text']
            
            # 构造一个“假”的 Claude 响应格式
            fake_claude_payload = {
                "content": [
                    {
                        "type": "text",
                        "text": answer_text
                    }
                ],
                "id": gemini_res.get("responseId", "fake_id"),
                "model": "gemini-3-flash-preview", # 或者是你用的版本
                "role": "assistant"
            }
            self.send_response(response.status_code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            # self.wfile.write(response.content)
            self.wfile.write(json.dumps(fake_claude_payload).encode())

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
