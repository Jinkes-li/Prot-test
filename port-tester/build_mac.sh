#!/bin/bash
# 打包 macOS 可执行文件（需在 Mac 上运行）
set -e
cd "$(dirname "$0")"

echo "====== PortTester macOS Build ======"

pip3 install pyinstaller --quiet

pyinstaller --onefile --windowed --name "PortTester" --clean main.py

echo ""
echo "Build OK: dist/PortTester.app  (macOS)"
