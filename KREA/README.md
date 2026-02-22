# Krea Playground

Minimal structure to keep multiple experiments organized while sharing config.

## Structure

- `app.py` – Flask demo (text → image) with local HTML UI.
- `experiments/text_to_image.py` – Script version with prompt input and download.
- `experiments/text_to_video.py` – Text → video experiment.
- `utils/krea_client.py` – Shared helpers (auth, create job, polling, download).
- `.env` – Store your key as `KREA_CART=...`.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run

Flask UI:

```bash
python app.py
```

Script:

```bash
python experiments/text_to_image.py
```

Text → video:

```bash
python experiments/text_to_video.py
```
