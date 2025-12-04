from flask import Flask, request, send_file, render_template
import base64
import json
import requests
import tempfile
from pathlib import Path
from urllib.parse import urlparse

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
    # TODO: Make checks to avoid pngs used for .pose and vice versa AKA SECURITY.. Don't be lazy
    # ----- IMAGE -----
    img_url = request.form.get("image_url", "").strip()
    img_file = request.files.get("image_file")

    if img_file and img_file.filename:
        image_bytes = img_file.read()
    elif img_url:
        image_bytes, _ = fetch_file_from_url(img_url)
    else:
        return "Error: No image provided (URL or file)", 400

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

    pose_json = json.loads(pose_bytes.decode("utf-8"))
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
