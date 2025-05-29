#!/usr/bin/env python3
import os
import sys
import threading
import asyncio
import subprocess
import argparse
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv
from mcp_pipe import connect_with_retry
import logging

# 解析命令行参数：--run-pipe-only 只运行管道，不启动 GUI
parser = argparse.ArgumentParser()
parser.add_argument(
    '--run-pipe-only',
    action='store_true',
    help='仅以管道子进程模式启动，不显示 GUI'
)
args = parser.parse_args()

if args.run_pipe_only:
    # 直接运行管道逻辑后退出
    try:
        connect_with_retry()
    except Exception as e:
        print(f"运行管道时出错: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

# 以下是 GUI 部分
# 全局保存子进程引用
process = None

# 加载环境变量
load_dotenv()
endpoint = os.getenv('MCP_ENDPOINT')
if not endpoint:
    messagebox.showerror('错误', '请在 .env 中设置 MCP_ENDPOINT')
    sys.exit(1)

# GUI 界面
root = tk.Tk()
root.title('MCP Pipe GUI')

# 日志区
text_log = scrolledtext.ScrolledText(root, width=80, height=20)
text_log.pack(padx=10, pady=(10, 0))

# TextHandler: Logging → GUI
class TextHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        text_log.insert(tk.END, msg + '\n')
        text_log.see(tk.END)

# 配置根日志
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = TextHandler()
handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
root_logger.addHandler(handler)
logging.getLogger('FileManager').setLevel(logging.INFO)

# 按钮区
top_frame = tk.Frame(root)
top_frame.pack(pady=(5, 10))
btn_run = tk.Button(top_frame, text='启动', width=12)
btn_run.pack(side=tk.LEFT, padx=5)
btn_stop = tk.Button(top_frame, text='停止', width=12, state=tk.DISABLED)
btn_stop.pack(side=tk.LEFT, padx=5)

# 启动逻辑
def run_pipe():
    global process

    def target():
        try:
            # 判断是否为打包后的可执行文件
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(__file__)

            mcp_pipe_path = os.path.join(base_path, 'mcp_pipe.py')

            # 调用自身 exe + 参数 --run-pipe-only
            process = subprocess.Popen(
                [sys.executable, mcp_pipe_path, '--run-pipe-only'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # 将子进程输出显示到 GUI 日志
            for line in process.stdout:
                logging.info(line.rstrip())
            process.wait()
        except Exception as e:
            logging.error(f"运行出错: {e}")

    threading.Thread(target=target, daemon=True).start()
    btn_run.config(state=tk.DISABLED)
    btn_stop.config(state=tk.NORMAL)

# 停止逻辑
def stop_pipe():
    logging.info("用户点击停止，终止子进程并退出")
    global process
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    root.quit()
    sys.exit(0)

btn_run.config(command=run_pipe)
btn_stop.config(command=stop_pipe)

# 启动 GUI 主循环
root.mainloop()
