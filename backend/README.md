# RepoMemory

**AI-powered code retrieval engine — index any GitHub repo, search with natural language**

[![PyPI](https://img.shields.io/pypi/v/repomemory.svg)](https://pypi.org/project/repomemory/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/repomemory.svg)](https://pypi.org/project/repomemory/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3572A5.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/aayushakumar/RepoMemory/actions/workflows/ci.yml/badge.svg)](https://github.com/aayushakumar/RepoMemory/actions/workflows/ci.yml)

*Point it at any GitHub URL. Get token-budget-aware context packs — ready to paste into any LLM. Free to run, free to deploy.*

---

## What is RepoMemory?


When you ask an LLM to fix a bug or trace a feature, it needs the *right* source files. Pasting the whole codebase wastes the context window. Guessing which files to include misses critical pieces.

RepoMemory solves this with a **hybrid retrieval pipeline** that runs on any public or private GitHub repo:

```bash
repomemory index https://github.com/pallets/flask
repomemory search "Where is request routing handled?"
```

```
Query  →  Task Classification (trace_flow)
       →  BM25 Lexical + FAISS Semantic + Fuzzy Path + Symbol search  (parallel)
       →  Reciprocal Rank Fusion  →  Top-20 ranked files
       →  Dependency-graph expansion  →  Re-rank with adaptive weights
       →  Token-budget packer  →  Context pack ready to paste into any LLM
       →  (optional) Groq AI summary
```

---

## Install

```bash
# Core — CLI + library, uses HuggingFace API for embeddings (no GPU needed)
pip install repomemory

# With local embeddings (~80 MB model download, fully offline)
pip install "repomemory[local]"

# With FastAPI web server
pip install "repomemory[server]"

# With Groq LLM explanations (free API key)
pip install "repomemory[llm]"

# Everything
pip install "repomemory[all]"
```

---

## Quick Start

### CLI

```bash
# Index a repo
repomemory index https://github.com/pallets/flask

# Search it
repomemory search "How does request routing work?"

# With AI explanations (free Groq key)
export REPOMEMORY_GROQ_API_KEY=gsk_...
repomemory search "Where is token rotation handled?"

# Adjust result count and token budget
repomemory search "auth middleware" --top-k 10 --budget 4000

# Force a task mode
repomemory search "test coverage for auth" --mode test_lookup

# Private repos
repomemory index https://github.com/myorg/private-repo --token ghp_...

# List indexed repos
repomemory list

# Start the web UI + API server
repomemory serve
```

### Python library

```python
from repomemory import RepoMemory

rm = RepoMemory()

# Index
repo = rm.index("https://github.com/pallets/flask")

# Search
result = rm.search("How does request dispatching work?")
for file in result.context_pack.files:
    print(f"{file.path}  score={file.relevance_score:.2f}")
    print(file.snippets[0].content[:300])
```

### REST API

```bash
# Start the server
pip install "repomemory[server]"
repomemory serve

# Index a repo
curl -X POST http://localhost:8000/api/repos \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/pallets/flask"}'

# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "query": "How does routing work?", "token_budget": 8000}'
```

---

## Features

| Feature | Details |
|---|---|
| **Hybrid search** | BM25 lexical + FAISS semantic (384-dim) + fuzzy path + symbol name, fused with Reciprocal Rank Fusion |
| **Dependency-graph retrieval** | Builds file-level import edges at index time; expands results through related files via BFS |
| **Adaptive weight learning** | Online SGD learning from user feedback (accept / dismiss / thumbs); falls back to static mode weights |
| **Symbol-aware indexing** | tree-sitter extracts functions, classes, and methods from Python, JavaScript, and TypeScript |
| **5 Task Modes** | `bug_fix`, `trace_flow`, `test_lookup`, `config_lookup`, `general` — auto-detected from query or set manually |
| **Token-budget packer** | Greedy packer respects any token limit (default 8 000 tokens, configurable up to 100 000+) |
| **Behavioral memory** | Frecency scoring from opened / accepted / thumbs-up actions; boosts relevant files in future queries |
| **RAG evaluation** | End-to-end pipeline scoring retrieval impact on LLM answer quality (relevance, completeness, faithfulness) |
| **Flexible embeddings** | Local `sentence-transformers` (offline) or free HuggingFace Inference API |
| **AI explanations** | Optional Groq LLM (free tier) explains why each result matters |
| **Incremental indexing** | SHA-256 per file; only changed files are re-embedded on re-index |
| **Web UI + REST API** | React 19 frontend + FastAPI backend; deploy on Render + Vercel (both free) |
| **Export as Markdown** | Copy context pack as a formatted Markdown block to paste directly into an LLM prompt |

---

## Task Modes

RepoMemory classifies each query and adjusts retrieval weights automatically:

| Mode | Auto-detected from | What it boosts |
|---|---|---|
| `bug_fix` | `error`, `exception`, `crash`, `fix`, `traceback` | Lexical signal, error-adjacent files |
| `trace_flow` | `trace`, `flow`, `route`, `handler`, `how does...work` | Symbol matching, call-chain ordering |
| `test_lookup` | `test`, `spec`, `mock`, `fixture`, `coverage` | Path matching for `tests/` / `spec/` dirs |
| `config_lookup` | `config`, `env`, `setting`, `yaml`, `toml` | Path matching for config-like files |
| `general` | *(fallback)* | Balanced across all signals |

---

## Configuration

All settings use the `REPOMEMORY_` env prefix (powered by `pydantic-settings`):

```bash
export REPOMEMORY_HF_API_KEY=hf_...          # HuggingFace free API key
export REPOMEMORY_GROQ_API_KEY=gsk_...       # Groq free API key (for AI summaries)
export REPOMEMORY_EMBEDDING_PROVIDER=local   # 'local' or 'huggingface'
export REPOMEMORY_DATA_DIR=/data/repomemory  # where SQLite + FAISS live
export REPOMEMORY_TOKEN_BUDGET=16000         # default context pack size
```

---

## Links

- **GitHub** — [github.com/aayushakumar/RepoMemory](https://github.com/aayushakumar/RepoMemory) (full docs, architecture diagram, contributing guide)
- **Issues** — [github.com/aayushakumar/RepoMemory/issues](https://github.com/aayushakumar/RepoMemory/issues)
- **Changelog** — [github.com/aayushakumar/RepoMemory/releases](https://github.com/aayushakumar/RepoMemory/releases)
- **API Docs** (when running locally) — `http://localhost:8000/docs`

---

## License

MIT © Aayush Kumar
