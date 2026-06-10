# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Tool support for agentic capabilities (BashTool, FileTool, GitTool, WebSearchTool)
- Tool call handling in chat interface
- Auto-approval policy for tools

### Fixed
- Chat streaming freezing TUI
- Model name handling for cloud models
- API key detection for Ollama Cloud
- Terminal restoration after crashes

## [0.1.0] - 2026-06-10

### Added
- Initial release
- Terminal User Interface built with Textual
- Support for local Ollama models
- Support for Ollama Cloud models with API key authentication
- Streaming chat responses
- Model selection with sidebar
- File browser widget
- Session management
- Configuration system with TOML support
- Multiple sandbox modes (read-only, workspace-write, danger-full-access)
- Approval policies (untrusted, on-request, never)
- Markdown and syntax highlighting support

### Security
- Path validation for file operations
- Command blocking for dangerous bash commands
- Sandbox restrictions for file writes

## [0.0.1] - 2026-06-01

### Added
- Project scaffolding
- Basic provider abstraction
- Local Ollama provider
- Cloud Ollama provider