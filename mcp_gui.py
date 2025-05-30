#!/usr/bin/env python3
import os
import sys
import threading
import subprocess
import argparse
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv
from mcp_pipe import connect_with_retry
import logging

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__)) # Changed from os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

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
            # Determine paths correctly whether running from source or bundled
            if getattr(sys, 'frozen', False): # Running in a bundle
                base_path = sys._MEIPASS
                python_executable = sys.executable # The bundled exe itself can run python scripts
            else: # Running in normal Python environment
                base_path = os.path.dirname(os.path.abspath(__file__))
                python_executable = sys.executable

            mcp_pipe_script_name = 'mcp_pipe.py' # Just the script name
            # PyInstaller will bundle mcp_pipe.py alongside the main script or in _MEIPASS.
            # So we expect it to be found directly.
            # If PyInstaller is structured to put it in a subfolder, adjust accordingly.
            # For now, assume it's at the same level as mcp_gui.py in the bundle.
            mcp_pipe_path = resource_path(mcp_pipe_script_name)


            # Ensure the script itself is passed as an argument to the python_executable
            # if mcp_pipe.py is bundled as a pyz or similar.
            # However, PyInstaller typically makes .py files available directly.
            # The most robust way if mcp_pipe.py is also a script to be run is often
            # to ensure it's added by PyInstaller and then call it.

            #cmd_list = [python_executable, mcp_pipe_path, '--run-pipe-only']
            cmd_list = [python_executable, mcp_pipe_path]
            if getattr(sys, 'frozen', False) and not os.path.exists(mcp_pipe_path):
                # Fallback for some PyInstaller structures if mcp_pipe.py is not directly accessible
                # This might happen if it's bundled into the main exe's PYZ archive.
                # A more complex solution involves PyInstaller hooks or making mcp_pipe.py an entry point.
                # For now, we assume PyInstaller makes it available.
                # A simple approach is to ensure mcp_pipe.py is added as a 'script' or 'binary'
                # in the .spec file if not found.
                logging.error(f"mcp_pipe.py not found at {mcp_pipe_path} in bundled app.")
                # If mcp_pipe.py is bundled directly into the executable (e.g. if it were the primary script),
                # sys.argv[0] would be the executable.
                # For a secondary script, it's simpler if PyInstaller bundles it as a discoverable file.

            # If .env file is needed by mcp_pipe.py, ensure it can find it
            # Assuming .env.xiaozhi1 is next to the exe or in _MEIPASS
            env_file_path_for_pipe = resource_path('.env.xiaozhi1')
            # You might need to pass this to mcp_pipe.py if it doesn't find it by default
            # e.g., cmd_list.extend(['--env-file', env_file_path_for_pipe])
            # and mcp_pipe.py needs to parse this argument.
            # For simplicity, let's assume load_dotenv in mcp_pipe.py can find it if it's bundled.

            logging.info(f"Executing command: {' '.join(cmd_list)}")
            process = subprocess.Popen(
                cmd_list, # Use the determined python_executable and path
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Capture stderr to stdout pipe
                text=True,
                # bufsize=1, # Not needed with text=True and iterating lines
                # universal_newlines=True # Deprecated, text=True is preferred
                # cwd=base_path # Set current working directory if scripts expect relative paths
            )

            # Log stdout
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    logging.info(line.rstrip())
                process.stdout.close()

            # Wait for the process to complete and get the exit code
            process.wait()
            if process.returncode != 0:
                logging.error(f"Subprocess mcp_pipe.py exited with code {process.returncode}")

        except Exception as e:
            logging.error(f"运行出错: {e}", exc_info=True) # Add exc_info for full traceback

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
