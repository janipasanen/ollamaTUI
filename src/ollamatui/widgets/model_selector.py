"""Model selector widget."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Button, Label, ListView, ListItem
from textual.message import Message
from textual.reactive import reactive

from ollamatui.providers.base import ModelInfo


class ModelSelector(Container):
    """Widget for selecting models."""
    
    class ModelSelected(Message):
        """Model selected event."""
        def __init__(self, model: ModelInfo) -> None:
            self.model = model
            super().__init__()
    
    class ProviderChanged(Message):
        """Provider changed event."""
        def __init__(self, provider: str) -> None:
            self.provider = provider
            super().__init__()
    
    # Reactive state
    models: reactive[list] = reactive([], init=False)
    selected_provider: reactive[str] = reactive("local", init=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.models = []
        self._model_list: ListView = None
    
    def compose(self) -> ComposeResult:
        yield Label("Models", classes="selector-title")
        
        with Container(classes="provider-tabs"):
            yield Button("Local", id="tab-local", variant="primary")
            yield Button("Cloud", id="tab-cloud")
        
        yield ListView(id="model-list")
    
    def on_mount(self) -> None:
        self._model_list = self.query_one("#model-list", ListView)
        self._update_model_list()
    
    def set_models(self, models: list[ModelInfo], provider: str) -> None:
        """Set the available models."""
        self.models = models
        self.selected_provider = provider
        self._update_model_list()
        
        # Update tab styles
        local_tab = self.query_one("#tab-local", Button)
        cloud_tab = self.query_one("#tab-cloud", Button)
        if provider == "local":
            local_tab.variant = "primary"
            cloud_tab.variant = "default"
        else:
            local_tab.variant = "default"
            cloud_tab.variant = "primary"
    
    def _update_model_list(self) -> None:
        """Update the model list view."""
        self._model_list.clear()
        
        # Filter models by provider
        filtered = [
            m for m in self.models
            if (self.selected_provider == "cloud" and m.is_cloud) or
               (self.selected_provider == "local" and not m.is_cloud)
        ]
        
        for model in filtered:
            # Create display text
            size_str = ""
            if model.size > 0:
                if model.size > 1024**3:
                    size_str = f" ({model.size / 1024**3:.1f}GB)"
                elif model.size > 1024**2:
                    size_str = f" ({model.size / 1024**2:.1f}MB)"
                else:
                    size_str = f" ({model.size / 1024:.1f}KB)"
            
            cloud_indicator = " ☁️" if model.is_cloud else ""
            display = f"{model.name}{size_str}{cloud_indicator}"
            
            item = ListItem(Label(display), id=f"model-{model.name}")
            self._model_list.append(item)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tab button presses."""
        if event.button.id == "tab-local":
            self.selected_provider = "local"
            self.post_message(self.ProviderChanged("local"))
        elif event.button.id == "tab-cloud":
            self.selected_provider = "cloud"
            self.post_message(self.ProviderChanged("cloud"))
        self._update_model_list()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle model selection."""
        if event.item.id and event.item.id.startswith("model-"):
            model_name = event.item.id[6:]  # Remove "model-" prefix
            model = next((m for m in self.models if m.name == model_name), None)
            if model:
                self.post_message(self.ModelSelected(model))
