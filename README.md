# OllamaTUI

An agentic Terminal User Interface (TUI) for macOS 10.15+ that works with Ollama local models and Ollama Cloud models, with API key authentication.

## Features

- **Cross-platform TUI**: Built with Textual, works on macOS 10.15+
- **Local Ollama Models**: Use any model installed locally via `ollama pull`
- **Ollama Cloud Models**: Access cloud models (Nemotron-3-Ultra, Gemma-4, GLM-5.1, Gemini, DeepSeek, Devstral, etc.) via local proxy or direct API
- **API Key Authentication**: Secure authentication with Ollama Cloud using API keys
- **Agentic Capabilities**: File operations, bash execution, Git integration
- **Sandbox Modes**: Read-only, workspace-write, danger-full-access
- **Approval Policies**: Untrusted, on-request, never
- **Session Management**: Save, resume, fork, and archive sessions
- **Streaming Responses**: Real-time token streaming from models
- **Markdown & Syntax Highlighting**: Rich rendering of code and markdown

## Installation

### Prerequisites

- macOS 10.15 (Catalina) or later
- Python 3.10+
- Ollama installed and running locally

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull some local models
ollama pull qwen2.5-coder:3b
ollama pull mistral:latest
```

### Install OllamaTUI

```bash
# Clone the repository
git clone https://github.com/janipasanen/ollamaTUI.git
cd ollamaTUI

# Install dependencies
pip install -e .

# Or install with pipx for isolated environment
pipx install .
```

## Quick Start

### 1. Start Ollama locally

```bash
ollama serve
```

### 2. Run OllamaTUI

```bash
# With local models
ollamatui

# With Ollama Cloud (requires API key)
export OLLAMA_API_KEY=your_api_key_from_ollama.com
ollamatui --provider cloud
```

### 3. Get an Ollama Cloud API Key

1. Go to https://ollama.com/settings/keys
2. Create a new API key
3. Export it: `export OLLAMA_API_KEY=your_key`

## Usage

### Basic Commands

```bash
# Start interactive TUI
ollamatui

# Run non-interactively (like codex exec)
ollamatui exec "refactor this function"

# Code review
ollamatui review

# Use specific model
ollamatui -m qwen2.5-coder:3b

# Use cloud model directly
ollamatui -m nemotron-3-ultra --provider cloud

# Set sandbox mode
ollamatui --sandbox read-only

# Set approval policy
ollamatui --approval on-request

# Resume last session
ollamatui resume

# List sessions
ollamatui sessions
```

### Configuration

Configuration is stored in `~/.ollamatui/config.toml`:

```toml
# Default model
model = "qwen2.5-coder:3b"

# Provider: "local" or "cloud"
provider = "local"

# Sandbox mode: "read-only", "workspace-write", "danger-full-access"
sandbox = "workspace-write"

# Approval policy: "untrusted", "on-request", "never"
approval = "on-request"

# Ollama Cloud API key (or use OLLAMA_API_KEY env var)
# api_key = "your_key_here"

# Working directory
working_dir = "."

# Additional writable directories
add_dirs = []
```

### Profiles

Create profiles for different workflows:

```bash
# Create a profile
ollamatui --profile coding

# This loads ~/.ollamatui/coding.config.toml on top of base config
```

## Supported Models

### Local Models (via Ollama)
Any model from `ollama pull`:
- `qwen2.5-coder:3b` - Great for coding
- `mistral:latest` - General purpose
- `llama2:latest` - Meta's LLaMA 2
- `phi:latest` - Microsoft's Phi
- `gemma:2b` - Google's Gemma
- `starcoder2:latest` - Code generation

### Cloud Models (via Ollama Cloud)
Available at https://ollama.com/search?c=cloud:
- `nemotron-3-ultra:cloud` - NVIDIA's Nemotron 3 Ultra
- `gemma-4:31b-cloud` - Google's Gemma 4
- `glm-5.1:cloud` - Zhipu's GLM 5.1
- `gemini-3-flash-preview:cloud` - Google's Gemini
- `deepseek-v4-pro:cloud` - DeepSeek V4 Pro
- `devstral-2:123b-cloud` - Devstral 2

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        OllamaTUI                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Textual   │  │  Async Core │  │   Provider Layer    │  │
│  │    TUI      │◄─┤  (Agent)    │◄─┤  (Ollama Local/Cloud)│  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│        ▲                ▲                     ▲              │
│        │                │                     │              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Widgets    │  │  Tools      │  │   Config/Session    │  │
│  │  (Chat,     │  │  (File,     │  │   (TOML + SQLite)   │  │
│  │   Files,    │  │   Bash,     │  │                     │  │
│  │   Diff)     │  │   Git)      │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Development

### Setup

```bash
# Clone and enter directory
git clone https://github.com/janipasanen/ollamaTUI.git
cd ollamaTUI

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run the TUI
python -m ollamatui
```

### Project Structure

```
ollamaTUI/
├── src/ollamatui/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── app.py               # Textual app
│   ├── config.py            # Configuration management
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # Base provider class
│   │   ├── local.py         # Local Ollama provider
│   │   └── cloud.py         # Cloud Ollama provider
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py          # Base tool class
│   │   ├── file.py          # File operations
│   │   ├── bash.py          # Bash execution
│   │   └── git.py           # Git operations
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── chat.py          # Chat interface
│   │   ├── model_selector.py
│   │   └── file_tree.py
│   └── sessions/
│       ├── __init__.py
│       └── manager.py       # Session management
├── tests/
├── pyproject.toml
├── README.md
└── AGENTS.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.com) for the amazing local LLM platform
- [Textual](https://textual.textualize.io) for the excellent TUI framework
- [Codex CLI](https://github.com/openai/codex) for inspiration
- [Claude Code](https://claude.ai/code) for inspiration
