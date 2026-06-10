# Feature Analysis: Agentic TUIs for macOS 10.15

## Executive Summary

This document analyzes the features of existing agentic TUIs (opencode, codex, claude CLI) and evaluates their compatibility with macOS 10.15 (Catalina). The goal is to design a new agentic TUI that works on macOS 10.15, supports Ollama local and cloud models, and authenticates using Ollama API key.

## System Environment

- **OS**: macOS 10.15.8 (Catalina)
- **Python**: 3.14.5
- **Node.js**: v22.22.1
- **Go**: 1.22.12
- **Rust**: 1.91.1
- **Ollama**: 0.20.2 (local)
- **Available local models**: qwen2.5-coder:3b, gemma:2b, phi:latest, starcoder2:latest, mistral:latest, llama2:latest
- **Cloud models tested**: nemotron-3-ultra:cloud (works via local Ollama proxy)

## Existing Tools Analysis

### 1. Codex CLI (OpenAI)

**Installation**: Available as binary (`/usr/local/bin/codex`)

**Key Features**:
- Interactive TUI with agentic coding capabilities
- Non-interactive execution modes (`exec`, `review`)
- Session management (resume, fork, archive, unarchive)
- Sandbox modes: read-only, workspace-write, danger-full-access
- Approval policies: untrusted, on-request, never
- Model selection (`-m` flag)
- Local provider support (--oss, --local-provider ollama/lmstudio)
- MCP server management
- Plugin system
- Remote connection support (WebSocket)
- Config via TOML (`~/.codex/config.toml`)
- Profile support
- Web search integration
- Git integration (apply diffs)
- Image attachment support

**macOS 10.15 Compatibility**: ✅ Works (binary runs)

### 2. Claude Code (Anthropic)

**Installation**: Available as binary (`/usr/local/bin/claude`) but **FAILS on macOS 10.15**
- Error: `dyld: Symbol not found: _ubrk_clone`
- Built for macOS 13.0+, requires ICU library not available on 10.15

**Key Features** (from documentation):
- Agentic coding assistant
- File operations (read, write, edit)
- Bash command execution
- Git integration
- MCP support
- Session management

**macOS 10.15 Compatibility**: ❌ **DOES NOT WORK** - binary incompatible

### 3. OpenCode

**Installation**: Not available via npm (package not found)
- Appears to be a different project or not published to npm

**macOS 10.15 Compatibility**: Unknown (not installable)

### 4. Ollama CLI (Built-in)

**Key Features**:
- Local model management (pull, run, list, delete)
- Cloud model support via `ollama run model:cloud` (proxies through local daemon)
- Direct cloud API access via `https://ollama.com/api/` with Bearer token auth
- OpenAI-compatible API endpoint
- Python/JS SDKs available

**Authentication**: 
- Local: No auth needed (uses local daemon)
- Cloud: `OLLAMA_API_KEY` environment variable + `Authorization: Bearer <key>` header
- API Key created at https://ollama.com/settings/keys

**macOS 10.15 Compatibility**: ✅ Works perfectly

## Feature Comparison Matrix

| Feature | Codex CLI | Claude Code | Ollama CLI | Target TUI |
|---------|-----------|-------------|------------|------------|
| Interactive TUI | ✅ | ✅ | ❌ | ✅ |
| Agentic coding | ✅ | ✅ | ❌ | ✅ |
| File operations | ✅ | ✅ | ❌ | ✅ |
| Bash execution | ✅ | ✅ | ❌ | ✅ |
| Git integration | ✅ | ✅ | ❌ | ✅ |
| Session management | ✅ | ✅ | ❌ | ✅ |
| Sandbox/approvals | ✅ | ✅ | ❌ | ✅ |
| Multiple models | ✅ | ❌ | ✅ | ✅ |
| Local Ollama models | ✅ (--local-provider) | ❌ | ✅ | ✅ |
| Ollama Cloud models | ✅ (via local proxy) | ❌ | ✅ | ✅ |
| Direct Cloud API | ❌ | ❌ | ✅ | ✅ |
| API Key auth | ❌ | ❌ | ✅ | ✅ |
| MCP support | ✅ | ✅ | ❌ | ✅ (planned) |
| Plugin system | ✅ | ❌ | ❌ | ✅ (planned) |
| Web search | ✅ | ❌ | ❌ | ✅ (planned) |
| Image support | ✅ | ✅ | ❌ (vision models only) | ✅ |
| macOS 10.15 support | ✅ | ❌ | ✅ | ✅ |

## Language Selection for Target TUI

### Options Considered:

