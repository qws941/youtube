#!/bin/bash
set -e

TARGET_HOST="192.168.50.201"
TARGET_DIR="/opt/ffmpeg-worker"

echo "=== Deploying FFmpeg Worker to CT 201 ==="

echo "[1/5] Installing system packages..."
ssh root@$TARGET_HOST "apt-get update && apt-get install -y ffmpeg python3-venv python3-pip"

echo "[2/5] Creating application directory..."
ssh root@$TARGET_HOST "mkdir -p $TARGET_DIR"

echo "[3/5] Copying files..."
scp main.py requirements.txt ffmpeg-worker.service root@$TARGET_HOST:$TARGET_DIR/

echo "[4/5] Setting up Python environment..."
ssh root@$TARGET_HOST "cd $TARGET_DIR && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"

echo "[5/5] Installing and starting systemd service..."
ssh root@$TARGET_HOST "cp $TARGET_DIR/ffmpeg-worker.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable ffmpeg-worker && systemctl restart ffmpeg-worker"

echo "=== Deployment complete ==="
echo "Service URL: http://$TARGET_HOST:8080"
echo "Health check: curl http://$TARGET_HOST:8080/health"
