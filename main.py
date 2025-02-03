import mimetypes
import urllib.parse
import json
import logging
import socket
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime
import os

# Настройки серверов
BASE_DIR = pathlib.Path(__file__).parent
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = "0.0.0.0"

SOCKET_HOST = os.environ.get("SOCKET_HOST", "127.0.0.1")
SOCKET_PORT = 5000

# Пути к файлам
STORAGE_DIR = BASE_DIR / "storage"
DATA_FILE = STORAGE_DIR / "data.json"

# Создание storage и data.json, если их нет
STORAGE_DIR.mkdir(exist_ok=True)
if not DATA_FILE.exists():
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Обрабатывает отправку формы, пересылая данные на Socket сервер"""
        size = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(size)

        # Отправка данных в Socket сервер
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
            client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def do_GET(self):
        """Обрабатывает GET-запросы"""
        pr_url = urllib.parse.urlparse(self.path)

        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message":
            self.send_html_file("message.html")
        else:
            file_path = BASE_DIR / pr_url.path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self.send_static(file_path)
            else:
                self.send_html_file("error.html", 404)

    def send_html_file(self, filename, status=200):
        """Отправляет HTML-файл клиенту"""
        file_path = BASE_DIR / filename
        if file_path.exists():
            self.send_response(status)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(file_path, "rb") as fd:
                self.wfile.write(fd.read())
        else:
            self.send_error(404, "File Not Found")

    def send_static(self, file_path):
        """Отправляет статические файлы"""
        self.send_response(200)
        mime_type, _ = mimetypes.guess_type(file_path)
        self.send_header("Content-type", mime_type or "text/plain")
        self.end_headers()
        with open(file_path, "rb") as file:
            self.wfile.write(file.read())


def save_data_from_form(data):
    """Сохраняет данные формы в data.json"""
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {
            key: value
            for key, value in [el.split("=", 1) for el in parse_data.split("&")]
        }
        timestamp = datetime.now().isoformat()

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {}

        existing_data[timestamp] = parse_dict

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(f"Ошибка обработки данных формы: {err}")


def run_socket_server(host, port):
    """Запускает Socket сервер"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((host, port))
        logging.info(f"Socket сервер слушает на {host}:{port}")

        while True:
            data, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Получены данные от {address}: {data}")
            save_data_from_form(data)


def run_http_server():
    """Запускает HTTP сервер"""
    server_address = (HTTP_HOST, HTTP_PORT)
    http = HTTPServer(server_address, HttpHandler)
    logging.info(f"HTTP сервер запущен на {HTTP_HOST}:{HTTP_PORT}")

    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s: %(message)s")

    socket_thread = threading.Thread(
        target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT), daemon=True
    )
    socket_thread.start()

    run_http_server()
