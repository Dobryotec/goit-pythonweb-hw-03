from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import os
import logging
from datetime import datetime
from jinja2 import Template


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STORAGE_DIR = '/app/storage'
DATA_FILE = os.path.join(STORAGE_DIR, 'data.json')

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        pr_url = urllib.parse.urlparse(self.path)
        logger.info(f"Received GET request: {pr_url.path}")

        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file('message.html')
        elif pr_url.path == '/read':
            self.show_messages()
        elif pr_url.path.startswith('/static/'):
            self.serve_static(pr_url.path[1:])
        else:
            logger.warning("404 Not Found: %s", pr_url.path)
            self.send_html_file('error.html', 404)

    def do_POST(self) -> None:
        pr_url = urllib.parse.urlparse(self.path)
        logger.info(f"Received POST request: {pr_url.path}")

        if pr_url.path == '/message':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            post_data = urllib.parse.parse_qs(body.decode('utf-8'))
            message_data = {
                "username": post_data.get("username", [""])[0],
                "message": post_data.get("message", [""])[0]
            }
            self.save_message(message_data)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            logger.warning("405 Method Not Allowed: %s", pr_url.path)
            self.send_response(405)
            self.end_headers()

    def send_html_file(self, filename, status=200):
        try:
            filepath = os.path.join("templates", filename)
            with open(filepath, 'rb') as fd:
                self.send_response(status)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(fd.read())
                logger.info(f"Served HTML file: {filename}")
        except FileNotFoundError:
            logger.error("File not found: %s", filename)
            self.send_response(404)
            self.end_headers()

    def serve_static(self, path):
        filepath = path.lstrip('/')
        try:
            with open(filepath, 'rb') as fd:
                self.send_response(200)
                if filepath.endswith(".css"):
                    self.send_header("Content-type", "text/css")
                elif filepath.endswith(".png"):
                    self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(fd.read())
                logger.info(f"Served static file: {filepath}")
        except FileNotFoundError:
            logger.error("Static file not found: %s", filepath)
            self.send_response(404)
            self.end_headers()

    def save_message(self, message_data):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        timestamp = datetime.now().isoformat()
        data[timestamp] = message_data

        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        logger.info("Saved new message from %s", message_data["username"])

    def show_messages(self):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Messages</title>
        </head>
        <body>
            <h1>Messages</h1>
            <ul>
                {% for timestamp, msg in messages.items() %}
                    <li><strong>{{ msg.username }}</strong>: {{ msg.message }} <em>({{ timestamp }})</em></li>
                {% endfor %}
            </ul>
            <a href="/">Back</a>
        </body>
        </html>
        """
        template = Template(template_str)
        response_content = template.render(messages=data)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response_content.encode('utf-8'))
        logger.info("Displayed messages page")

def run(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    logger.info("Starting server on port 3000")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()
        logger.info("Server stopped")

if __name__ == '__main__':
    run()