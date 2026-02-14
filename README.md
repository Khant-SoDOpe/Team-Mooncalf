# Team Mooncalf — Avatar Video API v0.1

A Flask API that converts Thai text into a talking avatar video using **Azure Text-to-Speech Avatar**, then uploads the result to **Cloudinary** and returns a shareable video link.

## Features

- POST endpoint accepts Thai text and generates an avatar video
- API key authentication
- Auto-uploads generated video to Cloudinary
- Returns a direct Cloudinary video URL

## Prerequisites

- Python 3.8+
- Azure Speech Service (S0 tier, Southeast Asia region)
- Cloudinary account

## Setup

### 1. Clone & install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
AZURE_SPEECH_KEY="your-azure-speech-key"
AZURE_SPEECH_REGION="southeastasia"
AZURE_AVATAR_ENDPOINT="https://southeastasia.api.cognitive.microsoft.com/"

API_KEY="your-secret-api-key"

CLOUDINARY_CLOUD_NAME="your-cloud-name"
CLOUDINARY_API_KEY="your-cloudinary-api-key"
CLOUDINARY_API_SECRET="your-cloudinary-api-secret"
```

### 3. Run the server

```bash
python app.py
```

Server starts at `http://localhost:3300`.

## API Endpoints

### `GET /health`

Health check.

**Response:**
```json
{ "status": "ok" }
```

### `POST /generate-avatar`

Generate an avatar video from Thai text.

**Headers:**

| Header         | Description                          |
| -------------- | ------------------------------------ |
| `Content-Type` | `application/json` (required)        |
| `X-API-Key`    | Your API key (or send `key` in body) |

**Request body:**

```json
{
  "key": "your-secret-api-key",
  "text": "สวัสดีค่ะ ฉันเจ็บหน้าอกและหายใจไม่ออก"
}
```

**Success response (200):**

```json
{
  "success": true,
  "video_url": "https://res.cloudinary.com/.../avatar_videos/xxxx.mp4",
  "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

**Error responses:**

| Status | Reason                        |
| ------ | ----------------------------- |
| 400    | Missing `text` field          |
| 401    | Invalid or missing API key    |
| 502    | Azure avatar generation error |
| 504    | Job timed out                 |

## Project Structure

```
├── app.py              # Flask API server
├── a.py                # Standalone avatar generation script
├── tts_azure.py        # Text-to-speech (audio only) script
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
└── README.md
```

## Notes

- The `/generate-avatar` request can take **several minutes** to respond because it waits for Azure to finish rendering the avatar video.
- Azure batch avatar synthesis is only available in **West US 2**, **West Europe**, and **Southeast Asia** regions.
- A **paid (S0) Azure Speech** resource is required — the free tier does not support avatar synthesis.

## Version

**v0.1** — Initial release
