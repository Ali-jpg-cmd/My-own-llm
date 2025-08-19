#!/usr/bin/env python3
"""
Download a small GGUF model for local llama.cpp inference (free).
Default: TinyLlama 1.1B Chat Q4_K_M (~0.7 GB).
"""

import os
import sys
from pathlib import Path
import httpx

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        done = int(50 * downloaded / total)
                        sys.stdout.write("\r[{}{}] {}%".format("#"*done, "."*(50-done), int(downloaded*100/total)))
                        sys.stdout.flush()
    print("\nDownloaded:", dest)

if __name__ == "__main__":
    # TinyLlama 1.1B Chat v1.0 Q4_K_M GGUF (from Hugging Face via direct link)
    # You can replace with another GGUF link if preferred.
    url = (
        "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/"
        "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf?download=true"
    )
    models_dir = Path(__file__).resolve().parent.parent / "models"
    dest = models_dir / "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"
    print("Downloading TinyLlama GGUF to:", dest)
    download(url, dest)
    print("Done. Set LLM_MODEL_PATH to:", dest)
