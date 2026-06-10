"""Web search tool."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

import httpx

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter


class WebSearchTool(BaseTool):
    """Tool for web search using DuckDuckGo HTML scraping."""
    
    name = "web_search"
    description = "Search the web for information"
    parameters = [
        ToolParameter(name="query", type="string", description="Search query", required=True),
        ToolParameter(name="max_results", type="integer", description="Maximum results to return", default=5),
        ToolParameter(name="region", type="string", description="Search region (e.g., us-en, uk-en)", default="us-en"),
    ]
    
    def __init__(
        self,
        working_dir: str = ".",
        allowed_dirs: List[str] = None,
        timeout: float = 10.0,
    ):
        super().__init__(working_dir, allowed_dirs)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute web search."""
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 5)
        region = kwargs.get("region", "us-en")
        
        if not query:
            return ToolResult(success=False, error="Missing required parameter: query")
        
        try:
            results = await self._search_duckduckgo(query, max_results, region)
            return ToolResult(
                success=True,
                output=results,
                metadata={"query": query, "count": len(results)}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {str(e)}")
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo HTML."""
        client = await self._get_client()
        
        url = "https://html.duckduckgo.com/html/"
        params = {
            "q": query,
            "kl": region,
        }
        
        response = await client.post(url, data=params)
        response.raise_for_status()
        
        # Parse HTML results
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for result in soup.select(".result")[:max_results]:
            title_elem = result.select_one(".result__title")
            snippet_elem = result.select_one(".result__snippet")
            url_elem = result.select_one(".result__url")
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")
                
                snippet = ""
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                
                display_url = ""
                if url_elem:
                    display_url = url_elem.get_text(strip=True)
                
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "display_url": display_url,
                })
        
        return results
    
    async def search_brave(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Brave Search API (requires API key)."""
        # This would require a Brave Search API key
        # Placeholder for future implementation
        return []
    
    async def search_google(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API (requires API key)."""
        # This would require Google API key and CX
        # Placeholder for future implementation
        return []
