"""
scraper.py
----------
Scrapes an Instagram post and returns structured data.
Called by main.py
"""

import instaloader
import json
import re
from urllib.parse import urlparse

# ==============================
# Initialize Instaloader
# ==============================
L = instaloader.Instaloader(
    download_comments=False,
    save_metadata=False,
    compress_json=False
)

# Uncomment to login (recommended to avoid rate limits):
# L.login("your_username", "your_password")


class VideoPostError(Exception):
    """Raised when a post is a video/reel (not yet supported)."""
    pass


def get_shortcode_from_url(url: str) -> str:
    """Extract shortcode from Instagram URLs.
    Handles both formats:
      - https://www.instagram.com/p/ABC123/
      - https://www.instagram.com/username/p/ABC123/
      - https://www.instagram.com/reel/ABC123/
    """
    path = urlparse(url).path.strip("/")
    parts = path.split("/")

    # Detect reel/tv URLs early
    for i, segment in enumerate(parts):
        if segment in ("reel", "tv") and i + 1 < len(parts):
            raise VideoPostError(
                "This is a video/reel post. "
                "We currently support only image-based posts. "
                "Video & reel fact-checking is under development — stay tuned!"
            )

    # Find the segment after 'p'
    for i, segment in enumerate(parts):
        if segment == "p" and i + 1 < len(parts):
            return parts[i + 1]

    raise ValueError(f"Could not extract shortcode from URL: {url}")


def extract_tags(text: str) -> tuple[list, list]:
    hashtags = re.findall(r"#\w+", text)
    mentions = re.findall(r"@\w+", text)
    return hashtags, mentions


def scrape(url: str) -> dict:
    """
    Scrapes the Instagram post at the given URL.
    Returns a dict with post metadata and media URLs.
    """
    print(f"[Scraper] Fetching post: {url}")
    shortcode = get_shortcode_from_url(url)
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    caption = post.caption or ""
    hashtags, mentions = extract_tags(caption)

    # Reject pure video posts (single video, not a carousel with images)
    if post.is_video and post.typename != "GraphSidecar":
        raise VideoPostError(
            "This is a video post. "
            "We currently support only image-based posts. "
            "Video & reel fact-checking is under development — stay tuned!"
        )

    data = {
        "shortcode":      post.shortcode,
        "url":            url,
        "owner_username": post.owner_username,
        "caption":        caption,
        "hashtags":       hashtags,
        "mentions":       mentions,
        "likes":          post.likes,
        "comments_count": post.comments,
        "is_video":       post.is_video,
        "media_urls":     [],
        "timestamp":      str(post.date_utc),
        "location":       post.location.name if post.location else None
    }

    # Collect media URLs
    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            data["media_urls"].append(
                node.video_url if node.is_video else node.display_url
            )
    else:
        data["media_urls"].append(
            post.video_url if post.is_video else post.url
        )

    print(f"[Scraper] Done. Found {len(data['media_urls'])} media item(s).")
    return data