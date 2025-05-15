# MCP in the Wild

A real-world implementation of the Model Context Protocol (MCP) using LangChain, Flask, and OpenAI.

This project powers the [MCP in the Wild](https://emergentailabs.substack.com/) article.

## 📦 Features

- 🧠 LangChain agents calling local HTTP tools (via `/manifest`)
- 🧪 Creativity score, math ops, weather simulation, and datetime tools
- 🧰 Zero-agent mode + ReAct + web UI with Flask
- 🧵 Async batch invocation
- 📄 Fully documented with step-by-step examples

## 📂 Structure

- `mcp_server.py` — Flask server exposing tools via MCP
- `advanced_mcp_client.py` — LangChain wrapper with batch and schema helpers
- `langchain_app.py` — Web UI + agent endpoint
- `zero_agent_mcp_client.py` — Simpler GPT-only fallback interface

## 🧪 Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python mcp_server.py     # terminal 1
python langchain_app.py  # terminal 2