# Krea Playground Docs

This document explains what each Python file does and how to run it.

## app.py (Flask Web UI)

What it does:
- Starts a local Flask server on `http://127.0.0.1:5000`.
- Serves `index.html` for the browser UI.
- Exposes API routes:
  - `POST /generate/image` for text → image (Flux).
  - `POST /generate/video` for text → video and image → video (Kling).
- Polls Krea jobs until they complete and returns the final URL to the browser.

Key functions:
- `wait_for_job(...)` polls `/jobs/{job_id}` and extracts a result URL.
- `generate_image()` sends prompt + size + steps to Flux.
- `generate_video()` sends prompt + size + duration + fps + motion_strength (+ optional image_base64) to Kling.

Run:
```bash
python app.py
```
Then open `http://127.0.0.1:5000`.

---

## utils/krea_client.py (Shared Helpers)

What it does:
- Centralizes auth and helper logic for scripts.

Functions:
- `get_api_token()` reads `KREA_CART` from `.env`.
- `create_job()` creates a Flux text → image job.
- `wait_for_job()` polls until a job completes.
- `download_image()` downloads and saves the image locally.

---

## experiments/text_to_image.py (Script)

What it does:
- Prompts in the terminal for a text prompt.
- Generates an image via Flux.
- Polls until done, prints the URL, and downloads the file.

Run:
```bash
python experiments/text_to_image.py
```

---

## experiments/text_to_video.py (Script)

What it does:
- Sends prompt + duration + size + fps to Kling.
- Polls until done and prints the video URL.

Run:
```bash
python experiments/text_to_video.py
```

---

## experiments/image_to_video.py (Script)

What it does:
- Sends a reference image + prompt to Kling.
- Polls until done and prints the video URL.

Two options for input:
- Use a **public image URL** (`image_url`).
- Use a **local image file** (base64) if the API supports it.

Run:
```bash
python experiments/image_to_video.py
```

---

## .env

Store your API key:
```
KREA_CART=your_real_key_here
```

`.env` is ignored by Git via `.gitignore`.

---

## Model Architecture, Training, and Notable Innovations

This project is an **API client**. It does not implement ML models itself; it calls Krea’s hosted models and returns URLs. The details below reflect **publicly documented** information from model owners and Krea’s API docs.

### FLUX (Text → Image, `bfl/flux-1-dev`)

**Architecture / Lineage**
- Black Forest Labs states that **FLUX.1 [dev]** is an **open‑weight, guidance‑distilled model** derived from **FLUX.1 [pro]**. citeturn0search4

**Training (Datasets / Methods / Compute)**
- Public sources do **not** disclose full datasets or compute budgets for FLUX.1 [dev]. citeturn0search4

**Notable Innovations**
- The key documented innovation is **guidance distillation** from FLUX.1 [pro] to improve efficiency while retaining prompt adherence/quality. citeturn0search4

**Krea API Reference**
- Krea’s API exposes Flux via `POST /generate/image/bfl/flux-1-dev`. citeturn0search6

### Kling 2.5 (Text → Video, Image → Video)

**Architecture / Lineage**
- Kuaishou’s public announcement describes **Kling 2.5** as a major upgrade for **text‑to‑video and image‑to‑video quality**, but does **not** publish detailed architecture diagrams or training specifics. citeturn1search6
- Krea lists **Kling 2.5** as an available video model and supports text‑to‑video and image‑to‑video workflows in the product. citeturn1search0

**Training (Datasets / Methods / Compute)**
- No official public details are provided in Kuaishou’s announcement or Krea’s model page regarding datasets or compute budgets. citeturn1search6turn1search0

**Notable Innovations**
- Public sources emphasize **improved quality and performance**, especially for fast motion and physics‑like realism, but do not expose low‑level algorithmic details. citeturn1search0turn1search6

**Krea API Context**
- The app calls Krea’s Kling endpoint for video generation (configured in `app.py`). citeturn1search0
