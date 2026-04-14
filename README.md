# 🔥 AI Agent Permission Firewall

A lightweight, real-time firewall that intercepts AI coding assistant tool calls (Claude, Cursor, Copilot, etc.) through MCP servers and blocks dangerous operations before they execute.

## What It Does

- **Monitors** every tool call your AI assistant makes through MCP servers
- **Blocks** access to sensitive files (`~/.ssh`, `~/.aws`, `.env`, passwords, tokens, etc.)
- **Blocks** dangerous shell commands (data exfiltration, reverse shells, credential harvesting)
- **Warns** on suspicious network calls to raw IP addresses
- **Logs** everything for audit and transparency
- **Shows native macOS notifications** when threats are detected

## How It Works


AI Assistant (Claude Desktop)
↓
MCP Request
↓
┌───────────────────┐
│  AI Agent Firewall│ ← Intercepts and analyzes every request
│    (proxy.py)     │
└───────────────────┘
┌─────┴─────┐
BLOCK           ALLOW
↓              ↓
Error          Real MCP Server
Notification   (filesystem, puppeteer, etc.)


## Requirements

- macOS or Linux
- Python 3.11+
- Node.js (for MCP servers)
- Claude Desktop (or any MCP-compatible AI assistant)

## Installation

### Step 1: Copy the Project

Copy the `agentic_firewall` folder to the new computer. Keep the folder structure intact:
- `src/proxy.py`
- `src/view_logs.py`
- `rules.yaml`
- `README.md`

### Step 2: Install Python Dependencies

```bash
pip install pyyaml pync
```
Linux users: pync only works on macOS. On Linux, notifications will be logged but not shown as popups. You can install notify2 for Linux notifications if desired.

### Step 3: Find Your Python Path

This is the most important step. Run:
```bash
which python3
```
Copy the exact output. It will look something like:
```bash
• /usr/local/bin/python3
• /Users/yourname/anaconda3/bin/python3
• /opt/homebrew/bin/python3
```
You MUST use this exact path in Step 4.

### Step 4: Configure Claude Desktop

Open Claude Desktop's MCP config file:

# On macOS:
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```
Use the ABSOLUTE path to python3 from Step 3. Here is an example config:
```bash
{
  "mcpServers": {
    "filesystem": {
      "command": "/FULL/PATH/TO/python3",
      "args": [
        "/FULL/PATH/TO/agentic_firewall/src/proxy.py",
        "/opt/homebrew/bin/node",
        "/opt/homebrew/lib/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js",
        "/Users/yourname"
      ]
    },
    "puppeteer": {
      "command": "/FULL/PATH/TO/python3",
      "args": [
        "/FULL/PATH/TO/agentic_firewall/src/proxy.py",
        "/opt/homebrew/bin/node",
        "/opt/homebrew/lib/node_modules/@modelcontextprotocol/server-puppeteer/dist/index.js"
      ]
    }
  }
}
```
Important replacements:

• Replace /FULL/PATH/TO/python3 with the exact output from which python3
• Replace /FULL/PATH/TO/agentic_firewall with wherever you copied this project
• Replace /Users/yourname with your actual home directory
• Update the /opt/homebrew/... paths if your Node.js or MCP servers are installed elsewhere

### Step 5: Restart Claude Desktop

1. Fully quit Claude Desktop (Cmd+Q)
2. Reopen it
3. Go to Claude → Settings → Developer → MCP Servers
4. Verify your servers show as running (green dot)

Usage

Once configured, the firewall runs automatically in the background whenever Claude Desktop uses an MCP server.

Test a Blocked Request

Ask Claude:

"Read my ~/.ssh/id_rsa file"

Expected result:

• 🔴 Terminal/log shows: [BLOCK]
• 🔔 macOS notification pops up: "🚨 AI Firewall BLOCKED"
• Claude shows an error that the request was blocked

Test an Allowed Request

Ask Claude:

"Create a README.md file in my project folder"

Expected result:

• 🟢 Log shows: [ALLOW]
• File is created normally
• No notification

View Logs
```bash
python3 /FULL/PATH/TO/agentic_firewall/src/view_logs.py
```
Or watch live:
```bash
tail -f ~/.ai-firewall.log
```
Customizing Security Rules
Edit rules.yaml to add or remove blocked paths and commands:

blocked_paths:
  - "~/.ssh/*"
  - "~/.aws/*"
  - "~/.env"
  - "*/secrets.*"
  - "*/credentials.*"

blocked_commands:
  - "curl.*-d.*@"
  - "base64.*<.*(~|/\\.ssh|/\\.aws|/\\.env)"
  - "eval\\s*\\("
  - "bash.*-i.*>&.* /dev/tcp/"

Restart Claude Desktop after editing rules.yaml for changes to take effect.

Troubleshooting

MCP servers show as "failed" in Claude Desktop

1. Check python3 path: Run which python3 and make sure the config uses the exact full path
2. Check MCP server paths: Make sure the .js files actually exist at those locations
3. Check Claude Desktop logs:cat ~/Library/Logs/Claude/mcp*.log | tail -20

Notifications don't appear on Linux

pync is macOS-only. Install notify2:
```bash
pip install notify2
```
Then modify proxy.py to use notify2 instead of pync.

Safe requests getting blocked (false positives)

Edit rules.yaml and remove or refine overly broad patterns. Restart Claude Desktop after changes.

Architecture

| File             | Purpose                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| src/proxy.py     | The firewall engine. Spawns real MCP servers and intercepts all traffic |
| src/view_logs.py | CLI tool to view firewall decision history                              |
| rules.yaml       | Human-editable security rules                                           |
| README.md        | This file                                                               |

Future Roadmap

• [ ] Desktop menubar app (no Terminal needed)
• [ ] Sandbox mode (run suspicious commands in isolated Docker containers)
• [ ] GUI rule editor
• [ ] Windows support
• [ ] Real-time dashboard

Credits

Built by Samant Patil.