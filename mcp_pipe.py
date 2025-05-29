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
from dotenv import load_dotenv

# 默认要执行的 MCP 脚本
mcp_script = "aggregate.py"

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
    global reconnect_attempt, backoff
    logger.info(f"正在连接到 {uri}...")
    async with websockets.connect(uri) as websocket:
        logger.info("已连接")
        reconnect_attempt = 0
        backoff = INITIAL_BACKOFF

        # Python 可执行文件路径
        python_exe = sys.executable
        # 脚本路径
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), mcp_script
        )
        process = subprocess.Popen(
            [python_exe, script_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1
        )
        logger.info(f"启动子进程: {mcp_script}")

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
    load_dotenv()
    signal.signal(signal.SIGINT, _signal_handler)
    endpoint = os.environ.get('MCP_ENDPOINT')
    if not endpoint:
        logger.error("请在 .env 中设置 MCP_ENDPOINT")
        sys.exit(1)
    try:
        asyncio.run(connect_with_retry(endpoint))
    except Exception as e:
        logger.error(f"执行出错: {e}")
        input("按回车键退出...")