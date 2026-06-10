"""File tree widget for workspace browsing."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label, ListView, ListItem, Tree
from textual.message import Message
from pathlib import Path
import os


class FileTreeWidget(Container):
    """Widget for browsing the file system."""
    
    class FileSelected(Message):
        """File selected event."""
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()
    
    def __init__(self, root_path: Path = None, **kwargs):
        super().__init__(**kwargs)
        self.root_path = root_path or Path.cwd()
        self._tree: Tree = None
    
    def compose(self) -> ComposeResult:
        yield Label("Files", classes="selector-title")
        yield Tree("Root", id="file-tree")
    
    def on_mount(self) -> None:
        self._tree = self.query_one("#file-tree", Tree)
        self._tree.root.expand()
        self._load_directory(self._tree.root, self.root_path)
    
    def _load_directory(self, node, path: Path) -> None:
        """Load directory contents into tree."""
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item in items:
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    child = node.add(item.name, expand=False, data=item)
                    # Add placeholder to show expand arrow
                    child.add_leaf("...", data=None)
                else:
                    node.add_leaf(item.name, data=item)
        except PermissionError:
            node.add_leaf("[Permission denied]", data=None)
    
    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion."""
        node = event.node
        if node.data and node.data.is_dir():
            # Remove placeholder
            if node.children and node.children[0].data is None:
                node.remove_child(node.children[0])
            self._load_directory(node, node.data)
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle file selection."""
        if event.node.data and event.node.data.is_file():
            self.post_message(self.FileSelected(event.node.data))
    
    def set_root(self, path: Path) -> None:
        """Change the root directory."""
        self.root_path = path
        self._tree.clear()
        self._tree.root.expand()
        self._load_directory(self._tree.root, path)
