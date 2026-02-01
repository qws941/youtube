# FFmpeg Worker API (VM 200)

n8n에서 호출할 FFmpeg 영상 합성 API 설계

## 엔드포인트

### POST /api/compose

영상 합성 요청

**Request:**
```json
{
  "audioUrl": "https://minio.jclee.me/youtube-assets/audio.mp3",
  "scenes": [
    {
      "imageUrl": "https://replicate.delivery/xxx.png",
      "sceneIndex": 0,
      "duration": 60
    }
  ],
  "outputFormat": "mp4",
  "resolution": "1920x1080",
  "fps": 30,
  "transitions": "crossfade"
}
```

**Response:**
```json
{
  "jobId": "job_abc123",
  "status": "processing",
  "estimatedTime": 120
}
```

### GET /api/jobs/{jobId}

작업 상태 확인

**Response:**
```json
{
  "jobId": "job_abc123",
  "status": "completed",
  "outputUrl": "https://minio.jclee.me/youtube-assets/video.mp4",
  "duration": 598,
  "fileSize": 125000000
}
```

## 구현 (FastAPI + FFmpeg)

```python
# /home/jclee/ffmpeg-worker/main.py

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import subprocess
import uuid
import httpx
from pathlib import Path

app = FastAPI()

WORK_DIR = Path("/tmp/ffmpeg-jobs")
WORK_DIR.mkdir(exist_ok=True)

jobs = {}

class Scene(BaseModel):
    imageUrl: str
    sceneIndex: int
    duration: int

class ComposeRequest(BaseModel):
    audioUrl: str
    scenes: list[Scene]
    outputFormat: str = "mp4"
    resolution: str = "1920x1080"
    fps: int = 30
    transitions: str = "crossfade"

async def process_video(job_id: str, request: ComposeRequest):
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # 1. Download audio
    async with httpx.AsyncClient() as client:
        audio_resp = await client.get(request.audioUrl)
        audio_path = job_dir / "audio.mp3"
        audio_path.write_bytes(audio_resp.content)
    
    # 2. Download images
    image_paths = []
    async with httpx.AsyncClient() as client:
        for scene in sorted(request.scenes, key=lambda s: s.sceneIndex):
            img_resp = await client.get(scene.imageUrl)
            img_path = job_dir / f"scene_{scene.sceneIndex}.png"
            img_path.write_bytes(img_resp.content)
            image_paths.append((img_path, scene.duration))
    
    # 3. Create video segments with Ken Burns effect
    segments = []
    for i, (img_path, duration) in enumerate(image_paths):
        segment_path = job_dir / f"segment_{i}.mp4"
        # Ken Burns zoom effect
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={duration*request.fps}:s={request.resolution}",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(segment_path)
        ]
        subprocess.run(cmd, check=True)
        segments.append(segment_path)
    
    # 4. Concatenate segments
    concat_file = job_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    
    video_no_audio = job_dir / "video_no_audio.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(video_no_audio)
    ], check=True)
    
    # 5. Add audio
    output_path = job_dir / f"output.{request.outputFormat}"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_no_audio),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ], check=True)
    
    # 6. Upload to MinIO
    # TODO: Implement MinIO upload
    
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["outputUrl"] = f"https://minio.jclee.me/youtube-assets/{job_id}/output.mp4"

@app.post("/api/compose")
async def compose_video(request: ComposeRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs[job_id] = {"status": "processing", "estimatedTime": len(request.scenes) * 20}
    
    background_tasks.add_task(process_video, job_id, request)
    
    return {"jobId": job_id, **jobs[job_id]}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}, 404
    return {"jobId": job_id, **jobs[job_id]}
```

## 배포 방법

### VM 200 (oc)에 배포

```bash
# SSH into VM 200
ssh oc.jclee.me

# Install dependencies
pip install fastapi uvicorn httpx python-multipart

# Ensure FFmpeg is installed
ffmpeg -version

# Run the worker
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Systemd Service

```ini
# /etc/systemd/system/ffmpeg-worker.service
[Unit]
Description=FFmpeg Worker API
After=network.target

[Service]
User=jclee
WorkingDirectory=/home/jclee/ffmpeg-worker
ExecStart=/usr/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

## n8n 연동

n8n에서 HTTP Request 노드로 호출:

1. **POST** `http://192.168.50.200:8080/api/compose` - 영상 합성 시작
2. **Wait** 노드로 폴링 또는 Webhook으로 완료 알림
3. **GET** `/api/jobs/{jobId}` - 상태 확인 후 outputUrl 획득
