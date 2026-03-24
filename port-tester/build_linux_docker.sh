#!/bin/bash
# 在 Mac 上用 Docker 打包 Linux 可执行文件
set -e
cd "$(dirname "$0")"

echo "====== PortTester Linux Build (via Docker) ======"

if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker not found. Install from https://www.docker.com/products/docker-desktop"
    exit 1
fi

docker run --rm \
    -v "$(pwd)":/app \
    -w /app \
    python:3.11-slim \
    bash -c "
        apt-get update -qq && apt-get install -y -qq binutils &&
        pip install pyinstaller --quiet &&
        pyinstaller --onefile --name PortTester --clean main.py
    "

echo ""
echo "Build OK: dist/PortTester  (Linux x86_64)"
