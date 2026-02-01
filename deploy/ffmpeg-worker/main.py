"""FFmpeg Worker API - Video Composition Service for YouTube Automation."""

import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import boto3
import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

# ============================================================================
# Configuration
# ============================================================================

WORK_DIR = Path(os.getenv("WORK_DIR", "/tmp/ffmpeg-jobs"))
WORK_DIR.mkdir(exist_ok=True)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://192.168.50.109:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "youtube-assets")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "https://minio.jclee.me")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# MinIO Client
# ============================================================================

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)


def ensure_bucket():
    """Create bucket if not exists."""
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        s3_client.create_bucket(Bucket=MINIO_BUCKET)
        logger.info(f"Created bucket: {MINIO_BUCKET}")


# ============================================================================
# Models
# ============================================================================


class Scene(BaseModel):
    imageUrl: str
    sceneIndex: int
    duration: int  # seconds


class ComposeRequest(BaseModel):
    audioUrl: str
    scenes: list[Scene]
    outputFormat: str = "mp4"
    resolution: str = "1920x1080"
    fps: int = 30
    transitions: str = "crossfade"
    videoId: Optional[str] = None  # Optional ID for tracking


class JobStatus(BaseModel):
    jobId: str
    status: str  # pending, processing, completed, failed
    progress: int = 0
    outputUrl: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[int] = None
    fileSize: Optional[int] = None


# ============================================================================
# Job Storage (In-memory - replace with Redis for production)
# ============================================================================

jobs: dict[str, JobStatus] = {}

# ============================================================================
# FFmpeg Processing
# ============================================================================


async def download_file(url: str, dest: Path) -> None:
    """Download file from URL."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        logger.info(f"Downloaded: {url} -> {dest}")


def create_ken_burns_segment(
    image_path: Path,
    output_path: Path,
    duration: int,
    fps: int,
    resolution: str,
) -> None:
    """Create video segment with Ken Burns zoom effect."""
    width, height = resolution.split("x")
    zoom_increment = 0.0015
    total_frames = duration * fps
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", (
            f"scale=8000:-1,"
            f"zoompan=z='min(zoom+{zoom_increment},1.5)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={resolution}:fps={fps}"
        ),
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    
    logger.info(f"Creating segment: {image_path} -> {output_path}")
    subprocess.run(cmd, check=True, capture_output=True)


def concatenate_segments(segment_paths: list[Path], output_path: Path) -> None:
    """Concatenate video segments."""
    concat_file = output_path.parent / "concat.txt"
    
    with open(concat_file, "w") as f:
        for seg in segment_paths:
            f.write(f"file '{seg}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def add_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Add audio track to video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def get_video_info(path: Path) -> tuple[int, int]:
    """Get video duration and file size."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = int(float(result.stdout.strip())) if result.stdout.strip() else 0
    file_size = path.stat().st_size
    
    return duration, file_size


def upload_to_minio(local_path: Path, object_key: str) -> str:
    """Upload file to MinIO and return public URL."""
    s3_client.upload_file(
        str(local_path),
        MINIO_BUCKET,
        object_key,
        ExtraArgs={"ContentType": "video/mp4"}
    )
    
    return f"{MINIO_PUBLIC_URL}/{MINIO_BUCKET}/{object_key}"


# ============================================================================
# Background Processing
# ============================================================================


async def process_video(job_id: str, request: ComposeRequest) -> None:
    """Process video composition in background."""
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    try:
        jobs[job_id].status = "processing"
        jobs[job_id].progress = 5
        
        logger.info(f"[{job_id}] Downloading audio...")
        audio_path = job_dir / "audio.mp3"
        await download_file(request.audioUrl, audio_path)
        jobs[job_id].progress = 15
        
        sorted_scenes = sorted(request.scenes, key=lambda s: s.sceneIndex)
        total_scenes = len(sorted_scenes)
        segment_paths = []
        
        for i, scene in enumerate(sorted_scenes):
            logger.info(f"[{job_id}] Processing scene {i+1}/{total_scenes}")
            
            img_path = job_dir / f"scene_{scene.sceneIndex}.png"
            await download_file(scene.imageUrl, img_path)
            
            segment_path = job_dir / f"segment_{scene.sceneIndex}.mp4"
            await asyncio.to_thread(
                create_ken_burns_segment,
                img_path,
                segment_path,
                scene.duration,
                request.fps,
                request.resolution
            )
            segment_paths.append(segment_path)
            jobs[job_id].progress = 15 + int((i + 1) / total_scenes * 60)
        
        logger.info(f"[{job_id}] Concatenating segments...")
        video_no_audio = job_dir / "video_no_audio.mp4"
        await asyncio.to_thread(concatenate_segments, segment_paths, video_no_audio)
        jobs[job_id].progress = 80
        
        logger.info(f"[{job_id}] Adding audio...")
        output_path = job_dir / f"output.{request.outputFormat}"
        await asyncio.to_thread(add_audio, video_no_audio, audio_path, output_path)
        jobs[job_id].progress = 90
        
        duration, file_size = get_video_info(output_path)
        
        logger.info(f"[{job_id}] Uploading to MinIO...")
        object_key = f"videos/{job_id}/output.mp4"
        output_url = await asyncio.to_thread(upload_to_minio, output_path, object_key)
        
        jobs[job_id].status = "completed"
        jobs[job_id].progress = 100
        jobs[job_id].outputUrl = output_url
        jobs[job_id].duration = duration
        jobs[job_id].fileSize = file_size
        
        logger.info(f"[{job_id}] Completed! Output: {output_url}")
        
    except Exception as e:
        logger.error(f"[{job_id}] Failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)
        
    finally:
        pass


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="FFmpeg Worker API",
    description="Video composition service for YouTube Automation",
    version="1.0.0"
)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    ensure_bucket()
    logger.info("FFmpeg Worker API started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ffmpeg-worker"}


@app.post("/api/compose", response_model=JobStatus)
async def compose_video(request: ComposeRequest, background_tasks: BackgroundTasks):
    """Start video composition job."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    if request.videoId:
        job_id = f"job_{request.videoId}"
    
    estimated_time_seconds = len(request.scenes) * 20 + 30
    
    jobs[job_id] = JobStatus(
        jobId=job_id,
        status="pending",
        progress=0
    )
    
    background_tasks.add_task(process_video, job_id, request)
    
    logger.info(f"Created job: {job_id} with {len(request.scenes)} scenes")
    
    return jobs[job_id]


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return list(jobs.values())


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job and cleanup."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dir = WORK_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    
    del jobs[job_id]
    
    return {"deleted": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
