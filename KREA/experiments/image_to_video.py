import base64
import time

import requests

from utils.krea_client import get_api_token


def wait_for_video(api_base: str, api_token: str, job_id: str) -> str:
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

        time.sleep(5)


def main() -> None:
    api_base = "https://api.krea.ai"
    api_token = get_api_token()

    # Option 1: Use a local image file (base64)
    # with open("input_image.jpg", "rb") as image_file:
    #     encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # Option 2: Use a public image URL
    image_url = "https://example.com/input-image.jpg"

    payload = {
        "image_url": image_url,
        "prompt": "gentle camera pan from left to right, subtle depth",
        "duration": 5,
        "motion_strength": 0.7,
        "fps": 24,
    }

    response = requests.post(
        f"{api_base}/generate/video/kling/kling-2.5",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    job = response.json()
    job_id = job.get("job_id")
    if not job_id:
        raise RuntimeError(f"Missing job_id in response: {job}")

    video_url = wait_for_video(api_base, api_token, job_id)
    print(f"Video ready: {video_url}")


if __name__ == "__main__":
    main()
