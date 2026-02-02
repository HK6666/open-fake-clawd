#!/usr/bin/env python3
"""
简单的 Git Webhook 服务器
监听来自 GitHub/GitLab 的 webhook 推送，自动执行部署脚本

使用方法：
1. 运行: python webhook-server.py
2. 在 GitHub/GitLab 设置 Webhook: http://your-server:9000/webhook
3. 设置 Secret Token（可选但推荐）
"""

import hmac
import hashlib
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# 配置
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'change-me-to-a-random-string')
DEPLOY_SCRIPT = './deploy.sh'
PORT = 9000


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # 验证签名（GitHub）
        signature = self.headers.get('X-Hub-Signature-256')
        if signature and WEBHOOK_SECRET != 'change-me-to-a-random-string':
            expected = 'sha256=' + hmac.new(
                WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected):
                print("❌ Invalid signature")
                self.send_response(401)
                self.end_headers()
                return

        # 验证签名（GitLab）
        token = self.headers.get('X-Gitlab-Token')
        if token and token != WEBHOOK_SECRET:
            print("❌ Invalid GitLab token")
            self.send_response(401)
            self.end_headers()
            return

        try:
            payload = json.loads(body.decode('utf-8'))
            
            # 获取分支名
            ref = payload.get('ref', '')
            
            # 只处理 main/master 分支的推送
            if ref in ['refs/heads/main', 'refs/heads/master']:
                print(f"🔔 Received push to {ref}")
                print("🚀 Starting deployment...")
                
                # 执行部署脚本
                result = subprocess.run(
                    [DEPLOY_SCRIPT],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print("✅ Deployment successful")
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'success',
                        'message': 'Deployment triggered successfully'
                    }).encode())
                else:
                    print(f"❌ Deployment failed: {result.stderr}")
                    self.send_response(500)
                    self.end_headers()
            else:
                print(f"ℹ️  Ignoring push to {ref}")
                self.send_response(200)
                self.end_headers()
                
        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # 自定义日志格式
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server():
    print(f"🎯 Webhook server starting on port {PORT}...")
    print(f"📍 Endpoint: http://0.0.0.0:{PORT}/webhook")
    
    if WEBHOOK_SECRET == 'change-me-to-a-random-string':
        print("⚠️  WARNING: Using default webhook secret! Set WEBHOOK_SECRET env var.")
    
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    print("✅ Server is running. Press Ctrl+C to stop.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
        server.shutdown()


if __name__ == '__main__':
    run_server()
