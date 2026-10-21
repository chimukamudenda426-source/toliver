import base64
import binascii
import hmac
import json
import mimetypes
import os
import re
import sqlite3
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = (ROOT / "imagesthereal").resolve()
DATABASE = Path(os.environ.get("DANCEFLOW_DB", ROOT / "registrations.sqlite3")).resolve()
HOST = os.environ.get("DANCEFLOW_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", os.environ.get("DANCEFLOW_PORT", "8000")))
ADMIN_PASSWORD = os.environ.get("DANCEFLOW_ADMIN_PASSWORD", "")
MAX_BODY_BYTES = 16_384
CATEGORIES = {
    "Memphis jookin",
    "Animation",
    "Party dance",
    "Cramp",
    "Other",
}
STATIC_FILES = {
    "/": "ideaweb.html",
    "/ideaweb.html": "ideaweb.html",
    "/nextpage1.html": "nextpage1.html",
    "/nextpage2.html": "nextpage2.html",
    "/nextpage3.html": "nextpage3.html",
    "/admin.html": "admin.html",
    "/Thereal's.css": "Thereal's.css",
}


def initialize_database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                category TEXT NOT NULL,
                category_details TEXT NOT NULL DEFAULT '',
                experience TEXT NOT NULL DEFAULT '',
                registered_at TEXT NOT NULL
            )
            """
        )


def valid_admin_header(header):
    if not header or not header.startswith("Basic "):
        return False
    try:
        credentials = base64.b64decode(header[6:], validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    username, separator, password = credentials.partition(":")
    return (
        bool(separator)
        and hmac.compare_digest(username, "admin")
        and hmac.compare_digest(password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8"))
    )


class DanceFlowHandler(SimpleHTTPRequestHandler):
    server_version = "DanceFlow"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def require_admin(self):
        if valid_admin_header(self.headers.get("Authorization")):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="DanceFlow Organizer", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/health":
            self.send_json(200, {"status": "ok"})
            return
        if path == "/api/registrations":
            if not self.require_admin():
                return
            with sqlite3.connect(DATABASE) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(
                    """
                    SELECT id, name, email, category, category_details, experience, registered_at
                    FROM registrations
                    ORDER BY registered_at DESC, id DESC
                    """
                ).fetchall()
            self.send_json(200, {"registrations": [dict(row) for row in rows]})
            return
        if path in STATIC_FILES:
            self.send_file(ROOT / STATIC_FILES[path])
            return
        if path.startswith("/imagesthereal/"):
            image_path = (ROOT / path.lstrip("/")).resolve()
            if image_path.is_relative_to(IMAGE_ROOT) and image_path.is_file():
                self.send_file(image_path)
                return
        self.send_error(404, "Not found")

    def send_file(self, path):
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/register":
            self.send_error(404, "Not found")
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Send registration details as JSON."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request size."})
            return
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "Registration details are missing or too large."})
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Registration details must be valid JSON."})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "Registration details must be an object."})
            return

        name = payload.get("name")
        email = payload.get("email")
        category = payload.get("category")
        details = payload.get("category_details", "")
        experience = payload.get("experience", "")
        if not all(isinstance(value, str) for value in (name, email, category, details, experience)):
            self.send_json(400, {"error": "Please provide valid registration details."})
            return

        name = name.strip()
        email = email.strip().lower()
        details = details.strip()
        experience = experience.strip()
        if not name or len(name) > 100:
            self.send_json(400, {"error": "Enter a name between 1 and 100 characters."})
            return
        if (
            len(email) > 254
            or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        ):
            self.send_json(400, {"error": "Enter a valid email address."})
            return
        if category not in CATEGORIES:
            self.send_json(400, {"error": "Choose one of the listed dance categories."})
            return
        if category == "Other" and (not details or len(details) > 100):
            self.send_json(400, {"error": "Please enter your other dance category (up to 100 characters)."})
            return
        if category != "Other":
            details = ""
        if len(experience) > 2000:
            self.send_json(400, {"error": "Dance experience must be 2,000 characters or fewer."})
            return

        registered_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with sqlite3.connect(DATABASE) as connection:
            cursor = connection.execute(
                """
                INSERT INTO registrations
                    (name, email, category, category_details, experience, registered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, email, category, details, experience, registered_at),
            )
            registration_id = cursor.lastrowid
        self.send_json(201, {"id": registration_id, "message": "Registration saved."})


if __name__ == "__main__":
    if not ADMIN_PASSWORD:
        raise SystemExit(
            "Set DANCEFLOW_ADMIN_PASSWORD before starting the server. "
            "For a local setup, run .\\start-danceflow.ps1."
        )
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), DanceFlowHandler)
    print(f"DanceFlow running at http://{HOST}:{PORT}/")
    print(f"Organizer dashboard: http://{HOST}:{PORT}/admin.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDanceFlow server stopped.")
    finally:
        server.server_close()
