"""
Fetch missing Holded images → JSON {res_id: base64_jpeg}
Resize 1200x1200 JPEG quality 82.
"""
import base64, csv, io, json, os, sys
from typing import Optional
import requests
from PIL import Image

API_KEY = os.environ["HOLDED_API_KEY"]
BASE = "https://api.holded.com/api/invoicing/v1"
HEADERS = {"key": API_KEY, "Accept": "application/json"}
TARGET = (1200, 1200)
QUALITY = 82

def fetch(holded_id):
    url = f"{BASE}/products/{holded_id}/image"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and r.headers.get("content-type","").startswith("image/"):
            return r.content
        if r.status_code == 200:
            try:
                j = r.json()
                if isinstance(j, dict) and "image" in j:
                    return base64.b64decode(j["image"])
            except Exception:
                pass
        # 400 "product without image" or 404 — no image
        return None
    except Exception as e:
        print(f"  [err {holded_id}] {e}", file=sys.stderr)
        return None

def to_jpeg_b64(raw):
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA","LA","P"):
        img = img.convert("RGB")
    img.thumbnail(TARGET, Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=QUALITY, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")

results = {"ok":[], "no_image":[], "err":[]}
out_data = {}

with open("/tmp/holded-ids.csv","r") as f:
    rows = list(csv.DictReader(f))

print(f"Total: {len(rows)}", flush=True)
for i, row in enumerate(rows, 1):
    hid = row["holded_id"].strip()
    res_id = int(row["res_id"])
    name = row["Name"]
    print(f"[{i}/{len(rows)}] {hid} ({res_id}) {name}", flush=True)
    raw = fetch(hid)
    if raw is None:
        results["no_image"].append({"res_id":res_id,"name":name,"holded_id":hid})
        continue
    try:
        b64 = to_jpeg_b64(raw)
        out_data[str(res_id)] = {"holded_id":hid,"name":name,"image_b64":b64,"size":len(b64)}
        results["ok"].append({"res_id":res_id,"name":name,"size":len(b64)})
    except Exception as e:
        print(f"  [err encode] {e}", file=sys.stderr)
        results["err"].append({"res_id":res_id,"name":name,"error":str(e)})

with open("/tmp/images.json","w") as f:
    json.dump(out_data, f)
with open("/tmp/results.json","w") as f:
    json.dump(results, f, indent=2)

print(f"\n=== SUMMARY ===")
print(f"OK: {len(results['ok'])}")
print(f"No image in Holded: {len(results['no_image'])}")
print(f"Errors: {len(results['err'])}")
print(f"Total b64 size: {sum(d['size'] for d in out_data.values())} bytes")
