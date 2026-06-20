#!/usr/bin/env python
"""
Download GGUF model weights for Arapai (not stored in Git).

Usage (from project root, venv active):
    python scripts/download_models.py              # audit default: light tier only
    python scripts/download_models.py --tier all     # light + standard + advanced
    python scripts/download_models.py --tier standard
"""
import argparse
import json
import os
import sys
import urllib.request

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "models", "MODEL_MANIFEST.json")


def load_manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def download_file(url, dest_path, label):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"[skip] {label}: already exists ({size_mb:.1f} MB) -> {dest_path}")
        return dest_path

    print(f"[download] {label}")
    print(f"  from: {url}")
    print(f"  to:   {dest_path}")

    def progress(block_num, block_size, total_size):
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        pct = min(100, downloaded * 100 / total_size)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        print(f"\r  progress: {pct:.1f}% ({mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)

    tmp_path = dest_path + ".part"
    urllib.request.urlretrieve(url, tmp_path, reporthook=progress)
    print()
    os.replace(tmp_path, dest_path)
    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"[done] {label}: {size_mb:.1f} MB")
    return dest_path


def main():
    parser = argparse.ArgumentParser(description="Download Arapai GGUF model weights")
    parser.add_argument(
        "--tier",
        default="light",
        choices=["light", "standard", "advanced", "all"],
        help="Which tier to download (default: light — required for ADTC audit)",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    models = manifest["models"]

    if args.tier == "all":
        tiers = ["light", "standard", "advanced"]
    else:
        tiers = [args.tier]

    print("Arapai model downloader")
    print(f"Project root: {PROJECT_ROOT}\n")

    for tier in tiers:
        spec = models[tier]
        dest = os.path.join(PROJECT_ROOT, spec["dest_path"])
        download_file(spec["direct_url"], dest, spec["display_name"])
        if tier == "light":
            adtc_dest = os.path.join(PROJECT_ROOT, "model", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
            if not os.path.exists(adtc_dest) or os.path.getsize(adtc_dest) != os.path.getsize(dest):
                os.makedirs(os.path.dirname(adtc_dest), exist_ok=True)
                import shutil
                shutil.copy2(dest, adtc_dest)
                print(f"[sync] ADTC path: {adtc_dest}")

    audit = manifest["audit_file"]
    print(f"\nAudit default model path: {audit}")
    print("Run: streamlit run app.py  (Mode: Offline, Model: Light)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
