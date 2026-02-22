import os
import time
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
import requests


def wait_for_job(api_base: str, api_token: str, job_id: str) -> str:
    while True:
        response = requests.get(
            f"{api_base}/jobs/{job_id}",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30,
        )
        response.raise_for_status()
        job = response.json()

        if job.get("completed_at"):
            if job.get("status") == "completed":
                return job["result"]["urls"][0]
            raise RuntimeError(f"Job failed: {job.get('status')}")

        print(f"Status: {job.get('status')}")
        time.sleep(2)


def main() -> None:
    load_dotenv()

    api_base = "https://api.krea.ai"
    api_token = os.environ.get("KREA_CART")
    if not api_token:
        raise SystemExit("Missing KREA_CART in environment or .env")

    app = Flask(__name__)

    @app.get("/")
    def index():
        return send_from_directory(".", "index.html")

    @app.post("/generate")
    def generate():
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt", "a serene mountain landscape at sunset")
        width = int(payload.get("width", 1024))
        height = int(payload.get("height", 576))
        steps = int(payload.get("steps", 28))

        response = requests.post(
            f"{api_base}/generate/image/bfl/flux-1-dev",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": steps,
            },
            timeout=60,
        )
        response.raise_for_status()
        job = response.json()
        job_id = job.get("job_id")
        if not job_id:
            return jsonify({"error": "Missing job_id", "raw": job}), 502

        try:
            image_url = wait_for_job(api_base, api_token, job_id)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"image_url": image_url})

    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
