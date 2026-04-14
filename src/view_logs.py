#!/usr/bin/env python3
import json
import os
import sys

LOG_PATH = os.path.expanduser("~/.ai-firewall.log")

def view_logs(limit=50):
    if not os.path.exists(LOG_PATH):
        print("No logs found.")
        return
    
    with open(LOG_PATH, "r") as f:
        lines = f.readlines()
    
    print(f"Last {min(limit, len(lines))} of {len(lines)} events:\n")
    
    for line in lines[-limit:]:
        entry = json.loads(line)
        ts = entry["timestamp"].split("T")[1].split(".")[0]
        decision = entry["decision"]
        tool = entry["tool"]
        reason = entry["reason"]
        
        color = {"ALLOW": "\033[92m", "WARN": "\033[93m", "BLOCK": "\033[91m"}.get(decision, "\033[0m")
        print(f"{color}[{ts}] [{decision}]\033[0m {tool}")
        print(f"     {reason}")
        print()

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    view_logs(limit)
