"""
Image Import from Holded API → Odoo CSV

Purpose:
    Fetches product images directly from Holded API endpoint
    /products/{id}/image, resizes to 1200x1200 JPEG quality 82,
    writes to CSV for Odoo import.

Why this separate script:
    Holded UI links (holded.com/...) require login and redirect through
    authenticated pages. The API endpoint /products/{id}/image returns
    raw binary directly with just API key auth — much more reliable.

Input:
    holded-ids.csv — CSV with columns:
        - 'holded_id' (the Holded product ID)
        - 'External ID' (target Odoo external ID)
        - 'Name'

Output:
    odoo_images_from_holded.csv — ready for Odoo import

Dependencies:
    pip install requests pillow

Env:
    HOLDED_API_KEY — API key from Holded account settings

Usage:
    HOLDED_API_KEY=xxx python image_import_from_holded_api.py
"""

import base64
import csv
import io
import os
from typing import Optional

import requests
from PIL import Image

INPUT_CSV = "holded-ids.csv"
OUTPUT_CSV = "odoo_images_from_holded.csv"
TARGET_SIZE = (1200, 1200)
JPEG_QUALITY = 82

HOLDED_API_KEY = os.environ.get("HOLDED_API_KEY")
if not HOLDED_API_KEY:
    raise RuntimeError("Set HOLDED_API_KEY env variable")

HOLDED_API_BASE = "https://api.holded.com/api/invoicing/v1"
HEADERS = {
    "key": HOLDED_API_KEY,
    "Accept": "application/json",
}


def fetch_image(holded_id: str) -> Optional[bytes]:
    """GET /products/{id}/image → raw bytes."""
    url = f"{HOLDED_API_BASE}/products/{holded_id}/image"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        # API may return JSON with base64 or raw binary depending on setup
        if resp.headers.get("content-type", "").startswith("image/"):
            return resp.content
        # JSON fallback
        try:
            j = resp.json()
            if isinstance(j, dict) and "image" in j:
                return base64.b64decode(j["image"])
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"  [error] holded_id={holded_id}: {e}")
        return None


def process_image(raw: bytes) -> Optional[str]:
    """Resize + JPEG 82 + base64."""
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception as e:
        print(f"  [error] processing: {e}")
        return None


def main():
    ok_count = 0
    err_count = 0

    with open(INPUT_CSV, "r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["External ID", "Name", "Image"])

            for row in reader:
                holded_id = row.get("holded_id", "").strip()
                ext_id = row.get("External ID", "").strip()
                name = row.get("Name", "").strip()

                if not holded_id or not ext_id:
                    continue

                print(f"Fetching {holded_id} → {ext_id} ({name})")
                raw = fetch_image(holded_id)
                if not raw:
                    err_count += 1
                    continue

                b64 = process_image(raw)
                if not b64:
                    err_count += 1
                    continue

                writer.writerow([ext_id, name, b64])
                ok_count += 1

    print(f"\nDone. OK: {ok_count}, Errors: {err_count}")
    print(f"Output: {OUTPUT_CSV}")
    print("Next step: run split_big_csv.py for batched import.")


if __name__ == "__main__":
    main()
