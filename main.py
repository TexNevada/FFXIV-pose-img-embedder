from flask import Flask, request, send_file, render_template
import base64
import json
import requests
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError
import io
app = Flask(__name__)


def fetch_file_from_url(url: str):  # -> (bytes, str):
    r = requests.get(url)
    r.raise_for_status()

    parsed = urlparse(url)
    filename = Path(parsed.path).name or "downloaded.pose"

    return r.content, filename


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():

    # ----- IMAGE -----
    img_url = request.form.get("image_url", "").strip()
    img_file = request.files.get("image_file")

    if img_file and img_file.filename:
        image_bytes = img_file.read()
    elif img_url:
        image_bytes, _ = fetch_file_from_url(img_url)
    else:
        return "Error: No image provided (URL or file)", 400

    # Verify image type using Pillow
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_format = (img.format or "").lower()
    except UnidentifiedImageError:
        return "Error: Provided image is not a supported image type", 400

    allowed_img_types = {"png", "jpeg", "gif", "bmp", "webp"}
    if img_format not in allowed_img_types:
        return "Error: Provided image is not a supported image type", 400

    b64_str = image_to_base64(image_bytes)

    # ----- POSE FILE -----
    pose_url = request.form.get("pose_url", "").strip()
    pose_file = request.files.get("pose_file")

    if pose_file and pose_file.filename:
        pose_bytes = pose_file.read()
        pose_filename = pose_file.filename
    elif pose_url:
        pose_bytes, pose_filename = fetch_file_from_url(pose_url)
    else:
        return "Error: No pose file provided (URL or file)", 400

    if not pose_filename:
        pose_filename = "updated.pose"

    # Require .pose extension
    if not pose_filename.lower().endswith(".pose"):
        return "Error: Pose file must have .pose extension", 400

    # Ensure pose file is not an image
    try:
        with Image.open(io.BytesIO(pose_bytes)):
            return "Error: Pose file appears to be an image; expected JSON .pose", 400
    except UnidentifiedImageError:
        pass

    # Ensure pose file is valid JSON
    try:
        pose_json = json.loads(pose_bytes.decode("utf-8"))
    except Exception:
        return "Error: Pose file is not valid JSON", 400

    pose_json["Base64Image"] = b64_str

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pose")
    temp.write(json.dumps(pose_json, indent=2).encode("utf-8"))
    temp.close()

    return send_file(
        temp.name,
        as_attachment=True,
        download_name=pose_filename,
        mimetype="application/json"
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80, threaded=True)