1. **Python** (with Textual/Textualize)
   - ✅ Excellent TUI framework (Textual)
   - ✅ Native on macOS 10.15 (Python 3.14.5 available)
   - ✅ Rich ecosystem for LLM integration
   - ✅ Ollama Python SDK available
   - ✅ Easy to test and maintain
   - ✅ Cross-platform
   - ⚠️ Performance may be slower than compiled languages

2. **Go** (with bubbletea/bubbles)
   - ✅ Excellent TUI framework (bubbletea)
   - ✅ Native compilation, fast startup
   - ✅ Good Ollama Go SDK
   - ✅ Single binary deployment
   - ✅ Runs on macOS 10.15
   - ⚠️ More complex to develop

3. **Rust** (with ratatui)
   - ✅ Best performance
   - ✅ Excellent TUI framework (ratatui)
   - ✅ Ollama Rust SDK available
   - ✅ Single binary deployment
   - ✅ Runs on macOS 10.15 (rustc 1.91.1 available)
   - ⚠️ Steepest learning curve, longer development time

4. **Node.js** (with blessed/ink)
   - ✅ Large ecosystem
   - ✅ Good for those familiar with JS/TS
   - ✅ Ollama JS SDK available
   - ⚠️ Heavier runtime, slower startup
   - ⚠️ TUI frameworks less mature

### **Recommendation: Python with Textual**

**Rationale**:
- Fastest development velocity for feature-rich TUI
- Textual is a mature, feature-rich TUI framework
- Excellent async support for streaming LLM responses
- Rich widget library (markdown, syntax highlighting, data tables)
- Easy integration with Ollama Python SDK
- Native async/await for concurrent operations
- Great testing support with pytest
- Can package as standalone executable with PyInstaller if needed
- Works perfectly on macOS 10.15 with Python 3.14.5

## Ollama Integration Architecture

### Local Models (via local Ollama daemon)
```
User → TUI → localhost:11434/api/* → Local Ollama → Model
```

### Cloud Models (via local Ollama proxy)
```
User → TUI → localhost:11434/api/* → Local Ollama → Ollama Cloud → Model
```
- Uses `model:cloud` naming convention
- No API key needed (handled by local daemon after `ollama signin`)

### Cloud Models (direct API)
```
User → TUI → https://ollama.com/api/* + Authorization: Bearer <key> → Ollama Cloud → Model
```
- Requires `OLLAMA_API_KEY` environment variable
- Uses model names without `:cloud` suffix (e.g., `gpt-oss:120b`)

## Implementation Constraints for macOS 10.15

### Compatible:
- Python 3.14.5 ✅
- Node.js 22+ ✅
- Go 1.22+ ✅
- Rust 1.91+ ✅
- Ollama 0.20+ ✅
- Local models ✅
- Cloud models via local proxy ✅
- Cloud models via direct API with API key ✅

### Incompatible/Limited:
- Claude Code binary ❌ (requires macOS 13+)
- Some newer ICU-dependent libraries ❌
- Metal/GPU acceleration limited ❌

## Recommended Architecture

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

## Key Features to Implement (Priority Order)

### Phase 1: Core TUI & Ollama Integration
1. Textual-based TUI with chat interface
2. Local Ollama model listing and selection
3. Streaming chat with local models
4. Cloud model support via local proxy
5. Direct cloud API with API key authentication
6. Model switching in-session

### Phase 2: Agentic Capabilities
7. File operations (read, write, edit, list)
8. Bash command execution with approval
9. Git integration (diff, status, commit)
10. Sandbox modes (read-only, workspace-write, danger-full-access)
11. Approval policies (untrusted, on-request, never)

### Phase 3: Advanced Features
12. Session management (save, resume, fork, archive)
13. MCP server support
14. Plugin system
15. Web search tool
16. Image attachment support
17. Syntax highlighting & markdown rendering
18. Configuration (TOML-based like Codex)

### Phase 4: Polish & Distribution
19. Comprehensive test suite
20. Packaging for distribution
21. Documentation
22. Shell completions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Textual compatibility with macOS 10.15 | Low | High | Test early, fallback to simpler TUI |
| Ollama API changes | Medium | Medium | Abstract provider layer, version detection |
| Cloud API rate limits | Medium | Medium | Implement retry/backoff, local cache |
| Performance with large contexts | Medium | High | Streaming, context window management |
| Sandbox implementation complexity | High | High | Start simple, use existing libraries |

## Next Steps

1. Create implementation plan with milestones
2. Create GitHub issues for each milestone
3. Generate README.md and AGENTS.md
4. Begin Phase 1 implementation
