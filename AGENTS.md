# AGENTS.md - Development Instructions for AI Agents

This file contains instructions for AI agents working on the OllamaTUI project.

## Project Overview

OllamaTUI is an agentic Terminal User Interface for macOS 10.15+ that works with Ollama local models and Ollama Cloud models with API key authentication. It's built with Python and Textual.

## Development Environment

- **OS**: macOS 10.15 (Catalina) - MUST maintain compatibility
- **Python**: 3.10+ (3.14.5 available)
- **Key Dependencies**: Textual, Ollama Python SDK, pytest, pydantic

## Code Style & Conventions

### Python Style
- Follow PEP 8
- Use type hints for all public functions
- Use `async`/`await` for all I/O operations
- Use Pydantic for data validation
- Maximum line length: 100 characters

### Project Structure
```
src/ollamatui/
├── main.py              # CLI entry point
├── app.py               # Textual App class
├── config.py            # Configuration (TOML)
├── providers/           # Ollama API providers
│   ├── base.py          # Abstract base provider
│   ├── local.py         # Local daemon provider
│   └── cloud.py         # Cloud API provider
├── tools/               # Agent tools
│   ├── base.py          # Abstract base tool
│   ├── file.py          # File operations
│   ├── bash.py          # Bash execution
│   └── git.py           # Git operations
├── widgets/             # Textual widgets
│   ├── chat.py          # Chat interface
│   ├── model_selector.py
│   └── file_tree.py
└── sessions/            # Session management
    └── manager.py
```

## Key Architectural Principles

### 1. Provider Abstraction
All Ollama interactions go through the provider layer:
- `LocalOllamaProvider` - connects to `http://localhost:11434`
- `CloudOllamaProvider` - connects to `https://ollama.com/api` with Bearer token
- Both implement `BaseOllamaProvider` interface

### 2. Tool System
Tools are self-contained classes that the agent can invoke:
- Each tool has a `name`, `description`, and `parameters` schema
- Tools return structured results
- Approval system wraps tool execution

### 3. Async-First
All network I/O, file I/O, and process execution must be async:
- Use `asyncio` and `aiofiles`
- Use `async_subprocess` for bash commands
- Textual widgets use async message handling

### 4. Configuration
- TOML-based config in `~/.ollamatui/config.toml`
- Profile support via layered configs
- CLI flags override config values
- Environment variables for secrets (API keys)

## Testing Requirements

### Test Organization
```
tests/
├── unit/
│   ├── test_providers.py
│   ├── test_tools.py
│   └── test_config.py
├── integration/
│   ├── test_chat_flow.py
│   └── test_session.py
└── widgets/
    └── test_chat_widget.py
```

### Testing Rules
- **Every new feature must have tests**
- Unit tests for providers, tools, config
- Integration tests for chat flows
- Widget tests using Textual's testing utilities
- Mock external APIs (Ollama, Git, etc.)
- Run tests with: `pytest -v --cov=ollamatui`

## Git Workflow

### Branching
- `main` - stable releases
- Feature branches: `feature/<issue-number>-<description>`
- Bug fix branches: `fix/<issue-number>-<description>`

### Commits
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- One logical change per commit
- Reference issues: `fixes #123`

### Pull Requests
- Must pass all tests
- Must have test coverage for new code
- Update documentation if needed
- Link to GitHub issue

## Implementation Phases

### Phase 1: Core TUI & Ollama Integration (Milestone 1)
Issues: #1-#5
1. Project setup with Textual
2. Chat interface with message history
3. Provider abstraction layer
4. Model selection UI
5. Streaming chat implementation

### Phase 2: Agentic Capabilities (Milestone 2)
Issues: #6-#8
1. File operations tool
2. Bash execution with approvals
3. Git integration

### Phase 3: Advanced Features (Milestone 3)
Issues: #9-#12
1. Session management
2. MCP support
3. Configuration system
4. Web search tool

### Phase 4: Polish & Distribution (Milestone 4)
Issues: #13-#14
1. Comprehensive test suite
2. Packaging and documentation

## Common Commands

```bash
# Run the TUI
python -m ollamatui

# Run tests
pytest -v

# Run with coverage
pytest --cov=ollamatui --cov-report=html

# Type checking
mypy src/ollamatui

# Linting
ruff check src/ollamatui

# Format code
ruff format src/ollamatui

# Build standalone binary (later)
pyinstaller --onefile src/ollamatui/main.py
```

## Important Constraints

### macOS 10.15 Compatibility
- **DO NOT** use APIs only available in macOS 11+
- **DO NOT** depend on libraries requiring macOS 11+
- Test on macOS 10.15 regularly
- Use `sys.version_info` checks if needed

### Ollama API
- Local: `http://localhost:11434/api/*`
- Cloud: `https://ollama.com/api/*` with `Authorization: Bearer <key>`
- Cloud models use names WITHOUT `:cloud` suffix in direct API
- Cloud models use `:cloud` suffix when via local proxy

### Security
- Never log API keys
- Validate all file paths against workspace root
- Sanitize shell command inputs
- Use subprocess with explicit args (no shell=True)

## Debugging Tips

### Enable Debug Logging
```bash
OLLAMATUI_DEBUG=1 python -m ollamatui
```

### Textual Debug Mode
```bash
python -m ollamatui --dev
```

### Inspect Ollama API
```bash
# Local
curl http://localhost:11434/api/tags

# Cloud (with API key)
curl -H "Authorization: Bearer $OLLAMA_API_KEY" https://ollama.com/api/tags
```

## Adding New Features

1. **Check existing issues** - Don't duplicate work
2. **Create GitHub issue** if not exists
3. **Write tests first** (TDD approach)
4. **Implement feature** following patterns
5. **Add documentation** in docstrings and README
6. **Run full test suite** before committing

## Code Review Checklist

- [ ] Tests pass
- [ ] Type hints present
- [ ] Async/await used correctly
- [ ] No sync I/O in async functions
- [ ] Error handling implemented
- [ ] Logging appropriate (not verbose)
- [ ] macOS 10.15 compatible
- [ ] Documentation updated
- [ ] No hardcoded secrets

## Resources

- [Textual Documentation](https://textual.textualize.io)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Cloud Docs](https://github.com/ollama/ollama/blob/main/docs/cloud.mdx)
- [Ollama Python SDK](https://github.com/ollama/ollama-python)
- [Codex CLI Reference](https://github.com/openai/codex)
