import base64
import binascii
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
                result = job.get("result") or {}
                if "video_url" in result:
                    return result["video_url"]
                if "image_url" in result:
                    return result["image_url"]
                if "url" in result:
                    return result["url"]
                urls = result.get("urls")
                if isinstance(urls, list) and urls:
                    return urls[0]
                raise RuntimeError(f"Missing video URL in result: {result}")
            raise RuntimeError(f"Job failed: {job.get('status')}")

        if "progress" in job:
            print(f"Progress: {job['progress']}%")
        else:
            print(f"Status: {job.get('status')}")
        time.sleep(2)


def upload_image_asset(
    api_base: str,
    api_token: str,
    image_base64: str,
    image_name: str | None,
    image_type: str | None,
) -> str:
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("Invalid image data provided.") from exc

    filename = image_name or "source-image.png"
    mime_type = image_type or "image/png"

    response = requests.post(
        f"{api_base}/assets",
        headers={"Authorization": f"Bearer {api_token}"},
        files={"file": (filename, image_bytes, mime_type)},
        timeout=60,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Asset upload failed with status {response.status_code}: {response.text}"
        ) from exc

    asset = response.json()
    image_url = asset.get("image_url")
    if not image_url:
        raise RuntimeError(f"Missing image_url from asset upload: {asset}")
    return image_url


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

    @app.post("/generate/image")
    def generate_image():
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt", "a serene mountain landscape at sunset")
        width = int(payload.get("width", 1024))
        height = int(payload.get("height", 576))
        steps = int(payload.get("steps", 28))

        try:
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
        except requests.HTTPError:
            return (
                jsonify(
                    {
                        "error": f"Krea API error {response.status_code}",
                        "details": response.text,
                    }
                ),
                502,
            )

        job_id = job.get("job_id")
        if not job_id:
            return jsonify({"error": "Missing job_id", "raw": job}), 502

        try:
            image_url = wait_for_job(api_base, api_token, job_id)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"image_url": image_url})

    @app.post("/generate/video")
    def generate_video():
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt", "a majestic eagle soaring over snow-capped mountains at sunrise")
        duration = int(payload.get("duration", 5))
        width = int(payload.get("width", 1280))
        height = int(payload.get("height", 720))
        fps = int(payload.get("fps", 24))
        motion_strength = float(payload.get("motion_strength", 0.7))
        image_base64 = payload.get("image_base64")
        image_name = payload.get("image_name")
        image_type = payload.get("image_type")

        aspect_ratio = "16:9"
        if width > 0 and height > 0:
            ratio = width / height
            if abs(ratio - 1.0) < 0.05:
                aspect_ratio = "1:1"
            elif ratio < 1.0:
                aspect_ratio = "9:16"

        image_url = None
        if image_base64:
            try:
                image_url = upload_image_asset(
                    api_base,
                    api_token,
                    image_base64,
                    image_name,
                    image_type,
                )
            except RuntimeError as exc:
                return jsonify({"error": str(exc)}), 502

        try:
            response = requests.post(
                f"{api_base}/generate/video/kling/kling-2.5",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "duration": duration,
                    "aspectRatio": aspect_ratio,
                    "fps": fps,
                    "motion_strength": motion_strength,
                    "startImage": image_url,
                    "image_url": image_url,
                },
                timeout=60,
            )
            response.raise_for_status()
            job = response.json()
        except requests.HTTPError:
            return (
                jsonify(
                    {
                        "error": f"Krea API error {response.status_code}",
                        "details": response.text,
                    }
                ),
                502,
            )
        job_id = job.get("job_id")
        if not job_id:
            return jsonify({"error": "Missing job_id", "raw": job}), 502

        try:
            video_url = wait_for_job(api_base, api_token, job_id)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"video_url": video_url})

    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
