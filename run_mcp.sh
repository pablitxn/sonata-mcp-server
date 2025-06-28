#!/bin/bash
# Run MCP dev server with correct PYTHONPATH

export PYTHONPATH=/home/pablitxn/repos/sonata_mcp_server/src:$PYTHONPATH
cd /home/pablitxn/repos/sonata_mcp_server/src
mcp dev main.py "$@"