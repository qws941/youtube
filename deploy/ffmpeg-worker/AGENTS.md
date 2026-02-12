# FFMPEG WORKER

**Purpose:** Remote FFmpeg processing worker — offloads video composition from main pipeline

## OVERVIEW

FastAPI service on Proxmox CT 201 (`192.168.50.201:8000`). Receives composition jobs, processes via FFmpeg, stores results in MinIO.

## KEY FILES

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, endpoints, MinIO client |
| `worker.py` | FFmpeg subprocess execution |
| `Dockerfile` | Container build with FFmpeg |
| `requirements.txt` | FastAPI, python-multipart, minio |

## ENDPOINTS

- `POST /compose` — Submit composition job (audio + visuals + config)
- `GET /status/{job_id}` — Check job status
- `GET /health` — Health check

## STORAGE

MinIO at `192.168.50.109`:
- Bucket: `youtube-videos`
- Input: audio files, image/video clips uploaded before job
- Output: composed video stored, URL returned

## DEPLOYMENT

```bash
docker build -t ffmpeg-worker .
docker run -p 8000:8000 --env-file .env ffmpeg-worker
```

Required env: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
