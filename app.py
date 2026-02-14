import json
import os
import tempfile
import time
import uuid

import cloudinary
import cloudinary.uploader
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY")  # custom key clients must send
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AVATAR_ENDPOINT = os.getenv("AZURE_AVATAR_ENDPOINT", "").rstrip("/")
API_VERSION = "2024-08-01"

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

for var in ("API_KEY", "AZURE_SPEECH_KEY", "AZURE_AVATAR_ENDPOINT",
            "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
    if not os.getenv(var):
        raise RuntimeError(f"Missing env var: {var}")

app = Flask(__name__)
CORS(app)

# ── Available models & voices ────────────────────────────────────────────
AVATARS = {
    "harry": ["business", "casual", "youthful"],
    "jeff": ["business", "formal"],
    "lisa": ["casual-sitting", "graceful-sitting", "graceful-standing", "technical-sitting", "technical-standing"],
    "lori": ["casual", "graceful", "formal"],
    "max": ["business", "casual", "formal"],
    "meg": ["formal", "casual", "business"],
}

VOICES = {
    "female": ["th-TH-PremwadeeNeural", "th-TH-AcharaNeural"],
    "male": ["th-TH-NiwatNeural"],
}

ALL_VOICES = [v for vs in VOICES.values() for v in vs]


# ── Helpers ──────────────────────────────────────────────────────────────
def _azure_headers():
    return {
        "Ocp-Apim-Subscription-Key": SPEECH_KEY,
        "Content-Type": "application/json",
    }


def create_avatar_job(text: str, voice: str = "th-TH-NiwatNeural",
                     character: str = "harry", style: str = "casual",
                     background: str | None = None) -> str:
    """Submit a batch avatar synthesis job. Returns the job ID."""
    job_id = str(uuid.uuid4())
    url = f"{AVATAR_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"

    avatar_config = {
        "talkingAvatarCharacter": character,
        "talkingAvatarStyle": style,
        "customized": False,
        "videoFormat": "mp4",
        "videoCodec": "h264",
        "subtitleType": "soft_embedded",
        "useBuiltInVoice": False,
    }

    if background:
        avatar_config["backgroundImage"] = background
    else:
        avatar_config["backgroundColor"] = "#FFFFFFFF"  # solid white

    payload = {
        "inputKind": "PlainText",
        "synthesisConfig": {"voice": voice},
        "customVoices": {},
        "inputs": [{"content": text}],
        "avatarConfig": avatar_config,
    }

    resp = requests.put(url, data=json.dumps(payload), headers=_azure_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"Azure job creation failed [{resp.status_code}]: {resp.text}")
    return job_id


def poll_avatar_job(job_id: str, timeout: int = 600, interval: int = 5) -> str:
    """Poll until the job succeeds (or fails). Returns the video download URL."""
    url = f"{AVATAR_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"
    headers = {"Ocp-Apim-Subscription-Key": SPEECH_KEY}
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "Succeeded":
            video_url = data.get("outputs", {}).get("result")
            if not video_url:
                raise RuntimeError("Job succeeded but no result URL found")
            return video_url
        if status == "Failed":
            raise RuntimeError(f"Avatar job failed: {json.dumps(data, indent=2)}")

        time.sleep(interval)

    raise TimeoutError(f"Avatar job {job_id} did not finish within {timeout}s")


def download_file(url: str) -> str:
    """Download a file to a temp path and return that path."""
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    for chunk in resp.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name


def upload_to_cloudinary(file_path: str) -> str:
    """Upload a video file to Cloudinary as restricted. Returns the secure URL."""
    result = cloudinary.uploader.upload(
        file_path,
        resource_type="video",
        folder="avatar_videos",
        type="authenticated",
    )
    return result["secure_url"]


# ── Routes ───────────────────────────────────────────────────────────────
@app.route("/generate-avatar", methods=["POST"])
def generate_avatar():
    # --- Auth ---
    provided_key = request.headers.get("X-API-Key") or request.json.get("key")
    if provided_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401

    # --- Validate input ---
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Missing 'text' field"}), 400

    voice = data.get("voice", "th-TH-NiwatNeural")
    character = data.get("talkingAvatarCharacter", "harry")
    style = data.get("talkingAvatarStyle", "casual")
    background = data.get("background")  # optional Cloudinary image URL

    # --- Validate voice ---
    if voice not in ALL_VOICES:
        return jsonify({"error": f"Invalid voice '{voice}'. See GET /voices for options."}), 400

    # --- Validate avatar character & style ---
    if character not in AVATARS:
        return jsonify({"error": f"Invalid character '{character}'. See GET /models for options."}), 400
    if style not in AVATARS[character]:
        return jsonify({"error": f"Invalid style '{style}' for character '{character}'. Valid: {AVATARS[character]}"}), 400

    try:
        # 1. Submit Azure avatar job
        job_id = create_avatar_job(text, voice=voice, character=character, style=style, background=background)

        # 2. Poll until done
        video_url = poll_avatar_job(job_id)

        # 3. Download the video
        local_path = download_file(video_url)

        # 4. Upload to Cloudinary
        cloudinary_url = upload_to_cloudinary(local_path)

        # 5. Cleanup temp file
        os.unlink(local_path)

        return jsonify({
            "success": True,
            "video_url": cloudinary_url,
            "job_id": job_id,
        })

    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/models", methods=["GET"])
def models():
    return jsonify({"avatars": AVATARS})


@app.route("/voices", methods=["GET"])
def voices():
    return jsonify({"voices": VOICES})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3300, debug=True)