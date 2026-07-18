# Handson-Exercise — AI Agent Playground

A LangChain/LangGraph-based multi-agent FastAPI server with a React chat UI. Supports two LLM backends (Ollama and SAP Hyperspace/Anthropic) with tool use, persistent in-memory store, MCP tool integration, and human-in-the-loop approval for MCP tool calls.

## Project Structure

```text
├── server.py            # FastAPI server — /askMe, /sapAgent, /sapAgent/resume endpoints
├── agent.py             # User context schema (User) and get_user_info tool
├── agent_with_store.py  # Ollama agent with InMemoryStore (get/set_store_info tools)
├── model.py             # LLM instances: model (Ollama), model_sap (Anthropic via SAP Hyperspace)
├── mcp_client.py        # MultiServerMCPClient config for MCP tool servers
├── dynamic_prompt.py    # Dynamic prompt utilities
├── start.sh             # Start both backend and UI dev server
├── .env                 # Environment variables (git-ignored)
└── ui/                  # React + Vite chat frontend
```

## Setup

### 1. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> All direct dependencies are listed in [`requirements.txt`](requirements.txt). Transitive dependencies are resolved automatically by pip.

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
# Ollama
OLLAMA_API_KEY=...
OLLAMA_BASE_URL=https://api.ollama.com
OLLAMA_MODEL_NAME=gpt-oss:120b

# SAP Hyperspace (Anthropic-compatible)
SAP_HYPERSPACE_BASE_URL=http://localhost:6655
SAP_HYPERSPACE_MODEL=claude-sonnet-latest
SAP_HYPERSPACE_API_KEY=...
```

### 3. Install UI dependencies

```bash
cd ui && npm install
```

### 4. Start

```bash
./start.sh
```

- Backend: <http://localhost:8000>
- UI: <http://localhost:5173>

## Endpoints

| Endpoint | Model | Description |
| --- | --- | --- |
| `POST /askMe` | Ollama | Streaming chat with in-memory store (NDJSON) |
| `POST /sapAgent` | Anthropic | Chat with MCP tools + human-in-the-loop approval |
| `POST /sapAgent/resume` | Anthropic | Resume after human approves/rejects a tool call |
| `POST /askMeTest` | Ollama | Simple non-streaming test endpoint |

## Human-in-the-Loop (MCP Tool Approval)

When the SAP agent wants to call an MCP tool, it pauses and returns an interrupt payload:

```json
{ "type": "interrupt", "interrupts": [[{ "action_requests": [...], "review_configs": [...] }]] }
```

The UI shows an **Approve / Reject** card. On decision, it calls `/sapAgent/resume`:

```json
{ "user_id": "RK01", "decisions": [{ "type": "approve" }] }
```

Decision types: `approve`, `reject`, `edit`, `respond`.

## Features

- **Dual model switcher** — toggle between Ollama and Anthropic in the UI
- **Streaming responses** — Ollama endpoint streams via NDJSON with progress updates
- **Persistent store** — save/retrieve facts across questions (Ollama agent)
- **MCP tool integration** — connect external tool servers via `mcp_client.py`
- **Human-in-the-loop** — approve or reject MCP tool calls before execution
- **Dark/light theme** toggle
