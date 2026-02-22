from utils.krea_client import create_job, download_image, get_api_token, wait_for_job


def main() -> None:
    api_base = "https://api.krea.ai"
    api_token = get_api_token()

    prompt = input("Enter a prompt: ").strip() or "a serene mountain landscape at sunset"
    width = 1024
    height = 576
    steps = 28

    job = create_job(api_base, api_token, prompt, width, height, steps)
    job_id = job.get("job_id")
    if not job_id:
        raise RuntimeError(f"Missing job_id in response: {job}")

    image_url = wait_for_job(api_base, api_token, job_id)
    print(f"Image ready: {image_url}")

    file_path = download_image(image_url, filename_base="images")
    print(f"Saved image to {file_path}")


if __name__ == "__main__":
    main()
