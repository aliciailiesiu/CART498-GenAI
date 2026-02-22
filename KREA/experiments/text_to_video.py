import time

from utils.krea_client import get_api_token
import requests


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
                return job["result"]["video_url"]
            raise RuntimeError(f"Job failed: {job.get('status')}")

        if "progress" in job:
            print(f"Progress: {job['progress']}%")
        else:
            print(f"Status: {job.get('status')}")

        time.sleep(5)


def main() -> None:
    api_base = "https://api.krea.ai"
    api_token = get_api_token()

    prompt = "a majestic eagle soaring over snow-capped mountains at sunrise"
    duration = 5
    width = 1280
    height = 720
    fps = 24

    response = requests.post(
        f"{api_base}/generate/video/kling/kling-2.5",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        json={
            "prompt": prompt,
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
        },
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
