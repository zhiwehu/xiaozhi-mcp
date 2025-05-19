source venv/bin/activate;
nohup export ENV_FILE=.env.xiaozhi1;python mcp_pipe.py aggregate.py > mcp.out 2>&1 &