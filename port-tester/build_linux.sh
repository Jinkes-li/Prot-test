#!/bin/bash
set -e
echo "====== 端口测试工具 Linux 打包 ======"

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "错误：未找到 python3，请先安装"
    exit 1
fi

# 安装 PyInstaller
echo "安装 PyInstaller..."
pip3 install pyinstaller --quiet

# 打包为单文件可执行
echo "开始打包..."
pyinstaller \
    --onefile \
    --windowed \
    --name "PortTester" \
    main.py

echo ""
echo "打包完成！输出文件: dist/PortTester"
echo ""

# 可选：制作 .deb 包（需要 dpkg-deb）
read -p "是否同时生成 .deb 安装包？(y/N): " make_deb
if [[ "$make_deb" =~ ^[Yy]$ ]]; then
    VERSION="1.0.0"
    PKG_DIR="deb_build/porttester_${VERSION}"

    mkdir -p "${PKG_DIR}/DEBIAN"
    mkdir -p "${PKG_DIR}/usr/local/bin"
    mkdir -p "${PKG_DIR}/usr/share/applications"

    cp dist/PortTester "${PKG_DIR}/usr/local/bin/porttester"
    chmod +x "${PKG_DIR}/usr/local/bin/porttester"

    cat > "${PKG_DIR}/DEBIAN/control" <<EOF
Package: porttester
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Your Name <you@example.com>
Description: 跨平台端口测试工具
 区分端口开放、未监听但防火墙放行、防火墙阻拦三种状态。
EOF

    cat > "${PKG_DIR}/usr/share/applications/porttester.desktop" <<EOF
[Desktop Entry]
Name=端口测试工具
Exec=/usr/local/bin/porttester
Type=Application
Categories=Network;Utility;
EOF

    dpkg-deb --build "${PKG_DIR}" "dist/porttester_${VERSION}_amd64.deb"
    echo "deb 包已生成: dist/porttester_${VERSION}_amd64.deb"
fi
