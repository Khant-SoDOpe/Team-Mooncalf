# Team Mooncalf — Azure Talking Avatar API

A Flask API that generates talking avatar videos from Thai text using **Azure Speech Service**, uploads them to **Cloudinary** (authenticated/restricted), and returns a video link.

## Features

- Generate talking avatar videos from Thai text
- 6 avatar characters with multiple styles
- Thai voice options (male & female)
- API key authentication
- Authenticated Cloudinary video storage
- Discovery endpoints for available models & voices

## Prerequisites

- Python 3.8+
- Azure Speech Service (**S0 tier**, Southeast Asia region)
- Cloudinary account

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file:

```env
API_KEY=your_api_key
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_AVATAR_ENDPOINT=https://southeastasia.api.cognitive.microsoft.com
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_key
CLOUDINARY_API_SECRET=your_cloudinary_secret
```

### 3. Run the server

```bash
python3 app.py
```

Server starts at `http://localhost:3300`.

---

## API Endpoints

### `GET /health`

Health check.

**Response:**
```json
{ "status": "ok" }
```

---

### `GET /models`

List available avatar characters and their styles.

**Response:**
```json
{
  "avatars": {
    "harry": ["business", "casual", "youthful"],
    "jeff": ["business", "formal"],
    "lisa": ["casual-sitting", "graceful-sitting", "graceful-standing", "technical-sitting", "technical-standing"],
    "lori": ["casual", "graceful", "formal"],
    "max": ["business", "casual", "formal"],
    "meg": ["formal", "casual", "business"]
  }
}
```

---

### `GET /voices`

List available Thai voices grouped by gender.

**Response:**
```json
{
  "voices": {
    "female": ["th-TH-PremwadeeNeural", "th-TH-AcharaNeural"],
    "male": ["th-TH-NiwatNeural"]
  }
}
```

---

### `POST /generate-avatar`

Generate a talking avatar video from text.

**Authentication:** Pass your API key via `X-API-Key` header or `key` in the JSON body.

**Request body:**

```json
{
  "key": "your_api_key",
  "text": "สวัสดีครับ ยินดีต้อนรับ",
  "voice": "th-TH-NiwatNeural",
  "talkingAvatarCharacter": "harry",
  "talkingAvatarStyle": "casual"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | **Yes** | — | Thai text for the avatar to speak |
| `key` | string | No* | — | API key (alternative to `X-API-Key` header) |
| `voice` | string | No | `th-TH-NiwatNeural` | Voice name (see `GET /voices`) |
| `talkingAvatarCharacter` | string | No | `harry` | Avatar character (see `GET /models`) |
| `talkingAvatarStyle` | string | No | `casual` | Avatar style (must be valid for the chosen character) |

**Success response (200):**

```json
{
  "success": true,
  "video_url": "https://res.cloudinary.com/.../avatar_videos/xyz.mp4",
  "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

**Error responses:**

| Status | Reason |
|--------|--------|
| 400 | Missing text, invalid voice / character / style |
| 401 | Missing or invalid API key |
| 502 | Azure job creation or processing failed |
| 504 | Job timed out (>600s) |

---

## Project Structure

```
├── app.py              # Flask API server
├── .env                # Environment variables (not committed)
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment config
└── README.md
```

## Notes

- The `/generate-avatar` request can take **several minutes** because it waits for Azure to finish rendering the avatar video.
- Azure batch avatar synthesis is available in **West US 2**, **West Europe**, and **Southeast Asia** regions.
- A **paid (S0) Azure Speech** resource is required — the free tier does not support avatar synthesis.
- Cloudinary videos are uploaded as **authenticated** (restricted access).

## Tech Stack

- **Python 3** + **Flask**
- **Azure Speech Service** — Batch Avatar Synthesis API (v2024-08-01)
- **Cloudinary** — Video hosting (authenticated/restricted)
