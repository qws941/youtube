# FFmpeg Worker Deployment

CT 201 (ffmpeg-worker) 배포 가이드

## Container Info

| Item | Value |
|------|-------|
| CTID | 201 |
| Hostname | ffmpeg-worker |
| Node | pve3 |
| Cores | 4 |
| Memory | 8GB |
| Disk | 50GB |
| OS | Debian 12 |

## Manual Deployment

### Step 1: Access Container (via Proxmox console)

```bash
pct enter 201
```

### Step 2: Install Dependencies

```bash
apt-get update
apt-get install -y ffmpeg python3-venv python3-pip curl
```

### Step 3: Create Application Directory

```bash
mkdir -p /opt/ffmpeg-worker
cd /opt/ffmpeg-worker
```

### Step 4: Create Files

Copy the contents from this directory:
- `main.py` - FastAPI application
- `requirements.txt` - Python dependencies
- `ffmpeg-worker.service` - Systemd service

### Step 5: Setup Python Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Step 6: Install Systemd Service

```bash
cp ffmpeg-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ffmpeg-worker
systemctl start ffmpeg-worker
```

### Step 7: Verify

```bash
systemctl status ffmpeg-worker
curl http://localhost:8080/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MINIO_ENDPOINT | http://192.168.50.109:9000 | MinIO server URL |
| MINIO_ACCESS_KEY | minioadmin | MinIO access key |
| MINIO_SECRET_KEY | minioadmin | MinIO secret key |
| MINIO_BUCKET | youtube-assets | Bucket for video storage |
| MINIO_PUBLIC_URL | https://minio.jclee.me | Public URL for video access |
| WORK_DIR | /tmp/ffmpeg-jobs | Temporary work directory |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /api/compose | Start video composition |
| GET | /api/jobs/{jobId} | Get job status |
| GET | /api/jobs | List all jobs |
| DELETE | /api/jobs/{jobId} | Delete job |

## Example Request

```bash
curl -X POST http://192.168.50.201:8080/api/compose \
  -H "Content-Type: application/json" \
  -d '{
    "audioUrl": "https://example.com/audio.mp3",
    "scenes": [
      {"imageUrl": "https://example.com/img1.png", "sceneIndex": 0, "duration": 10},
      {"imageUrl": "https://example.com/img2.png", "sceneIndex": 1, "duration": 10}
    ],
    "resolution": "1920x1080",
    "fps": 30
  }'
```

## Networking

Internal IP: `192.168.50.201` (DHCP assigned, verify in Proxmox)

To expose via Cloudflare Tunnel:
1. Add to Traefik (CT 102)
2. Configure route: `ffmpeg.jclee.me` -> `http://192.168.50.201:8080`
