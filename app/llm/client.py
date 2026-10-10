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
        self._client: Optional[OpenAI] = None

    @property
    def deployment_name(self) -> str:
        from app.config import get_secret
        return get_secret("AZURE_OPENAI_DEPLOYMENT_NAME", "Neo-Hackathon")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            from app.config import get_secret
            endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
            api_key = get_secret("AZURE_OPENAI_API_KEY")
            if not api_key or not endpoint:
                raise ValueError(
                    f"Missing Azure OpenAI credentials (endpoint={'configured' if endpoint else 'MISSING'}, api_key={'configured' if api_key else 'MISSING'}). "
                    "Please configure AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in your Streamlit Cloud Secrets."
                )
            self._client = OpenAI(
                base_url=endpoint,
                api_key=api_key
            )
        return self._client



    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        reraise=True
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2500
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

            # If model returned reasoning but empty content due to token boundary, use reasoning as answer
            if not content.strip() and reasoning and reasoning.strip():
                content = reasoning.strip()

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
