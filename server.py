import os
import json
import hashlib
import secrets
import urllib.request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import SimpleHTTPRequestHandler, HTTPServer
import sys
import ssl
import io
import html
import hmac
import time
from PIL import Image

CONTENT_FILE = 'content.json'

# In-memory session store: token -> timestamp
_sessions = {}
SESSION_MAX_AGE = 86400  # 24 hours

# Load environment variables from .env file
def load_env():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()

def get_admin_password():
    return os.environ.get('ADMIN_PASSWORD', 'changeme')

def hash_password(pw):
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

def read_content():
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def write_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class CustomHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        # Suppress noisy access logs; keep errors
        pass

    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def get_session_token(self):
        cookie = self.headers.get('Cookie', '')
        for part in cookie.split(';'):
            part = part.strip()
            if part.startswith('admin_token='):
                return part[len('admin_token='):]
        return None

    def is_authenticated(self):
        token = self.get_session_token()
        if not token or token not in _sessions:
            return False
        if time.time() - _sessions[token] > SESSION_MAX_AGE:
            del _sessions[token]
            return False
        return True

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        if self.path == '/api/content':
            data = read_content()
            self.send_json(200, data)
            return
        # Serve admin page
        super().do_GET()

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))

        # Enforce max body size
        max_size = 10 * 1024 * 1024  # 10MB for images
        if self.path == '/api/upload-image':
            if content_length > max_size:
                self.send_json(413, {'status': 'error', 'message': 'File too large (max 10MB)'})
                return
        elif content_length > 1024 * 1024:  # 1MB for JSON endpoints
            self.send_json(413, {'status': 'error', 'message': 'Request too large'})
            return

        post_data = self.rfile.read(content_length)

        # ---- Admin login
        if self.path == '/api/admin-login':
            try:
                data = json.loads(post_data.decode('utf-8'))
                password = data.get('password', '')
                expected = get_admin_password()
                if hmac.compare_digest(hash_password(password), hash_password(expected)):
                    token = secrets.token_hex(32)
                    _sessions[token] = time.time()
                    body = json.dumps({'status': 'ok'}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Set-Cookie',
                        f'admin_token={token}; Path=/; HttpOnly; SameSite=Strict')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    print(f'🔐 Admin login successful')
                else:
                    self.send_json(401, {'status': 'error', 'message': 'Wrong password'})
            except Exception as e:
                print(f'❌ Error: {e}')
                self.send_json(500, {'status': 'error', 'message': 'Internal server error'})
            return

        # ---- Save content (requires auth)
        if self.path == '/api/content':
            if not self.is_authenticated():
                self.send_json(401, {'status': 'error', 'message': 'Unauthorized'})
                return
            try:
                data = json.loads(post_data.decode('utf-8'))
                write_content(data)
                print(f'💾 Content saved via admin panel')
                self.send_json(200, {'status': 'ok'})
            except Exception as e:
                print(f'❌ Error: {e}')
                self.send_json(500, {'status': 'error', 'message': 'Internal server error'})
            return

        # ---- Upload image (requires auth)
        if self.path == '/api/upload-image':
            if not self.is_authenticated():
                self.send_json(401, {'status': 'error', 'message': 'Unauthorized'})
                return
            try:
                target_path = self.headers.get('X-Target-Path', '')
                if not target_path:
                    self.send_json(400, {'status': 'error', 'message': 'Missing X-Target-Path header'})
                    return
                
                # Security check
                normalized = os.path.normpath(target_path)
                if normalized.startswith('..') or os.path.isabs(normalized) or not (normalized.startswith('assets/logos/') or normalized.startswith('assets/images/')):
                    self.send_json(403, {'status': 'error', 'message': 'Forbidden path'})
                    return
                
                # Check file extension compatibility
                if target_path.endswith('.svg'):
                    # Save SVG directly
                    os.makedirs(os.path.dirname(normalized), exist_ok=True)
                    with open(normalized, 'wb') as f:
                        f.write(post_data)
                elif target_path.endswith(('.webp', '.png', '.jpg', '.jpeg')):
                    # Use Pillow to optimize and save as WebP
                    image_file = io.BytesIO(post_data)
                    img = Image.open(image_file)
                    os.makedirs(os.path.dirname(normalized), exist_ok=True)
                    
                    # Convert to WebP and save (enforcing WEBP format for webp target filenames)
                    img.save(normalized, format='WEBP', quality=85, optimize=True)
                else:
                    self.send_json(400, {'status': 'error', 'message': 'Unsupported file format'})
                    return
                
                print(f'📸 Image {normalized} uploaded and optimized successfully')
                self.send_json(200, {'status': 'ok'})
            except Exception as e:
                print(f'❌ Error: {e}')
                self.send_json(500, {'status': 'error', 'message': 'Internal server error'})
            return

        # ---- Admin logout
        if self.path == '/api/admin-logout':
            token = self.get_session_token()
            if token and token in _sessions:
                del _sessions[token]
            body = json.dumps({'status': 'ok'}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Set-Cookie', 'admin_token=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ---- Partner inquiry form (existing)
        if self.path == '/api/partner-inquiry':
            try:
                data = json.loads(post_data.decode('utf-8'))
                name = data.get('name', '')
                org = data.get('org', '')
                email = data.get('email', '')
                type_val = data.get('type', '')
                message = data.get('message', '')

                print(f"\n📩 Отримано нову заявку від: {name} ({org})")

                text_msg = (
                    f"🔔 Новий запит на партнерство!\n\n"
                    f"👤 Ім'я: {name}\n"
                    f"🏢 Організація: {org}\n"
                    f"📧 Email: {email}\n"
                    f"🤝 Напрямок: {type_val}\n"
                    f"📝 Повідомлення: {message}"
                )

                tg_status = "Not configured"
                tg_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
                tg_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

                if tg_token and tg_chat_id:
                    try:
                        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                        payload = json.dumps({
                            "chat_id": tg_chat_id,
                            "text": text_msg
                        }).encode('utf-8')
                        req = urllib.request.Request(
                            url, data=payload,
                            headers={'Content-Type': 'application/json'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as response:
                            res = json.loads(response.read().decode())
                            tg_status = "Sent" if res.get('ok') else f"Failed: {res.get('description')}"
                    except Exception as e:
                        tg_status = f"Error: {str(e)}"

                email_status = "Not configured"
                smtp_host = os.environ.get('SMTP_HOST', '')
                smtp_port = os.environ.get('SMTP_PORT', '587')
                smtp_user = os.environ.get('SMTP_USER', '')
                smtp_pass = os.environ.get('SMTP_PASSWORD', '')
                to_email = os.environ.get('TO_EMAIL', 'nb@kosmostabir.org')

                if smtp_host and smtp_user and smtp_pass:
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = smtp_user
                        msg['To'] = to_email
                        msg['Subject'] = f"Нова заявка на партнерство: {name} ({org})"
                        safe_name = html.escape(name)
                        safe_org = html.escape(org)
                        safe_email = html.escape(email)
                        safe_type = html.escape(type_val)
                        safe_message = html.escape(message)
                        html_body = f"""
                        <html>
                          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                            <h2 style="color: #1a3c34; border-bottom: 2px solid #1a3c34; padding-bottom: 8px;">Нова заявка на партнерство</h2>
                            <p><strong>Ім'я контактної особи:</strong> {safe_name}</p>
                            <p><strong>Організація / Компанія:</strong> {safe_org}</p>
                            <p><strong>Електронна пошта:</strong> <a href="mailto:{safe_email}">{safe_email}</a></p>
                            <p><strong>Напрямок співпраці:</strong> {safe_type}</p>
                            <div style="background: #f7f6f2; padding: 15px; border-radius: 6px; border: 1px solid #e5e5e5; margin-top: 15px;">
                              <strong>Повідомлення / Пропозиція:</strong><br>
                              {safe_message.replace(chr(10), '<br>')}
                            </div>
                          </body>
                        </html>
                        """
                        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                        port = int(smtp_port)
                        if port == 465:
                            server = smtplib.SMTP_SSL(smtp_host, port)
                        else:
                            server = smtplib.SMTP(smtp_host, port)
                            server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.sendmail(smtp_user, to_email, msg.as_string())
                        server.quit()
                        email_status = "Sent"
                        print(f"✅ Email sent to {to_email}")
                    except Exception as e:
                        email_status = f"Error: {str(e)}"

                self.send_json(200, {"status": "success", "telegram": tg_status, "email": email_status})

            except Exception as e:
                print(f'❌ Error: {e}')
                self.send_json(500, {"status": "error", "message": "Internal server error"})
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run(port=8181):
    load_env()
    server_address = ('', port)
    httpd = HTTPServer(server_address, CustomHandler)
    print(f"\n🚀 Сервер запущено на http://localhost:{port}")
    print(f"🔐 Адмін-панель: http://localhost:{port}/admin.html")
    print(f"🔑 Пароль адмінки: встановіть ADMIN_PASSWORD у файлі .env")
    print("Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер зупинено.")
        sys.exit(0)


if __name__ == '__main__':
    port_arg = 8181
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            pass
    run(port_arg)
