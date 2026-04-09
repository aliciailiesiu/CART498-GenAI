import os
from pathlib import Path

from openai import OpenAI


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


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))

    client = OpenAI()
    response = client.responses.create(
        model="gpt-5.2",
        input="Write a one-sentence bedtime story about a unicorn.",
    )
    print(response.output_text)


if __name__ == "__main__":
    main()
