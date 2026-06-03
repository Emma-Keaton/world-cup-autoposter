"""
NVIDIA NIM API client for LLM inference and embeddings.
"""
import httpx
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.config import settings


class NVIDIAClient:
    """
    Client for NVIDIA NIM API.
    
    Provides access to Llama-3-70B-Instruct for content generation
    and embedding models for vector similarity.
    """
    
    def __init__(self):
        """Initialize the NVIDIA client."""
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = settings.NVIDIA_API_BASE_URL
        self.chat_model = "meta/llama-3.1-70b-instruct"
        self.embedding_model = "nvidia/nv-embedqa-e5-v5"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a chat completion using NVIDIA NIM API.
        
        Args:
            messages: List of message dicts with role and content
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Generated text content
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Build messages array
        api_messages = []
        
        if system_prompt:
            api_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        api_messages.extend(messages)
        
        payload = {
            "model": self.chat_model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.7,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                logger.debug(f"Generated {len(content)} characters")
                return content
                
        except httpx.HTTPError as e:
            logger.error(f"NVIDIA API HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}")
            raise
    
    async def generate_with_json_schema(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output with schema validation.
        
        Args:
            prompt: User prompt
            json_schema: JSON schema for output validation
            system_prompt: Optional system prompt
            
        Returns:
            Parsed JSON object
        """
        messages = [{
            "role": "user",
            "content": f"{prompt}\n\nReturn ONLY valid JSON matching this schema:\n{json.dumps(json_schema)}"
        }]
        
        response_text = await self.chat_completion(
            messages=messages,
            temperature=0.3,  # Lower temperature for structured output
            system_prompt=system_prompt or "You are a JSON generator. Return ONLY valid JSON with no markdown, no explanations, no additional text.",
        )
        
        # Parse JSON from response
        return self._parse_json_response(response_text)
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using NVIDIA embedding model.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.embedding_model,
            "input": texts,
            "input_type": "passage",
            "encoding_format": "float",
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                
                return embeddings
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str
    ) -> str:
        """
        Analyze an image using NVIDIA's multimodal model.
        
        Args:
            image_url: URL of the image to analyze
            prompt: Question/prompt about the image
            
        Returns:
            Analysis text
        """
        # Use NeVA model for multimodal analysis
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "adept/neva-22b",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt}
                ]
            }],
            "max_tokens": 1024,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return ""
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response."""
        content = content.strip()
        
        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Invalid JSON response: {content[:200]}")