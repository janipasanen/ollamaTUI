"""Main entry point for OllamaTUI."""

import sys
import argparse
from pathlib import Path

from ollamatui.config import Config, load_config, save_config
from ollamatui.app import OllamaTUIApp


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="ollamatui",
        description="Agentic TUI for Ollama local and cloud models",
    )
    
    parser.add_argument(
        "-m", "--model",
        help="Model to use",
    )
    parser.add_argument(
        "--provider",
        choices=["local", "cloud"],
        help="Provider to use (local or cloud)",
    )
    parser.add_argument(
        "--sandbox",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Sandbox mode",
    )
    parser.add_argument(
        "--approval",
        choices=["untrusted", "on-request", "never"],
        help="Approval policy",
    )
    parser.add_argument(
        "--api-key",
        help="Ollama Cloud API key",
    )
    parser.add_argument(
        "-C", "--cd",
        help="Working directory",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        help="Additional writable directories",
    )
    parser.add_argument(
        "-p", "--profile",
        help="Configuration profile to use",
    )
    parser.add_argument(
        "--config",
        help="Path to config file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP server (stdio transport)",
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # exec command
    exec_parser = subparsers.add_parser("exec", help="Run non-interactively")
    exec_parser.add_argument("prompt", nargs="*", help="Prompt to execute")
    
    # review command
    subparsers.add_parser("review", help="Run code review")
    
    # sessions command
    subparsers.add_parser("sessions", help="List sessions")
    
    # resume command
    resume_parser = subparsers.add_parser("resume", help="Resume last session")
    resume_parser.add_argument("session", nargs="?", help="Session ID to resume")
    
    # config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show current config")
    config_subparsers.add_parser("edit", help="Edit config file")
    
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration
    cli_overrides = {}
    if args.model:
        cli_overrides["model"] = args.model
    if args.provider:
        cli_overrides["provider"] = args.provider
    if args.sandbox:
        cli_overrides["sandbox"] = args.sandbox
    if args.approval:
        cli_overrides["approval"] = args.approval
    if args.api_key:
        cli_overrides["api_key"] = args.api_key
    if args.cd:
        cli_overrides["working_dir"] = args.cd
    if args.add_dir:
        cli_overrides["add_dirs"] = args.add_dir
    
    config = load_config(profile=args.profile, cli_overrides=cli_overrides)
    
    # Handle commands
    if args.mcp:
        return run_mcp_server(config)
    elif args.command == "exec":
        return run_exec(config, args.prompt)
    elif args.command == "review":
        return run_review(config)
    elif args.command == "sessions":
        return run_sessions(config)
    elif args.command == "resume":
        return run_resume(config, args.session)
    elif args.command == "config":
        return run_config(config, args.config_command)
    else:
        # Run interactive TUI
        return run_tui(config)


def run_mcp_server(config: Config) -> int:
    """Run MCP server."""
    import asyncio
    from ollamatui.mcp.server import MCPServer
    
    async def run():
        server = MCPServer(
            working_dir=config.working_dir,
            allowed_dirs=config.add_dirs,
            approval_policy=config.approval,
        )
        await server.run_stdio()
    
    try:
        asyncio.run(run())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"MCP server error: {e}", file=sys.stderr)
        return 1


def run_tui(config: Config) -> int:
    """Run the interactive TUI."""
    try:
        app = OllamaTUIApp(config=config)
        app.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Ensure terminal is restored
        try:
            import os
            # Reset terminal modes
            os.system('stty sane 2</dev/null >/dev/null')
        except:
            pass


def run_exec(config: Config, prompt_parts: list) -> int:
    """Run non-interactive execution."""
    prompt = " ".join(prompt_parts)
    if not prompt:
        print("Error: No prompt provided", file=sys.stderr)
        return 1
    
    # TODO: Implement non-interactive execution
    print(f"Exec mode not yet implemented. Prompt: {prompt}")
    return 0


def run_review(config: Config) -> int:
    """Run code review."""
    print("Review mode not yet implemented")
    return 0


def run_sessions(config: Config) -> int:
    """List sessions."""
    print("Sessions not yet implemented")
    return 0


def run_resume(config: Config, session_id: str = None) -> int:
    """Resume a session."""
    print("Resume not yet implemented")
    return 0


def run_config(config: Config, command: str = None) -> int:
    """Manage configuration."""
    if command == "show":
        import tomli_w
        print(tomli_w.dumps(config.model_dump()))
    elif command == "edit":
        config_path = Path.home() / ".ollama" / "config.toml"
        import subprocess
        subprocess.run(["${EDITOR:-vi}", str(config_path)])
    else:
        print("Config commands: show, edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
