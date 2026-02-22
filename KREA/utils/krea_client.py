import os
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv


def get_api_token() -> str:
    load_dotenv()
    token = os.environ.get("KREA_CART")
    if not token:
        raise RuntimeError("Missing KREA_CART in environment or .env")
    return token


def create_job(
    api_base: str,
    api_token: str,
    prompt: str,
    width: int,
    height: int,
    steps: int,
) -> Dict[str, Any]:
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
    return response.json()


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


def download_image(image_url: str, filename_base: str = "images") -> str:
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    ext = "png"
    if "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
    elif "webp" in content_type:
        ext = "webp"
    elif "png" in content_type:
        ext = "png"
    file_path = f"{filename_base}.{ext}"
    with open(file_path, "wb") as f:
        f.write(response.content)
    return file_path
