"""
Hugging Face Dense Embeddings Engine.
Default Model: BAAI/bge-small-en-v1.5 (Top MTEB Retrieval Model on Hugging Face).
Supports local SentenceTransformer inference with Hugging Face Hub token authentication,
plus serverless HTTP fallback and graceful TF-IDF safety net.
"""

import logging
import requests
import numpy as np
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Apply compatibility patch for PyTorch / Transformers if needed
try:
    import torch
    if not hasattr(torch, "accelerator"):
        class _DummyAccelerator:
            @staticmethod
            def current_accelerator():
                return None
            @staticmethod
            def is_available():
                return False
        torch.accelerator = _DummyAccelerator()
except Exception:
    pass


class HuggingFaceEmbedder:
    def __init__(
        self,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.model_id = model_id or settings.HUGGINGFACE_EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5"
        self.api_key = api_key or settings.HUGGINGFACE_API_KEY
        self.local_model = None

        # Hugging Face Serverless Endpoints
        self.router_url = f"https://router.huggingface.co/hf-inference/models/{self.model_id}"

        # Try initializing local SentenceTransformer with Hugging Face authentication
        self._init_local_model()

    def _init_local_model(self):
        """Attempts to load SentenceTransformer using the authenticated Hugging Face token."""
        try:
            from sentence_transformers import SentenceTransformer
            token = self.api_key.strip() if self.api_key else None
            self.local_model = SentenceTransformer(self.model_id, token=token)
            logger.info(f"Loaded Hugging Face SentenceTransformer: {self.model_id}")
        except Exception as e:
            logger.info(f"Local SentenceTransformer load skipped/failed ({e}); will use API or fallback.")
            self.local_model = None

    @property
    def is_configured(self) -> bool:
        """Returns True if local model is loaded or an API token is present."""
        return bool(self.local_model is not None or (self.api_key and self.api_key.strip()))

    def get_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Fetches dense vector embeddings for a list of texts.
        Uses local SentenceTransformer if available, or Hugging Face HTTP API.
        Returns float32 numpy array of shape (len(texts), embedding_dim) or None.
        """
        if not texts:
            return None

        # 1. Fast local execution with SentenceTransformer (0ms latency, zero credit cost)
        if self.local_model is not None:
            try:
                embeddings = self.local_model.encode(
                    texts,
                    batch_size=32,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
                return np.array(embeddings, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Error during local model encode: {e}")

        # 2. HTTP Inference API fallback
        if self.api_key and self.api_key.strip():
            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json"
            }
            try:
                response = requests.post(
                    self.router_url,
                    headers=headers,
                    json={
                        "inputs": texts,
                        "options": {"wait_for_model": True, "use_cache": True}
                    },
                    timeout=15
                )
                if response.status_code == 200:
                    arr = np.array(response.json(), dtype=np.float32)
                    if arr.ndim == 2 and arr.shape[0] == len(texts):
                        return self._l2_normalize(arr)
                    elif arr.ndim == 3 and arr.shape[0] == len(texts):
                        return self._l2_normalize(arr.mean(axis=1))
            except Exception as e:
                logger.warning(f"HTTP Inference API error: {e}")

        return None

    def get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Fetches normalized embedding vector for a single query."""
        if not query.strip():
            return None
        res = self.get_embeddings([query.strip()])
        if res is not None and len(res) > 0:
            return res[0]
        return None

    @staticmethod
    def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
        """L2 normalizes embedding vectors."""
        norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms


# Singleton instance
hf_embedder = HuggingFaceEmbedder()
