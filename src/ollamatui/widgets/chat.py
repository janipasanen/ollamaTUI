"""Chat interface widgets."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Static, Input, Button, Markdown
from textual.message import Message
from textual.reactive import reactive
from textual import events
from rich.syntax import Syntax
from rich.text import Text
from datetime import datetime

from ollamatui.providers.base import ChatMessage


class ChatMessageWidget(Static):
    """A single chat message widget."""
    
    def __init__(self, message: ChatMessage, timestamp: datetime = None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self._rendered = False
    
    def compose(self) -> ComposeResult:
        # Role indicator
        role_style = "bold cyan" if self.message.role == "user" else "bold green"
        role_text = "You" if self.message.role == "user" else "Assistant"
        
        # Timestamp
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        # Content with markdown rendering
        yield Markdown(
            self.message.content,
            code_theme="monokai",
        )
    
    def on_mount(self) -> None:
        self.add_class(f"message-{self.message.role}")


class ChatWidget(Container):
    """Main chat interface widget."""
    
    class MessageSubmitted(Message):
        """Message submitted event."""
        def __init__(self, content: str) -> None:
            self.content = content
            super().__init__()
    
    # Reactive state
    messages: reactive[list] = reactive([], init=False)
    is_streaming: reactive[bool] = reactive(False, init=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []
        self._message_container: VerticalScroll = None
        self._input: Input = None
    
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-messages"):
            # Messages will be added here dynamically
            pass
        
        with Container(id="chat-input-container"):
            yield Input(
                placeholder="Type a message... (Enter to send, Shift+Enter for newline)",
                id="chat-input",
            )
            yield Button("Send", id="send-button", variant="primary")
            yield Button("Stop", id="stop-button", variant="error", disabled=True)
    
    def on_mount(self) -> None:
        self._message_container = self.query_one("#chat-messages", VerticalScroll)
        self._input = self.query_one("#chat-input", Input)
        self._input.focus()
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the chat."""
        widget = ChatMessageWidget(message)
        self._message_container.mount(widget)
        self.messages.append(message)
        self._scroll_to_bottom()
    
    def update_last_message(self, content: str, role: str = "assistant") -> None:
        """Update the last message (for streaming)."""
        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content = content
            # Re-render the last widget
            widgets = list(self._message_container.children)
            if widgets:
                last_widget = widgets[-1]
                if isinstance(last_widget, ChatMessageWidget):
                    last_widget.message.content = content
                    last_widget.refresh()
        else:
            # Add new message
            self.add_message(ChatMessage(role=role, content=content))
    
    def append_to_last_message(self, delta: str, role: str = "assistant") -> None:
        """Append to the last message (for streaming)."""
        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content += delta
            widgets = list(self._message_container.children)
            if widgets:
                last_widget = widgets[-1]
                if isinstance(last_widget, ChatMessageWidget):
                    last_widget.message.content = self.messages[-1].content
                    last_widget.refresh()
        else:
            self.add_message(ChatMessage(role=role, content=delta))
    
    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat."""
        self._message_container.scroll_end(animate=False)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        content = event.value.strip()
        if content:
            self.post_message(self.MessageSubmitted(content))
            event.input.value = ""
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "send-button":
            content = self._input.value.strip()
            if content:
                self.post_message(self.MessageSubmitted(content))
                self._input.value = ""
        elif event.button.id == "stop-button":
            # Emit stop event
            self.post_message(self.StopRequested())
    
    class StopRequested(Message):
        """Stop generation requested."""
        pass
    
    def set_streaming(self, streaming: bool) -> None:
        """Set streaming state."""
        self.is_streaming = streaming
        self._input.disabled = streaming
        self.query_one("#send-button", Button).disabled = streaming
        self.query_one("#stop-button", Button).disabled = not streaming
    
    def clear(self) -> None:
        """Clear all messages."""
        self._message_container.remove_children()
        self.messages = []
