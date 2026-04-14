#!/usr/bin/env python3
"""
AI Agent Permission Firewall - Real MCP Server Proxy
Sits between AI clients and MCP servers, intercepting and filtering tool calls.
"""

import asyncio
import json
import sys
import os
import re
import yaml
import subprocess
from datetime import datetime

try:
    from pync import Notifier
    NOTIFICATIONS_ENABLED = True
except ImportError:
    NOTIFICATIONS_ENABLED = False

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules.yaml")

# Command to spawn the real MCP server
MCP_SERVER_CMD = sys.argv[1:] if len(sys.argv) > 1 else ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/Users/yallappah"]


def load_rules():
    try:
        with open(RULES_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"blocked_paths": [], "blocked_commands": []}


def send_notification(title, message, is_block=True):
    if NOTIFICATIONS_ENABLED:
        Notifier.notify(
            message,
            title=title,
            sound="default" if is_block else None
        )


def log_decision(tool_name, arguments, decision, reason):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "arguments": arguments,
        "decision": decision,
        "reason": reason,
    }
    log_path = os.path.expanduser("~/.ai-firewall.log")
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    color = {"ALLOW": "\033[92m", "WARN": "\033[93m", "BLOCK": "\033[91m"}.get(decision, "\033[0m")
    reset = "\033[0m"
    print(f"{color}[{decision}]{reset} {tool_name}: {reason}", file=sys.stderr)
    
    if decision == "BLOCK":
        send_notification("🚨 AI Firewall BLOCKED", reason, is_block=True)
    elif decision == "WARN":
        send_notification("⚠️ AI Firewall Warning", reason, is_block=False)


def analyze_tool_call(tool_name, arguments, rules):
    """Analyze a tool call against security rules."""
    
    tool_lower = tool_name.lower()
    
    # Detect file-reading tools by name pattern OR by checking arguments
    is_read_tool = any(k in tool_lower for k in ["read", "file", "open", "load", "fetch", "get", "view", "show", "display", "content"])
    is_write_tool = any(k in tool_lower for k in ["write", "edit", "create", "save", "append", "update", "modify", "delete", "remove"])
    
    # Extract path from arguments regardless of tool name
    path = arguments.get("path", "") or arguments.get("file_path", "") or arguments.get("uri", "") or arguments.get("file", "") or arguments.get("filename", "") or arguments.get("target", "")
    
    # Block sensitive file reads
    if is_read_tool and path:
        for blocked in rules.get("blocked_paths", []):
            pattern = blocked.replace("*", ".*")
            if re.search(pattern, path):
                return "BLOCK", f"Attempted to read sensitive path: {path}"
    
    # Block sensitive file writes
    if is_write_tool and path:
        for blocked in rules.get("blocked_paths", []):
            pattern = blocked.replace("*", ".*")
            if re.search(pattern, path):
                return "BLOCK", f"Attempted to write sensitive path: {path}"
    
    # Block dangerous commands
    if any(k in tool_lower for k in ["bash", "shell", "command", "exec", "run", "script", "terminal"]):
        command = arguments.get("command", "") or arguments.get("cmd", "") or arguments.get("executable", "") or arguments.get("script", "") or arguments.get("code", "")
        command_str = command if isinstance(command, str) else " ".join(command)
        
        for blocked in rules.get("blocked_commands", []):
            pattern = blocked.replace(".*", ".*")
            if re.search(pattern, command_str, re.IGNORECASE):
                return "BLOCK", f"Dangerous command pattern detected: {blocked}"
        
        if re.search(r"(curl|wget|fetch)\s+.*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", command_str, re.IGNORECASE):
            return "WARN", f"Network call to raw IP address: {command_str[:50]}"
        
        if re.search(r"(curl|wget).*(-d|--data|-T|--upload-file)", command_str, re.IGNORECASE):
            return "WARN", f"Potential data upload/exfiltration: {command_str[:50]}"
    
    return "ALLOW", "No risk patterns detected"


async def proxy_mcp():
    """
    Bidirectional proxy between MCP client (stdin/stdout) and MCP server (subprocess).
    """
    rules = load_rules()
    
    print("🔥 AI Agent Firewall starting...", file=sys.stderr)
    print(f"Spawning MCP server: {' '.join(MCP_SERVER_CMD)}", file=sys.stderr)
    print("Monitoring all tool calls. Logs: ~/.ai-firewall.log", file=sys.stderr)
    
    # Start the real MCP server as a subprocess
    proc = await asyncio.create_subprocess_exec(
        *MCP_SERVER_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Task to forward server stderr to our stderr (so we can see server logs)
    async def forward_stderr():
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            sys.stderr.buffer.write(b"[SERVER] " + line)
            sys.stderr.flush()
    
    asyncio.create_task(forward_stderr())
    
    # Forward client -> server, with interception
    async def client_to_server():
        while True:
            try:
                line = await asyncio.to_thread(sys.stdin.readline)
                if not line:
                    break
                
                try:
                    message = json.loads(line.strip())
                except json.JSONDecodeError:
                    # Not JSON, forward as-is
                    proc.stdin.write(line.encode())
                    await proc.stdin.drain()
                    continue
                
                # Intercept tool calls
                method = message.get("method", "")
                if method == "tools/call" or method.startswith("tools/"):
                    params = message.get("params", {})
                    tool_name = params.get("name", "unknown")
                    arguments = params.get("arguments", {})
                    
                    decision, reason = analyze_tool_call(tool_name, arguments, rules)
                    log_decision(tool_name, arguments, decision, reason)
                    
                    if decision == "BLOCK":
                        response = {
                            "jsonrpc": "2.0",
                            "id": message.get("id"),
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"🚨 AI Agent Firewall BLOCKED: {reason}"
                                    }
                                ],
                                "isError": True
                            }
                        }
                        print(json.dumps(response))
                        sys.stdout.flush()
                        continue
                
                # Forward allowed messages to server
                proc.stdin.write(line.encode())
                await proc.stdin.drain()
                
            except Exception as e:
                print(f"Client->Server error: {e}", file=sys.stderr)
                break
    
    # Forward server -> client (pass-through)
    async def server_to_client():
        while True:
            try:
                line = await proc.stdout.readline()
                if not line:
                    break
                
                sys.stdout.buffer.write(line)
                sys.stdout.flush()
                
            except Exception as e:
                print(f"Server->Client error: {e}", file=sys.stderr)
                break
    
    # Run both directions concurrently
    await asyncio.gather(client_to_server(), server_to_client())
    
    # Cleanup
    proc.stdin.close()
    await proc.wait()


if __name__ == "__main__":
    asyncio.run(proxy_mcp())
