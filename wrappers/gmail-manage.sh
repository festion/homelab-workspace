#!/bin/bash
# Gmail Manage MCP Server Wrapper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../mcp-servers/gmail-manage-mcp-server"

# Optional: override credentials dir
# export GMAIL_CREDENTIALS_DIR="$HOME/.config/gmail-manage"

cd "$SERVER_DIR" || exit 1
exec uv run --directory "$SERVER_DIR" gmail-manage
