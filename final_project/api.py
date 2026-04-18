import base64
import json
import os
import re
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from openai import APIConnectionError, AuthenticationError, OpenAI, OpenAIError, RateLimitError


ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "index.html"
OUTPUT_DIR = ROOT / "images"
HOST = "127.0.0.1"
PORT = 5000
OPENAI_MODEL = "gpt-image-1.5"
XAI_MODEL = "grok-imagine-image"
XAI_BASE_URL = "https://api.x.ai/v1"
BAD_PROXY_VALUES = {
    "http://127.0.0.1:9",
    "https://127.0.0.1:9",
    "http://localhost:9",
    "https://localhost:9",
}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def clear_broken_proxy_settings() -> None:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        value = os.environ.get(key, "").strip()
        if value in BAD_PROXY_VALUES:
            os.environ.pop(key, None)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "untitled"


def get_batch_dir(provider: str, batch_name: str, prompt: str) -> Path:
    normalized_batch_name = slugify(batch_name.strip() or prompt)
    batch_dir = OUTPUT_DIR / provider / normalized_batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    return batch_dir


def next_image_path(batch_dir: Path) -> Path:
    existing_indices = []
    for file_path in batch_dir.glob("image-*.png"):
        match = re.fullmatch(r"image-(\d+)\.png", file_path.name)
        if match:
            existing_indices.append(int(match.group(1)))

    next_index = max(existing_indices, default=0) + 1
    return batch_dir / f"image-{next_index}.png"


def save_generated_image(provider: str, batch_name: str, prompt: str, image_b64: str) -> str:
    batch_dir = get_batch_dir(provider, batch_name, prompt)
    file_path = next_image_path(batch_dir)
    file_path.write_bytes(base64.b64decode(image_b64))
    return str(file_path.relative_to(ROOT)).replace("\\", "/")


def generate_openai_image(prompt: str) -> str:
    client = OpenAI()
    result = client.images.generate(
        model=OPENAI_MODEL,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )
    return result.data[0].b64_json


def generate_xai_image(prompt: str) -> str:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API_KEY is missing from .env")

    client = OpenAI(base_url=XAI_BASE_URL, api_key=api_key)
    result = client.images.generate(
        model=XAI_MODEL,
        prompt=prompt,
        n=1,
        response_format="b64_json",
    )
    return result.data[0].b64_json


def generate_image(provider: str, prompt: str, batch_name: str) -> tuple[str, str]:
    if provider == "xai":
        image_b64 = generate_xai_image(prompt)
    else:
        image_b64 = generate_openai_image(prompt)

    image_url = f"data:image/png;base64,{image_b64}"
    saved_file = save_generated_image(provider, batch_name, prompt, image_b64)
    return image_url, saved_file


class ImageAppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html(INDEX_FILE.read_text(encoding="utf-8"))
            return

        self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/generate":
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(
                {"error": "Request body must be valid JSON."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        prompt = str(payload.get("prompt", "")).strip()
        provider = str(payload.get("provider", "openai")).strip().lower()
        batch_name = str(payload.get("batchName", "")).strip()

        if not prompt:
            self._send_json(
                {"error": "Please enter a prompt before generating an image."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        if provider not in {"openai", "xai"}:
            self._send_json(
                {"error": "Provider must be either openai or xai."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            image_url, saved_file = generate_image(provider, prompt, batch_name)
        except AuthenticationError:
            self._send_json(
                {
                    "error": (
                        f"Authentication failed for {provider}. Check the matching API key "
                        "in .env, then restart the server."
                    )
                },
                status=HTTPStatus.UNAUTHORIZED,
            )
            return
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except APIConnectionError:
            self._send_json(
                {
                    "error": (
                        f"Connection to {provider} failed. Your local page is running, but "
                        "the server could not reach the provider API."
                    )
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return
        except RateLimitError:
            self._send_json(
                {
                    "error": (
                        f"{provider} rejected the request due to rate limits or billing. "
                        "Check your usage limits and account status."
                    )
                },
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
            return
        except OpenAIError as exc:
            self._send_json(
                {"error": f"{provider} returned an error: {exc}"},
                status=HTTPStatus.BAD_GATEWAY,
            )
            return
        except Exception as exc:
            self._send_json(
                {"error": f"Image generation failed: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json({"imageUrl": image_url, "savedFile": saved_file})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    load_dotenv(ROOT / ".env")
    clear_broken_proxy_settings()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing from .env")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((HOST, PORT), ImageAppHandler)
    url = f"http://{HOST}:{PORT}"
    print("")
    print("=" * 56)
    print("Local image comparison app is running.")
    print(f"Open this page in your browser: {url}")
    print("Each click generates 1 image and appends it into the chosen batch folder.")
    print("Leave this terminal open while you test.")
    print("=" * 56)
    print("")
    webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
