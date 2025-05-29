#!/usr/bin/env python3
import os
import sys
import threading
import asyncio
import subprocess
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv
from mcp_pipe import connect_with_retry
import logging

# 在文件顶部检查命令行参数
if '--run-pipe-only' in sys.argv:
    # 如果检测到特定参数，导入并运行 mcp_pipe 的核心逻辑
    try:
        # PyInstaller 打包后，直接导入可能需要确保 sys.path 包含临时目录
        # 或者如果 mcp_pipe.py 自身是可执行的，并且逻辑在文件执行时运行，则无需在这里导入
        # 最简单的方式是确保 mcp_pipe.py 自身的代码结构适合作为独立进程运行
        # 假设 mcp_pipe.py 执行时会运行其主要逻辑
        # 在这里，我们只是让这个子进程继续执行 mcp_pipe.py 的代码
        # 而主进程（不带 --run-pipe-only 参数的那个）则不进入这里的逻辑
        logging.info("Running as pipe process. Executing mcp_pipe.py logic...")
        # 如果 mcp_pipe.py 需要 MCP_ENDPOINT，确保子进程也能访问到环境变量
        # 这里不需要再调用 mcp_pipe 的函数，因为子进程就是运行的 mcp_pipe_path
        # 这个 if 块的目的是让带有 --run-pipe-only 参数的进程在执行完 mcp_pipe_path 的代码后退出
        # 避免它继续执行 mcp_gui.py 的 GUI 代码
        pass # 子进程会执行 mcp_pipe.py 的代码，执行完毕后会自动退出
    except Exception as e:
        logging.error(f"Error in pipe process logic: {e}")
    sys.exit(0) # 子进程执行完毕或出错后退出，避免启动 GUI

# 如果没有 --run-pipe-only 参数，则继续作为 GUI 主进程运行

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
text_log.pack(padx=10, pady=(10,0))

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
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)
logging.getLogger('FileManager').setLevel(logging.INFO)

# 按钮区
top_frame = tk.Frame(root)
top_frame.pack(pady=(5,10))
btn_run = tk.Button(top_frame, text='启动', width=12)
btn_run.pack(side=tk.LEFT, padx=5)
btn_stop = tk.Button(top_frame, text='停止', width=12, state=tk.DISABLED)
btn_stop.pack(side=tk.LEFT, padx=5)

# 启动逻辑
def run_pipe():
    global process
    def target():
        try:
            # 内部调用 mcp_pipe.connect_with_retry
            # 并直接创建子进程：

            # 获取 PyInstaller 临时目录路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件
                base_path = sys._MEIPASS
            else:
                # 如果是直接运行 Python 脚本
                base_path = os.path.dirname(__file__)

            mcp_pipe_path = os.path.join(base_path, 'mcp_pipe.py')

            process = subprocess.Popen(
                [sys.executable, mcp_pipe_path, '--run-pipe-only'], # 修改这里，传递参数给子进程
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            # 管道甚至可以在这里并入 GUI 日志:
            for line in process.stdout:
                logging.info(line.strip())
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
    # 退出主 GUI 进程
    root.quit()
    sys.exit(0)

btn_run.config(command=run_pipe)
btn_stop.config(command=stop_pipe)

# 只有当没有 --run-pipe-only 参数时才启动 GUI
# if '--run-pipe-only' not in sys.argv: # 这个检查已经在文件顶部做了
root.mainloop() # <-- 保持在这里，但上面的 if 块会阻止带参数的进程到达这里
