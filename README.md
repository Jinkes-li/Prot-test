# 端口测试工具 PortTester

跨平台 TCP 端口连通性测试工具，精确区分三种端口状态，支持 GUI 和命令行两种模式。

---

## 状态说明

| 状态 | 含义 | 网络行为 |
|------|------|---------|
| 🟢 开放 | 端口有服务监听且连接成功 | SYN → SYN+ACK |
| 🟡 未监听_防火墙放行 | 防火墙放行但无服务监听 | SYN → RST（适用于本机/局域网） |
| 🔴 超时_无法判断 | 无响应，防火墙拦截或端口未监听 | SYN → 无回包 |

> **注意：** 云服务器（阿里云/腾讯云/AWS）安全组工作在网络层，RST 包会被丢弃。因此在云环境中，"防火墙拦截"和"端口未监听"均表现为超时，客户端无法区分，这是 TCP 协议的固有限制，非工具缺陷。

---

## 功能特性

- 批量测试多个端口
- 自动识别运行环境，有桌面启动 GUI，无桌面自动切换 CLI
- GUI 模式支持结果导出为日志文件
- CLI 模式支持命令行参数，可集成到脚本/自动化任务
- 非阻塞 socket + select 实现，正确处理各平台错误码
- 跨平台：Windows / macOS / Linux

---

## 环境要求

- Python 3.8+
- 无第三方依赖（仅用标准库）
- 打包为可执行文件后无需安装 Python

---

## 直接运行（需要 Python）

```bash
# GUI 模式（有桌面环境自动启动）
python main.py

# CLI 模式（命令行参数）
python main.py --ip 192.168.1.1 --ports 80,443,8080

# CLI 模式（交互式输入）
python main.py --cli

# 指定超时和日志路径
python main.py --ip 192.168.1.1 --ports 80,443 --timeout 3 --log result.log
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--ip` | 目标 IP 地址 | 交互输入 |
| `--ports` | 端口列表，逗号分隔 | 交互输入 |
| `--timeout` | 连接超时秒数 | `2` |
| `--log` | 日志保存路径 | 自动生成带时间戳的文件名 |
| `--cli` | 强制使用命令行模式 | - |

---

## 打包为可执行文件

### Windows → PortTester.exe

在 Windows 机器上，确保已安装 Python 3.8+ 并勾选 "Add Python to PATH"，然后运行：

```bat
build_win.bat
```

输出：`dist\PortTester.exe`，双击即用，无需安装 Python。

---

### Linux → PortTester

**方式一：在 Linux 机器上直接打包**

```bash
chmod +x build_linux.sh
./build_linux.sh
```

**方式二：在 Mac 上用 Docker 打包 Linux 版**（需安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)）

```bash
chmod +x build_linux_docker.sh
./build_linux_docker.sh
```

输出：`dist/PortTester`

```bash
chmod +x dist/PortTester
./dist/PortTester --cli
```

`build_linux.sh` 还支持可选生成 `.deb` 安装包（需要系统有 `dpkg-deb`）：

```bash
sudo dpkg -i dist/porttester_1.0.0_amd64.deb
# 安装后直接使用
porttester --ip 192.168.1.1 --ports 80,443
```

---

### macOS → PortTester.app

```bash
chmod +x build_mac.sh
./build_mac.sh
```

输出：`dist/PortTester.app`

---

## 项目结构

```
port-tester/
├── main.py                  # 主程序（GUI + CLI）
├── build_win.bat            # Windows 打包脚本
├── build_linux.sh           # Linux 打包脚本（含可选 .deb）
├── build_linux_docker.sh    # 在 Mac 上用 Docker 打包 Linux 版
├── build_mac.sh             # macOS 打包脚本
└── requirements.txt         # 打包依赖（PyInstaller）
```

---

## 技术说明

使用非阻塞 socket + `select` 实现连接检测，相比阻塞式 `connect` 能正确处理 Windows 上的 `WSAEWOULDBLOCK (10035)` 和 Linux 上的 `EINPROGRESS (115)`，通过 `SO_ERROR` 获取最终连接结果，避免误判。
