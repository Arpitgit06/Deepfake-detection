"""
Downloads the Qwen3-4B-Instruct-2507 (Q8_0 GGUF) model into the project folder.

Used by setup.bat. Downloads to:  <project>/backend/models/llm/
Skips the download when the file is already present.

Size: ~4.0 GB (Q8_0 quantization) - fits comfortably in 8 GB VRAM with room
for the KV cache.
"""

import shutil
import sys
from pathlib import Path

REPO_ID = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
FILENAME = "Qwen3-4B-Instruct-2507-Q8_0.gguf"
MIN_VALID_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB sanity check for a 4 GB Q8 model

BACKEND_DIR = Path(__file__).resolve().parent
MODELS_DIR = BACKEND_DIR / "models" / "llm"
TARGET = MODELS_DIR / FILENAME


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET.exists() and TARGET.stat().st_size >= MIN_VALID_BYTES:
        size_gb = TARGET.stat().st_size / (1024 ** 3)
        print(f"[OK] LLM already downloaded: {TARGET} ({size_gb:.2f} GB) - skipping.")
        return 0

    print(f"[INFO] Downloading {REPO_ID}/{FILENAME}")
    print(f"[INFO] Target folder: {MODELS_DIR}")
    print(f"[INFO] This is a ~4 GB download - it may take a while. It resumes automatically if interrupted.")
    print()

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[ERROR] huggingface_hub is not installed. Run: pip install huggingface_hub")
        return 1

    try:
        path = hf_hub_download(
            repo_id=REPO_ID,
            filename=FILENAME,
            local_dir=str(MODELS_DIR),
        )
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print("[INFO] Check your internet connection and try again. Partial downloads resume.")
        return 1

    # Make sure the file sits exactly where the backend expects it
    downloaded = Path(path)
    if downloaded != TARGET:
        if TARGET.exists():
            TARGET.unlink()
        shutil.move(str(downloaded), str(TARGET))

    size_gb = TARGET.stat().st_size / (1024 ** 3)
    if size_gb < MIN_VALID_BYTES / (1024 ** 3):
        print(f"[ERROR] Downloaded file looks incomplete ({size_gb:.2f} GB). Delete it and re-run.")
        return 1

    print()
    print(f"[OK] LLM downloaded successfully: {TARGET} ({size_gb:.2f} GB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
