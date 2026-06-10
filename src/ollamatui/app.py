"""Main Textual application for OllamaTUI."""

import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual.binding import Binding
from textual.screen import Screen
from textual import events

from ollamatui.config import Config, load_config
from ollamatui.providers.factory import create_provider
from ollamatui.providers.base import ModelInfo, ChatMessage
from ollamatui.widgets.chat import ChatWidget
from ollamatui.widgets.model_selector import ModelSelector
from ollamatui.widgets.file_tree import FileTreeWidget
from ollamatui.tools import FileTool, BashTool, GitTool, WebSearchTool


class OllamaTUIApp(App):
    """Main OllamaTUI application."""
    
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #sidebar {
        width: 30;
        min-width: 25;
        max-width: 50;
        border-right: solid $primary;
        padding: 1;
    }
    
    #main-content {
        width: 1fr;
        layout: vertical;
    }
    
    #chat-area {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #input-area {
        height: auto;
        min-height: 5;
        margin: 1;
    }
    
    .selector-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .provider-tabs {
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .provider-tabs Button {
        margin-right: 1;
    }
    
    #model-list {
        height: 1fr;
    }
    
    #file-tree {
        height: 1fr;
    }
    
    .message-user {
        background: $surface;
        margin: 1;
        padding: 1;
    }
    
    .message-assistant {
        background: $surface;
        margin: 1;
        padding: 1;
    }
    
    #chat-messages {
        padding: 1;
    }
    
    #chat-input-container {
        layout: horizontal;
        height: auto;
    }
    
    #chat-input {
        width: 1fr;
        margin-right: 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new_chat", "New Chat"),
        Binding("ctrl+m", "toggle_models", "Models"),
        Binding("ctrl+f", "toggle_files", "Files"),
        Binding("ctrl+s", "save_session", "Save"),
        Binding("ctrl+r", "resume_session", "Resume"),
    ]
    
    def __init__(self, config: Config = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or load_config()
        self.provider = None
        self.current_model: ModelInfo = None
        self.chat_widget: ChatWidget = None
        self.model_selector: ModelSelector = None
        self.file_tree: FileTreeWidget = None
        self._sidebar_visible = True
        
        # Initialize tools
        self._init_tools()
    
    def _init_tools(self):
        """Initialize available tools."""
        working_dir = self.config.working_dir
        allowed_dirs = self.config.add_dirs
        
        self.tools = {
            "bash": BashTool(working_dir=working_dir, allowed_dirs=allowed_dirs),
            "file": FileTool(working_dir=working_dir, allowed_dirs=allowed_dirs),
            "git": GitTool(working_dir=working_dir, allowed_dirs=allowed_dirs),
            "web_search": WebSearchTool(),
        }
    
    def _get_tool_schemas(self):
        """Get tool schemas for the model."""
        return [tool.get_schema() for tool in self.tools.values()]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal():
            # Sidebar
            with Container(id="sidebar"):
                self.model_selector = ModelSelector(id="model-selector")
                yield self.model_selector
                
                self.file_tree = FileTreeWidget(
                    root_path=Path(self.config.working_dir),
                    id="file-tree"
                )
                yield self.file_tree
            
            # Main content
            with Container(id="main-content"):
                with Container(id="chat-area"):
                    self.chat_widget = ChatWidget(id="chat-widget")
                    yield self.chat_widget
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize the app."""
        # Create provider
        self.provider = create_provider(self.config)
        
        # Load models
        await self._load_models()
        
        # Set up event handlers
        self.chat_widget.focus()
    
    async def _load_models(self) -> None:
        """Load models from provider."""
        try:
            models = await self.provider.list_models()
            self.model_selector.set_models(models, self.config.provider)
            
            # Auto-select model from config if specified
            if self.config.model and not self.current_model:
                # For cloud provider, strip -cloud suffix if present
                model_name = self.config.model
                if self.config.provider == "cloud" and model_name.endswith("-cloud"):
                    model_name = model_name[:-6]  # Remove -cloud suffix
                
                # Find matching model
                for model in models:
                    if model.name == model_name or model.name == self.config.model:
                        self.current_model = model
                        self.notify(f"Using model: {model.name}")
                        break
        except Exception as e:
            self.notify(f"Failed to load models: {e}", severity="error")
    
    async def on_model_selector_model_selected(self, event: ModelSelector.ModelSelected) -> None:
        """Handle model selection."""
        self.current_model = event.model
        self.config.model = event.model.name
        self.notify(f"Selected model: {event.model.name}")
    
    async def on_model_selector_provider_changed(self, event: ModelSelector.ProviderChanged) -> None:
        """Handle provider change."""
        self.config.provider = event.provider
        await self._load_models()
    
    async def on_chat_widget_message_submitted(self, event: ChatWidget.MessageSubmitted) -> None:
        """Handle chat message submission."""
        if not self.current_model:
            self.notify("Please select a model first", severity="warning")
            return
        
        # Add user message
        user_msg = ChatMessage(role="user", content=event.content)
        self.chat_widget.add_message(user_msg)
        
        # Start streaming response
        self.chat_widget.set_streaming(True)
        
        # Use call_from_thread to run async operation
        import asyncio
        asyncio.create_task(self._stream_chat_response())
    
    async def _stream_chat_response(self) -> None:
        """Stream chat response."""
        response_text = ""
        try:
            # Build message history
            messages = [
                ChatMessage(role=m.role, content=m.content)
                for m in self.chat_widget.messages
            ]
            
            # Get model name
            model_name = self.current_model.name
            
            # Get tool schemas
            tools = self._get_tool_schemas()
            
            # Stream response
            async for chunk in self.provider.chat(
                model_name,
                messages,
                stream=True,
                options={
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                },
                tools=tools,
            ):
                # Check if we should stop
                if not self.chat_widget.is_streaming:
                    break
                
                try:
                    # Handle tool calls
                    if chunk.tool_calls:
                        # Add assistant message with tool calls
                        self.chat_widget.append_to_last_message("\n🔧 Using tools...", "assistant")
                        
                        # Process tool calls
                        for tool_call in chunk.tool_calls:
                            tool_name = tool_call.get("function", {}).get("name", "")
                            tool_args = tool_call.get("function", {}).get("arguments", {})
                            
                            if tool_name in self.tools:
                                # Show what we're doing
                                self.chat_widget.append_to_last_message(f"\n⏳ {tool_name}(...)", "assistant")
                                
                                # Execute tool
                                try:
                                    result = await self.tools[tool_name].execute(**tool_args)
                                    if result.success:
                                        result_str = str(result.output)[:500]  # Limit output length
                                        self.chat_widget.append_to_last_message(f"\n✅ {result_str}", "assistant")
                                    else:
                                        self.chat_widget.append_to_last_message(f"\n❌ Error: {result.error}", "assistant")
                                except Exception as e:
                                    self.chat_widget.append_to_last_message(f"\n❌ Tool error: {e}", "assistant")
                        continue
                    
                    if chunk.thinking:
                        self.chat_widget.append_to_last_message(f"\n\n💭 *Thinking...*", "assistant")
                    
                    if chunk.message and chunk.message.content:
                        response_text += chunk.message.content
                        self.chat_widget.append_to_last_message(chunk.message.content, "assistant")
                    
                    if chunk.done:
                        break
                except Exception as e:
                    print(f"Error processing chunk: {e}")
                    continue
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Chat error: {error_detail}")
            self.notify(f"Error: {e}", severity="error", timeout=10)
            if not response_text:
                self.chat_widget.append_to_last_message(f"\n\n❌ Error: {e}", "assistant")
        
        finally:
            # Always reset streaming state
            self.chat_widget.set_streaming(False)
    
    async def on_chat_widget_stop_requested(self, event: ChatWidget.StopRequested) -> None:
        """Handle stop request."""
        # Close provider connection to stop streaming
        await self.provider.close()
        self.provider = create_provider(self.config)
        self.chat_widget.set_streaming(False)
        self.notify("Generation stopped")
    
    def action_toggle_models(self) -> None:
        """Toggle model selector visibility."""
        self.model_selector.display = not self.model_selector.display
    
    def action_toggle_files(self) -> None:
        """Toggle file tree visibility."""
        self.file_tree.display = not self.file_tree.display
    
    def action_new_chat(self) -> None:
        """Start a new chat."""
        self.chat_widget.clear()
        self.notify("New chat started")
    
    async def action_save_session(self) -> None:
        """Save current session."""
        # TODO: Implement session saving
        self.notify("Session save not yet implemented")
    
    async def action_resume_session(self) -> None:
        """Resume a session."""
        # TODO: Implement session resume
        self.notify("Session resume not yet implemented")
    
    async def on_unmount(self) -> None:
        """Cleanup on exit."""
        if self.provider:
            await self.provider.close()


# Import Path for file_tree
from pathlib import Path
