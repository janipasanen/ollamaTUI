"""Cloud Ollama provider (connects to ollama.com API)."""

from typing import AsyncIterator, List, Optional, Dict, Any
import json

from ollamatui.providers.base import BaseOllamaProvider, ModelInfo, ChatMessage, ChatResponse


class CloudOllamaProvider(BaseOllamaProvider):
    """Provider for Ollama Cloud API."""
    
    def __init__(self, host: str = "https://ollama.com", api_key: Optional[str] = None, timeout: float = 120.0):
        if not api_key:
            raise ValueError("API key is required for CloudOllamaProvider")
        super().__init__(host, api_key, timeout)
    
    @property
    def provider_name(self) -> str:
        return "cloud"
    
    async def list_models(self) -> List[ModelInfo]:
        """List cloud models available via API."""
        client = await self._get_client()
        
        # Try the cloud models endpoint
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
        except Exception:
            # Fallback: try search endpoint
            response = await client.get("/api/search?c=cloud")
            response.raise_for_status()
            data = response.json()
        
        models = []
        for m in data.get("models", []):
            # Cloud models don't have size in the same way
            models.append(ModelInfo(
                name=m.get("name", m.get("model", "")),
                size=m.get("size", 0),
                digest=m.get("digest", ""),
                modified_at=m.get("modified_at", ""),
                details=m.get("details"),
                is_cloud=True,
            ))
        return models
    
    async def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
        think: bool = False,
    ) -> AsyncIterator[ChatResponse]:
        """Chat with a cloud model."""
        client = await self._get_client()
        
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_msg = {"role": msg.role, "content": msg.content}
            if msg.images:
                ollama_msg["images"] = msg.images
            ollama_messages.append(ollama_msg)
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": stream,
        }
        
        if options:
            payload["options"] = options
        
        if think:
            payload["think"] = True
        
        try:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code >= 400:
                    error_body = await response.aread()
                    error_msg = error_body.decode('utf-8', errors='replace')
                    raise Exception(f"API error {response.status_code}: {error_msg}")
                
                response.raise_for_status()
                
                if stream:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                yield self._parse_response(data)
                            except json.JSONDecodeError as e:
                                # Skip invalid JSON lines
                                continue
                else:
                    data = response.json()
                    yield self._parse_response(data)
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Chat request failed: {e}")
    
    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        """Parse Ollama Cloud API response."""
        msg_data = data.get("message", {}) or {}
        
        # Handle thinking field if present
        thinking = data.get("thinking") or msg_data.get("thinking")
        
        # Handle content safely - might be None
        content = msg_data.get("content", "") or ""
        
        return ChatResponse(
            model=data.get("model", ""),
            message=ChatMessage(
                role=msg_data.get("role", "assistant"),
                content=content,
            ),
            done=data.get("done", False),
            done_reason=data.get("done_reason"),
            total_duration=data.get("total_duration"),
            load_duration=data.get("load_duration"),
            prompt_eval_count=data.get("prompt_eval_count"),
            prompt_eval_duration=data.get("prompt_eval_duration"),
            eval_count=data.get("eval_count"),
            eval_duration=data.get("eval_duration"),
            thinking=thinking,
        )
