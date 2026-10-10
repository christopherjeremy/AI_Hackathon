"""
Azure OpenAI Client wrapper with rate-limit resilience, exponential backoff,
and fallback handling.
"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.model_name = settings.AZURE_OPENAI_MODEL_NAME
        
        self.client = OpenAI(
            base_url=self.endpoint,
            api_key=self.api_key
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        reraise=True
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Calls Azure OpenAI chat completion with exponential backoff retry.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning = getattr(choice.message, "reasoning_content", None)
            return {
                "content": content,
                "reasoning": reasoning,
                "finish_reason": choice.finish_reason
            }
        except RateLimitError as e:
            logger.warning(f"Azure OpenAI Rate Limit encountered: {e}. Retrying with backoff...")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise

llm_client = LLMClient()
