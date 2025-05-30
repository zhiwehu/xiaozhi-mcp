"""
This script connects to the MCP WebSocket endpoint and pipes data to/from `aggregate.py`.
Exports function `connect_with_retry(uri)` for external callers.
"""
import asyncio
import websockets
import subprocess
import logging
import os
import signal
import sys
import random
import argparse
from dotenv import load_dotenv

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# 默认要执行的 MCP 脚本
mcp_script_name = "aggregate.py"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MCP_PIPE')

# Reconnection settings
INITIAL_BACKOFF = 1
MAX_BACKOFF = 60
MAX_RECONNECT_ATTEMPTS = 5
reconnect_attempt = 0
backoff = INITIAL_BACKOFF

async def connect_with_retry(uri: str):
    """Connect to WebSocket server with retry mechanism"""
    global reconnect_attempt, backoff
    while reconnect_attempt < MAX_RECONNECT_ATTEMPTS:
        try:
            if reconnect_attempt > 0:
                wait_time = backoff * (1 + random.random() * 0.1)
                logger.info(f"等待 {wait_time:.2f}s 后重连 (第 {reconnect_attempt} 次)...")
                await asyncio.sleep(wait_time)
            await _connect_to_server(uri)
            return
        except Exception as e:
            reconnect_attempt += 1
            logger.warning(f"连接失败 (第 {reconnect_attempt} 次): {e}")
            backoff = min(backoff * 2, MAX_BACKOFF)
    logger.error(f"达到最大重试次数 ({MAX_RECONNECT_ATTEMPTS})，终止。")
    raise RuntimeError("无法连接到 WebSocket 服务器")

async def _connect_to_server(uri: str):
    global reconnect_attempt, backoff, mcp_script_name # Add mcp_script_name
    logger.info(f"正在连接到 {uri}...")
    async with websockets.connect(uri) as websocket:
        # ... (connection success logic) ...

        python_exe = sys.executable # This will be the bundled exe or system python

        # Adjust script_path for bundled app
        # aggregate.py should be bundled by PyInstaller at the same level
        script_path = resource_path(mcp_script_name)
        logger.info(f"Full path for {mcp_script_name}: {script_path}")
        if not os.path.exists(script_path):
            logger.error(f"{mcp_script_name} not found at {script_path}!")
            return # Or raise an error

        process = subprocess.Popen(
            [python_exe, script_path], # sys.executable should correctly run bundled python scripts
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            # encoding='utf-8', # Deprecated for Popen
            encoding='utf-8',  # <--- 新增：明确指定使用 UTF-8 编码
            errors='replace',  # <--- 新增 (可选): 更优雅地处理潜在的编码错误，用替换字符替代无法解码的字节
            stderr=subprocess.PIPE, text=True, bufsize=1
            # cwd=os.path.dirname(script_path) # Optional: set CWD if aggregate.py uses relative paths
        )
        logger.info(f"启动子进程: {script_path}")

        try:
            await asyncio.gather(
                _pipe_ws_to_proc(websocket, process),
                _pipe_proc_to_ws(process, websocket),
                _pipe_stderr(process)
            )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(5)
                logger.info("子进程已终止")

async def _pipe_ws_to_proc(websocket, process):
    try:
        async for msg in websocket:
            process.stdin.write(msg + "\n")
            process.stdin.flush()
    except Exception as e:
        logger.error(f"WS→进程 传输错误: {e}")
        raise
    finally:
        process.stdin.close()

async def _pipe_proc_to_ws(process, websocket):
    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, process.stdout.readline)
            if not line:
                break
            await websocket.send(line)
    except Exception as e:
        logger.error(f"进程→WS 传输错误: {e}")
        raise

async def _pipe_stderr(process):
    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, process.stderr.readline)
            if not line:
                break
            sys.stderr.write(line)
    except Exception as e:
        logger.error(f"读取 stderr 错误: {e}")
        raise

# 信号处理
def _signal_handler(sig, frame):
    logger.info("收到中断，退出...")
    sys.exit(0)

if __name__ == '__main__':
    # Allow overriding .env file via argument, useful for packaging
    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument('--env-file', help="Path to .env file to load")
    cli_parser.add_argument('mcp_script_arg', nargs='?', default=mcp_script_name, help="MCP script to run (e.g., aggregate.py)") # For start.sh compatibility
    args = cli_parser.parse_args()

    mcp_script_name = args.mcp_script_arg # Update global from parsed arg if necessary

    # Load .env:
    # 1. Try .env file specified by --env-file
    # 2. Try .env file next to the script/exe (e.g., .env.xiaozhi1)
    # 3. Fallback to default .env if nothing else is found
    env_file_to_load = None
    if args.env_file:
        env_file_to_load = args.env_file
        logger.info(f"Attempting to load .env file from argument: {env_file_to_load}")
    else:
        # Try to find a default .env (e.g., .env.xiaozhi1) next to the executable
        # This name is hardcoded from your start.sh, make it more flexible if needed
        default_env_name = ".env.xiaozhi1"
        potential_env_path = resource_path(default_env_name)
        if os.path.exists(potential_env_path):
            env_file_to_load = potential_env_path
            logger.info(f"Attempting to load .env file from bundled location: {env_file_to_load}")
        else:
            logger.info(f"No specific .env file found at {potential_env_path}, will use environment variables or default .env if present.")
            # If you have a plain ".env" for general defaults, you could try resource_path(".env") here

    if env_file_to_load and os.path.exists(env_file_to_load):
        load_dotenv(dotenv_path=env_file_to_load)
        logger.info(f"Loaded environment variables from: {env_file_to_load}")
    elif args.env_file: # if specified via arg but not found
        logger.error(f"Specified .env file not found: {args.env_file}")
        sys.exit(1)
    else: # No specific file, rely on system env or a default .env in current dir
        load_dotenv() # Loads .env from current working directory or parents
        logger.info("Loaded environment variables from default .env path or system environment.")


    signal.signal(signal.SIGINT, _signal_handler)
    endpoint = os.environ.get('MCP_ENDPOINT')
    if not endpoint:
        logger.error("请在 .env 中或系统环境变量中设置 MCP_ENDPOINT")
        # sys.exit(1) # Allow running even if endpoint is missing, for some scenarios
        # input("按回车键退出...")
        # For GUI, better to show error in GUI or log, not block with input()

    try:
        asyncio.run(connect_with_retry(endpoint if endpoint else "ws://dummy-endpoint")) # Provide a dummy if not set
    except Exception as e:
        logger.error(f"执行出错: {e}", exc_info=True)
        # For GUI, don't use input() here. The error will be logged.
        # if not getattr(sys, 'frozen', False): # Only input() if not bundled, or if specifically console mode
        #    input("按回车键退出...")