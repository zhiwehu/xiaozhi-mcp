import os, sys, threading, subprocess
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
endpoint = os.getenv('MCP_ENDPOINT')
if not endpoint:
    raise RuntimeError('请在 .env 文件中设置 MCP_ENDPOINT')

SCRIPT = 'aggregate.py'

# 启动子进程并读取输出
def run_pipe():
    env = os.environ.copy()
    env['MCP_ENDPOINT'] = endpoint
    cmd = [sys.executable, 'mcp_pipe.py', SCRIPT]
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
        )
    except Exception as e:
        messagebox.showerror('启动失败', str(e))
        return

    def reader():
        for line in proc.stdout:
            text_log.insert(tk.END, line)
            text_log.see(tk.END)
        proc.wait()
        text_log.insert(tk.END, f"\n进程退出，返回码：{proc.returncode}\n")

    threading.Thread(target=reader, daemon=True).start()
    btn_run.config(state=tk.DISABLED)
    btn_stop.config(state=tk.NORMAL)

# 停止子进程
def stop_pipe():
    # 简易方式：直接退出应用
    root.destroy()

# 构建 GUI
root = tk.Tk()
root.title('MCP Pipe GUI')

btn_run = tk.Button(root, text='启动', width=10, command=run_pipe)
btn_run.pack(pady=(10,0))

btn_stop = tk.Button(root, text='停止', width=10, command=stop_pipe, state=tk.DISABLED)
btn_stop.pack(pady=(5,10))

text_log = scrolledtext.ScrolledText(root, width=80, height=20)
text_log.pack(padx=10, pady=5)

root.mainloop()