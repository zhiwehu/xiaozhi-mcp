#!/usr/bin/env python3
import os
import sys
import threading
import subprocess
import argparse
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv
# from mcp_pipe import connect_with_retry # connect_with_retry 在 mcp_pipe.py 中，不由 mcp_gui.py 直接调用
import logging

# 全局保存子进程引用 (在 if __name__ == '__main__': 块之外定义，以便函数可以访问)
process = None
# root Tkinter 对象也需要在全局（或可传递的上下文）中定义，以便 stop_pipe 可以访问
# 但更好的做法是将其作为参数传递或通过类成员访问。为简单起见，暂时保持全局。
root = None
text_log = None  # 日志区也需要类似处理


# 1. 修改后的 resource_path 函数
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (frozen)
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment (not frozen)
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # Fallback if __file__ is not defined
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_path, relative_path)


# TextHandler: Logging → GUI (在 if __name__ == '__main__': 之外定义，以便全局使用)
class TextHandler(logging.Handler):
    def emit(self, record):
        # 确保 text_log 已经初始化
        if text_log:
            msg = self.format(record)
            text_log.insert(tk.END, msg + '\n')
            text_log.see(tk.END)


# 配置根日志记录器 (在 if __name__ == '__main__': 之外定义和配置)
# 这样，即使在脚本早期（例如参数解析前）发生的日志事件也能被捕获（如果处理程序已添加）
# 但 TextHandler 需要 text_log，所以它的添加必须在 text_log 初始化后。
# 基本配置可以先做。
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# logging.getLogger('FileManager').setLevel(logging.INFO) # 这可以在主GUI逻辑中进一步配置

# 启动逻辑 (在 if __name__ == '__main__': 之外定义)
def run_pipe():
    global process, root  # 声明要修改全局变量 process 和 root (如果 stop_pipe 需要 root.quit())

    # 以及 btn_run, btn_stop 如果要修改它们的状态

    def target():
        try:
            # Determine paths correctly whether running from source or bundled
            if getattr(sys, 'frozen', False):  # Running in a bundle
                # base_path = sys._MEIPASS # base_path 在此上下文中未使用
                python_executable = sys.executable  # The bundled exe itself can run python scripts
            else:  # Running in normal Python environment
                # base_path = os.path.dirname(os.path.abspath(__file__)) # base_path 在此上下文中未使用
                python_executable = sys.executable

            mcp_pipe_script_name = 'mcp_pipe.py'
            mcp_pipe_path = resource_path(mcp_pipe_script_name)  # 使用修改后的 resource_path

            cmd_list = [python_executable, mcp_pipe_path]  # 正确的调用方式

            # 移除检查 mcp_pipe_path 是否存在的逻辑，如果 resource_path 配置正确，它应该能找到
            # if getattr(sys, 'frozen', False) and not os.path.exists(mcp_pipe_path):
            #     logging.error(f"mcp_pipe.py not found at {mcp_pipe_path} in bundled app.")
            #     return # 如果找不到，提前返回

            logging.info(f"Executing command: {' '.join(cmd_list)}")
            # 使用全局变量 `process`
            globals()['process'] = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # 显式指定编码
                errors='replace'  # 处理潜在的编码错误
            )

            if globals()['process'].stdout:
                for line in iter(globals()['process'].stdout.readline, ''):
                    logging.info(line.rstrip())  # 日志将通过 TextHandler 显示到 GUI
                globals()['process'].stdout.close()

            globals()['process'].wait()
            if globals()['process'].returncode != 0:
                logging.error(f"Subprocess mcp_pipe.py exited with code {globals()['process'].returncode}")

        except Exception as e:
            logging.error(f"运行子进程出错: {e}", exc_info=True)
        finally:
            # 无论成功与否，重新启用 "启动" 按钮，禁用 "停止" 按钮（如果 root 和按钮已定义）
            if root and btn_run and btn_stop:  # 确保 Tkinter 对象已创建
                btn_run.config(state=tk.NORMAL)
                btn_stop.config(state=tk.DISABLED)

    # 启动子进程的线程
    # 禁用 "启动" 按钮，启用 "停止" 按钮 （如果 root 和按钮已定义）
    if root and btn_run and btn_stop:  # 确保 Tkinter 对象已创建
        btn_run.config(state=tk.DISABLED)
        btn_stop.config(state=tk.NORMAL)
    threading.Thread(target=target, daemon=True).start()


# 停止逻辑 (在 if __name__ == '__main__': 之外定义)
def stop_pipe():
    global process, root  # 声明要修改全局变量 process 和 root
    logging.info("用户点击停止，尝试终止子进程并退出GUI")
    if process and process.poll() is None:  # 检查 process 是否存在且仍在运行
        process.terminate()
        try:
            process.wait(timeout=5)
            logging.info("子进程已终止。")
        except subprocess.TimeoutExpired:
            process.kill()
            logging.warning("子进程强制终止。")
        except Exception as e:
            logging.error(f"终止子进程时发生错误: {e}", exc_info=True)
    else:
        logging.info("子进程未运行或已结束。")

    if root:  # 检查 root 是否已初始化
        root.quit()  # 退出 Tkinter 主循环
        # root.destroy() # 可选，销毁窗口


