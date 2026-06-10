"""Base provider interface for Ollama API."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional, List, Dict, Any
import httpx


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    size: int
    digest: str
    modified_at: str
    details: Optional[Dict[str, Any]] = None
    is_cloud: bool = False


@dataclass
class ChatMessage:
    """A chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    images: Optional[List[str]] = None  # base64 encoded images


@dataclass
class ChatResponse:
    """A chat response chunk."""
    model: str
    message: ChatMessage
    done: bool
    done_reason: Optional[str] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None
    thinking: Optional[str] = None


class BaseOllamaProvider(ABC):
    """Abstract base class for Ollama providers."""
    
    def __init__(self, host: str, api_key: Optional[str] = None, timeout: float = 60.0):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.host,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
        think: bool = False,
    ) -> AsyncIterator[ChatResponse]:
        """Chat with a model."""
        pass
    
    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[ChatResponse]:
        """Generate a completion (legacy API)."""
        messages = [ChatMessage(role="user", content=prompt)]
        async for chunk in self.chat(model, messages, stream, options):
            yield chunk
    
    async def pull_model(self, model: str) -> AsyncIterator[Dict[str, Any]]:
        """Pull a model."""
        client = await self._get_client()
        async with client.stream(
            "POST",
            "/api/pull",
            json={"model": model, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    yield json.loads(line)
    
    async def delete_model(self, model: str) -> bool:
        """Delete a model."""
        client = await self._get_client()
        response = await client.request(
            "DELETE",
            "/api/delete",
            json={"model": model},
        )
        return response.status_code == 200
    
    async def show_model(self, model: str) -> Dict[str, Any]:
        """Show model information."""
        client = await self._get_client()
        response = await client.post("/api/show", json={"model": model})
        response.raise_for_status()
        return response.json()
    
    async def check_connection(self) -> bool:
        """Check if the provider is accessible."""
        try:
            client = await self._get_client()
            response = await client.get("/api/version", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
