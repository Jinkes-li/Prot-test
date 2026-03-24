#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台端口测试工具
区分三种状态：开放 / 未监听但防火墙放行 / 超时无法判断
支持 GUI 模式（有桌面环境）和 CLI 模式（无桌面/命令行参数）
"""

import socket
import select
import threading
import datetime
import sys
import os
import platform
import argparse

# ── 状态常量（GUI/CLI 共用）──────────────────────────────────

S_OPEN    = "开放"
S_RST     = "未监听_防火墙放行"
S_TIMEOUT = "超时_无法判断"
S_ERROR   = "连接异常"

# ── 核心测试逻辑 ──────────────────────────────────────────────

def test_port(ip: str, port: int, timeout: float = 2.0) -> dict:
    """
    非阻塞 socket + select，正确处理 WSAEWOULDBLOCK(10035) / EINPROGRESS(115)。
    返回 dict: ip, port, status, detail, time
    """
    result = {
        "ip": ip,
        "port": port,
        "status": S_TIMEOUT,
        "detail": "",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # ECONNREFUSED: Linux=111, Windows=10061
    ECONNREFUSED = (111, 10061)
    # connect_ex 立即返回"进行中"的正常码
    IN_PROGRESS = (0, 10035, 115)

    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False)

        ret = s.connect_ex((ip, port))

        if ret not in IN_PROGRESS:
            # 立即得到结果（本机/局域网常见）
            if ret in ECONNREFUSED:
                result["status"] = S_RST
                result["detail"] = "端口无进程监听，防火墙放行（RST，适用于本机/局域网）"
            else:
                result["status"] = S_TIMEOUT
                result["detail"] = f"连接立即失败，错误码: {ret}"
            return result

        # 等待连接结果：同时监听可读（RST/数据）和可写（连接成功）
        readable, writable, _ = select.select([s], [s], [], timeout)

        if not readable and not writable:
            # select 超时，无任何响应
            result["status"] = S_TIMEOUT
            result["detail"] = "无响应：防火墙/安全组拦截，或端口未监听（云环境无法区分）"
            return result

        # 用 SO_ERROR 获取真实连接结果
        err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)

        if err == 0:
            result["status"] = S_OPEN
            result["detail"] = "端口已监听，连接成功"
        elif err in ECONNREFUSED:
            result["status"] = S_RST
            result["detail"] = "端口无进程监听，防火墙放行（RST，适用于本机/局域网）"
        else:
            result["status"] = S_TIMEOUT
            result["detail"] = f"连接失败，SO_ERROR={err}"

    except OSError as e:
        result["status"] = S_ERROR
        result["detail"] = f"socket 异常: {e}"
    finally:
        if s:
            try:
                s.close()
            except OSError:
                pass

    return result


# ── CLI 模式 ─────────────────────────────────────────────────

# Windows cmd 不支持 ANSI，需要判断
_USE_COLOR = sys.stdout.isatty() and platform.system() != "Windows"

CLI_COLORS = {
    S_OPEN:    "\033[32m",
    S_RST:     "\033[33m",
    S_TIMEOUT: "\033[31m",
    S_ERROR:   "\033[35m",
}
RESET = "\033[0m"

def _colored(text: str, status: str) -> str:
    if not _USE_COLOR:
        return text
    return f"{CLI_COLORS.get(status, '')}{text}{RESET}"

def cli_run(ip: str, ports: list, timeout: float, log_file: str = None):
    results = []
    print(f"\n===== 端口测试 (目标: {ip}) =====\n")
    for port in ports:
        r = test_port(ip, port, timeout)
        # 固定宽度用空格手动补齐，避免中文字符宽度导致列错位
        status_padded = r["status"].ljust(12)
        line = f"[{r['time']}]  {ip}:{port}  {_colored(status_padded, r['status'])}  {r['detail']}"
        print(line)
        results.append(r)

    if log_file:
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("============ 端口测试日志 ============\n")
                f.write(f"测试时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"目标IP: {ip}\n")
                f.write(f"操作系统: {platform.system()} {platform.release()}\n")
                f.write("======================================\n\n")
                for r in results:
                    f.write(
                        f"时间: {r['time']} | IP: {r['ip']} | 端口: {r['port']} "
                        f"| 状态: {r['status']} | 详情: {r['detail']}\n"
                    )
            print(f"\n日志已保存: {log_file}")
        except OSError as e:
            print(f"\n日志保存失败: {e}")

    print(f"\n完成，共测试 {len(results)} 个端口\n")


# ── 显示环境检测 ──────────────────────────────────────────────

def has_display() -> bool:
    if platform.system() == "Windows":
        return True
    if platform.system() == "Darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


# ── GUI 模式 ──────────────────────────────────────────────────

STATUS_COLORS = {
    S_OPEN:    "#27ae60",
    S_RST:     "#f39c12",
    S_TIMEOUT: "#e74c3c",
    S_ERROR:   "#9b59b6",
    "测试中...": "#3498db",
}

# App 类在模块级定义，但只在 GUI 模式下实例化
# tkinter 在入口处按需 import 后注入全局命名空间
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("端口测试工具 v1.0")
        self.root.resizable(True, True)
        self.root.minsize(700, 520)
        self._results = []
        self._build_ui()

    def _build_ui(self):
        import tkinter as tk
        from tkinter import ttk
        pad = {"padx": 8, "pady": 4}

        frm_input = ttk.LabelFrame(self.root, text="测试配置")
        frm_input.pack(fill="x", **pad)

        ttk.Label(frm_input, text="目标 IP:").grid(row=0, column=0, sticky="w", **pad)
        self.var_ip = tk.StringVar(value="127.0.0.1")
        ttk.Entry(frm_input, textvariable=self.var_ip, width=20).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(frm_input, text="端口列表 (逗号分隔):").grid(row=0, column=2, sticky="w", **pad)
        self.var_ports = tk.StringVar(value="80, 443, 3389, 8080")
        ttk.Entry(frm_input, textvariable=self.var_ports, width=30).grid(row=0, column=3, sticky="w", **pad)

        ttk.Label(frm_input, text="超时(秒):").grid(row=0, column=4, sticky="w", **pad)
        self.var_timeout = tk.StringVar(value="2")
        ttk.Entry(frm_input, textvariable=self.var_timeout, width=6).grid(row=0, column=5, sticky="w", **pad)

        frm_btn = ttk.Frame(self.root)
        frm_btn.pack(fill="x", **pad)

        self.btn_start = ttk.Button(frm_btn, text="▶  开始测试", command=self._start)
        self.btn_start.pack(side="left", padx=4)
        ttk.Button(frm_btn, text="💾  导出日志", command=self._export).pack(side="left", padx=4)
        ttk.Button(frm_btn, text="🗑  清空结果", command=self._clear).pack(side="left", padx=4)

        self.lbl_status = ttk.Label(frm_btn, text="就绪", foreground="gray")
        self.lbl_status.pack(side="right", padx=8)

        cols = ("时间", "IP", "端口", "状态", "详情")
        frm_tree = ttk.Frame(self.root)
        frm_tree.pack(fill="both", expand=True, **pad)

        self.tree = ttk.Treeview(frm_tree, columns=cols, show="headings", height=12)
        widths = (150, 120, 60, 180, 320)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center" if col != "详情" else "w")

        vsb = ttk.Scrollbar(frm_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for status, color in STATUS_COLORS.items():
            if status != "测试中...":
                self.tree.tag_configure(status, foreground=color)

        frm_legend = ttk.Frame(self.root)
        frm_legend.pack(fill="x", padx=8, pady=2)
        for status, color in STATUS_COLORS.items():
            if status == "测试中...":
                continue
            tk.Label(frm_legend, text=f"● {status}", foreground=color, font=("", 9)).pack(side="left", padx=6)

    def _start(self):
        from tkinter import messagebox
        ip = self.var_ip.get().strip()
        ports_raw = self.var_ports.get().strip()
        try:
            timeout = float(self.var_timeout.get())
        except ValueError:
            messagebox.showerror("错误", "超时时间必须是数字")
            return
        if not ip:
            messagebox.showerror("错误", "请输入目标 IP")
            return
        try:
            ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
        except ValueError:
            messagebox.showerror("错误", "端口格式错误，请用逗号分隔整数")
            return
        if not ports:
            messagebox.showerror("错误", "请至少输入一个端口")
            return

        self.btn_start.config(state="disabled")
        self.lbl_status.config(text="测试中...", foreground=STATUS_COLORS["测试中..."])
        threading.Thread(target=self._run_tests, args=(ip, ports, timeout), daemon=True).start()

    def _run_tests(self, ip, ports, timeout):
        self._results = []
        for port in ports:
            r = test_port(ip, port, timeout)
            self._results.append(r)
            self.root.after(0, self._append_row, r)
        self.root.after(0, self._done)

    def _append_row(self, r):
        tag = r["status"] if r["status"] in STATUS_COLORS else ""
        self.tree.insert("", "end",
                         values=(r["time"], r["ip"], r["port"], r["status"], r["detail"]),
                         tags=(tag,))
        self.tree.yview_moveto(1)

    def _done(self):
        self.btn_start.config(state="normal")
        self.lbl_status.config(text=f"完成，共测试 {len(self._results)} 个端口", foreground="gray")

    def _clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._results = []
        self.lbl_status.config(text="就绪", foreground="gray")

    def _export(self):
        from tkinter import filedialog, messagebox
        if not self._results:
            messagebox.showinfo("提示", "没有可导出的结果")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            initialfile=f"PortTest_{ts}.log",
            filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("============ 端口测试日志 ============\n")
                f.write(f"测试时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"操作系统: {platform.system()} {platform.release()}\n")
                f.write("======================================\n\n")
                for r in self._results:
                    f.write(
                        f"时间: {r['time']} | IP: {r['ip']} | 端口: {r['port']} "
                        f"| 状态: {r['status']} | 详情: {r['detail']}\n"
                    )
            messagebox.showinfo("导出成功", f"日志已保存到:\n{path}")
        except OSError as e:
            messagebox.showerror("导出失败", str(e))


# ── 入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="端口测试工具 - 区分开放/未监听/超时无法判断",
    )
    parser.add_argument("--ip",      help="目标 IP 地址")
    parser.add_argument("--ports",   help="端口列表，逗号分隔，如 80,443,8080")
    parser.add_argument("--timeout", type=float, default=2.0, help="超时秒数（默认 2）")
    parser.add_argument("--log",     help="日志输出路径（可选，不指定则自动生成）")
    parser.add_argument("--cli",     action="store_true", help="强制使用命令行模式")
    args = parser.parse_args()

    use_cli = args.cli or bool(args.ip) or not has_display()

    if use_cli:
        ip = args.ip or input("目标 IP: ").strip()
        if not ip:
            print("错误：IP 不能为空")
            sys.exit(1)
        ports_raw = args.ports or input("端口列表 (逗号分隔): ").strip()
        try:
            ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
            assert ports
        except (ValueError, AssertionError):
            print("错误：端口格式不正确")
            sys.exit(1)
        log = args.log or f"PortTest_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        cli_run(ip, ports, args.timeout, log)
    else:
        import tkinter as tk
        root = tk.Tk()
        App(root)
        root.mainloop()
