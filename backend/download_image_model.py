"""Download pinned, data-only classifier assets. No uploaded image leaves this PC."""
from pathlib import Path
from huggingface_hub import snapshot_download
from app.core.config import settings


def main():
    destination = Path(settings.AI_IMAGE_MODEL_PATH)
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=settings.AI_IMAGE_MODEL_ID,
        revision=settings.AI_IMAGE_MODEL_REVISION,
        local_dir=str(destination),
        allow_patterns=['config.json', 'preprocessor_config.json', 'model.safetensors', 'README.md'],
    )
    print(f'Whole-image classifier saved to {destination}')


if __name__ == '__main__':
    main()
