"""
preprocessor.py
---------------
Takes raw scraper output, downloads all images to /data/images/,
and saves a preprocessed payload that fact_checker.py consumes.
"""

import os
import json
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO

# ==============================
# Paths
# ==============================
DATA_DIR   = Path("data")
IMAGE_DIR  = DATA_DIR / "images"
RAW_PATH   = DATA_DIR / "post_data.json"
PREP_PATH  = DATA_DIR / "preprocessed.json"


def setup_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)


def download_image(url: str, filename: str) -> str | None:
    """
    Downloads an image from a URL, saves it locally.
    Returns the local file path, or None if it failed.
    """
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        save_path = IMAGE_DIR / filename
        img.save(save_path, format="JPEG")
        print(f"  [Preprocessor] Saved image → {save_path}")
        return str(save_path)
    except Exception as e:
        print(f"  [Preprocessor] Failed to download {url[:60]}... → {e}")
        return None


def preprocess(post_data: dict) -> dict:
    """
    Main preprocessing function.
    - Saves raw post data to data/post_data.json
    - Downloads all images to data/images/
    - Returns a preprocessed dict ready for fact_checker.py
    """
    setup_dirs()

    # Save raw scraper output
    with open(RAW_PATH, "w") as f:
        json.dump(post_data, f, indent=4)
    print(f"[Preprocessor] Raw data saved → {RAW_PATH}")

    # Download images
    local_images = []
    image_urls   = []

    for i, url in enumerate(post_data.get("media_urls", [])):
        # Skip video URLs (they end in .mp4 or come from video_url fields)
        # For single-video posts, is_video is True and there's only 1 media
        if post_data.get("is_video") and len(post_data.get("media_urls", [])) == 1:
            print(f"  [Preprocessor] Skipping video post")
            continue

        filename = f"image_{post_data['shortcode']}_{i+1}.jpg"
        local_path = download_image(url, filename)

        if local_path:
            local_images.append(local_path)
            image_urls.append(url)

    # Build preprocessed payload
    preprocessed = {
        "url":            post_data["url"],
        "shortcode":      post_data["shortcode"],
        "owner_username": post_data["owner_username"],
        "caption":        post_data["caption"],
        "hashtags":       post_data["hashtags"],
        "mentions":       post_data["mentions"],
        "likes":          post_data["likes"],
        "comments_count": post_data["comments_count"],
        "timestamp":      post_data["timestamp"],
        "location":       post_data["location"],
        "is_video":       post_data["is_video"],
        "image_urls":     image_urls,
        "local_images":   local_images,   # ← fact_checker reads these
    }

    # Save preprocessed payload
    with open(PREP_PATH, "w") as f:
        json.dump(preprocessed, f, indent=4)
    print(f"[Preprocessor] Preprocessed data saved → {PREP_PATH}")
    print(f"[Preprocessor] {len(local_images)} image(s) ready for analysis.")

    return preprocessed