"""
Hugging Face Inference API Embeddings Client.
Default Model: BAAI/bge-base-en-v1.5 (Top MTEB Retrieval Model on Hugging Face).
Supports serverless inference via HTTPS with automatic fallback.
"""

import logging
import requests
import numpy as np
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class HuggingFaceEmbedder:
    def __init__(
        self,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.model_id = model_id or settings.HUGGINGFACE_EMBEDDING_MODEL
        self.api_key = api_key or settings.HUGGINGFACE_API_KEY
        
        # Hugging Face Serverless Endpoints
        self.router_url = f"https://router.huggingface.co/hf-inference/models/{self.model_id}"
        self.inference_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_id}"

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty Hugging Face API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def get_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Fetches dense vector embeddings for a list of texts via Hugging Face API.
        Returns a float32 numpy array of shape (len(texts), embedding_dim), or None on failure.
        """
        if not self.is_configured or not texts:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json"
        }

        # Try endpoints in order
        for url in [self.router_url, self.inference_url]:
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json={
                        "inputs": texts,
                        "options": {"wait_for_model": True, "use_cache": True}
                    },
                    timeout=20
                )
                if response.status_code == 200:
                    data = response.json()
                    arr = np.array(data, dtype=np.float32)
                    
                    # Expected 2D: (num_texts, dim)
                    if arr.ndim == 2 and arr.shape[0] == len(texts):
                        return self._l2_normalize(arr)
                    # 3D case: (num_texts, seq_len, dim) -> mean pooling
                    elif arr.ndim == 3 and arr.shape[0] == len(texts):
                        pooled = arr.mean(axis=1)
                        return self._l2_normalize(pooled)
                    elif arr.ndim == 1 and len(texts) == 1:
                        return self._l2_normalize(arr.reshape(1, -1))
                else:
                    logger.warning(
                        f"Hugging Face embedding API ({url}) returned {response.status_code}: {response.text[:200]}"
                    )
            except Exception as e:
                logger.warning(f"Failed to reach Hugging Face endpoint ({url}): {e}")

        return None

    def get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Fetches normalized embedding vector for a single search query."""
        if not query.strip():
            return None
        res = self.get_embeddings([query.strip()])
        if res is not None and len(res) > 0:
            return res[0]
        return None

    @staticmethod
    def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
        """L2 normalizes embedding vectors along the last axis."""
        norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms


# Singleton instance
hf_embedder = HuggingFaceEmbedder()
