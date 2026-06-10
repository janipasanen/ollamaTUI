"""Local Ollama provider (connects to local daemon)."""

from typing import AsyncIterator, List, Optional, Dict, Any
import json

from ollamatui.providers.base import BaseOllamaProvider, ModelInfo, ChatMessage, ChatResponse


class LocalOllamaProvider(BaseOllamaProvider):
    """Provider for local Ollama daemon."""
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    async def list_models(self) -> List[ModelInfo]:
        """List locally available models."""
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        
        models = []
        for m in data.get("models", []):
            # Check if it's a cloud model (has :cloud suffix or no size)
            is_cloud = m.get("name", "").endswith(":cloud") or m.get("size", 0) == 0
            models.append(ModelInfo(
                name=m["name"],
                size=m.get("size", 0),
                digest=m.get("digest", ""),
                modified_at=m.get("modified_at", ""),
                details=m.get("details"),
                is_cloud=is_cloud,
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
        """Chat with a local model."""
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
        
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            
            if stream:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield self._parse_response(data)
            else:
                data = response.json()
                yield self._parse_response(data)
    
    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        """Parse Ollama API response."""
        msg_data = data.get("message", {})
        
        # Handle thinking field if present
        thinking = data.get("thinking") or msg_data.get("thinking")
        
        return ChatResponse(
            model=data.get("model", ""),
            message=ChatMessage(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content", ""),
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