# ---- 主程序入口 ----
if __name__ == '__main__':
    # 获取程序名称，用于日志和帮助信息
    prog_name = os.path.basename(sys.executable) if getattr(sys, 'frozen', False) else os.path.basename(sys.argv[0])

    # 2. 修改后的 argparse 逻辑
    parser = argparse.ArgumentParser(prog=prog_name)
    parser.add_argument(
        '--run-pipe-only',
        action='store_true',
        help='(遗留功能) 使 GUI 程序以管道模式运行，不显示 GUI。'
    )
    parser.add_argument(
        'script_to_run_for_pyinstaller',  # 这个参数名是任意的
        nargs='?',  # '?' 表示0或1个参数
        default=None,  # 如果没有提供，则为 None
        help=argparse.SUPPRESS  # 不在帮助信息中显示此参数
    )
    args = parser.parse_args()

    # 场景1: XiaozhiMCP.exe 被 PyInstaller 内部调用来执行另一个脚本 (如 mcp_pipe.py)
    if args.script_to_run_for_pyinstaller is not None:
        logging.info(
            f"'{prog_name}' instance acting as host for script: '{args.script_to_run_for_pyinstaller}'. Letting PyInstaller bootloader proceed.")
        # 此处不需要做任何事情，PyInstaller 的引导程序会在这个脚本执行完毕后处理
        # args.script_to_run_for_pyinstaller 指定的脚本。
        # 通常，这意味着这个实例的 mcp_gui.py 不应该初始化 GUI。
        # 这个脚本会自然结束，PyInstaller的引导加载程序会接管。
        # （根据PyInstaller的工作方式，实际上是这个脚本的Python代码执行完后，
        #  PyInstaller的C引导部分会查找 sys.argv[1] 并执行那个脚本的内容）

    # 场景2: 用户直接运行 XiaozhiMCP.exe 以启动 GUI
    else:
        if args.run_pipe_only:
            logging.info(f"'{prog_name}' called with --run-pipe-only. (Legacy mode, GUI will not start).")
            # 在此模式下，不应启动GUI。如果此模式需要执行实际的管道操作，
            # 那么应该在这里调用相应的逻辑（可能来自 mcp_pipe.py 或类似模块）。
            # 为简单起见，这里直接退出。
            # from mcp_pipe import connect_with_retry # 如果要在此处运行管道
            # try:
            #     asyncio.run(connect_with_retry(os.getenv('MCP_ENDPOINT')))
            # except Exception as e:
            #     logging.error(f"Error running pipe in --run-pipe-only mode: {e}", exc_info=True)
            sys.exit(0)

        # ---- 3. GUI 初始化代码现在在这个条件块内 ----
        logging.info(f"'{prog_name}' starting GUI normally.")

        # 加载环境变量 (现在移到GUI初始化流程中)
        # GUI可能需要.env文件中的某些配置，比如MCP_ENDPOINT的默认值
        # mcp_pipe.py (子进程) 会自己加载其所需的.env配置
        # load_dotenv(resource_path(".env.xiaozhi1")) # 如果GUI也需要
        # endpoint = os.getenv('MCP_ENDPOINT')
        # if not endpoint:
        #     # 对于GUI，如果某些配置是必需的，可以在这里检查并提示
        #     # tkinter.messagebox.showerror('错误', '请在 .env 中为GUI设置必要的配置 (例如 MCP_ENDPOINT)')
        #     # sys.exit(1) # 或者允许在没有某些配置的情况下运行
        #     pass

        # 创建主窗口 (使用全局变量 root)
        globals()['root'] = tk.Tk()
        globals()['root'].title('MCP Pipe GUI')

        # 日志区 (使用全局变量 text_log)
        globals()['text_log'] = scrolledtext.ScrolledText(globals()['root'], width=80, height=20)
        globals()['text_log'].pack(padx=10, pady=(10, 0))

        # 配置并添加 TextHandler 到根日志记录器
        # 必须在 text_log 初始化之后
        gui_log_handler = TextHandler()  # 使用上面定义的 TextHandler 类
        gui_log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(gui_log_handler)
        # logging.getLogger('FileManager').setLevel(logging.INFO) # 如果需要特定配置

        # 按钮区
        top_frame = tk.Frame(globals()['root'])
        top_frame.pack(pady=(5, 10))

        # 定义全局按钮变量以便 run_pipe/stop_pipe 可以访问它们的状态
        # (更好的做法是将这些作为参数传递或使用类来管理GUI状态)
        global btn_run, btn_stop
        btn_run = tk.Button(top_frame, text='启动', width=12, command=run_pipe)
        btn_run.pack(side=tk.LEFT, padx=5)
        btn_stop = tk.Button(top_frame, text='停止', width=12, state=tk.DISABLED, command=stop_pipe)
        btn_stop.pack(side=tk.LEFT, padx=5)

        # 优雅退出处理
        globals()['root'].protocol("WM_DELETE_WINDOW", stop_pipe)

        # 启动 GUI 主循环
        globals()['root'].mainloop()