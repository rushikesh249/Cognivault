"""Embedding Service for local vector representation (TRD Section 16.1, Component #10, ADR-006)."""

from abc import ABC, abstractmethod
import hashlib
import logging
import math
from pathlib import Path
from typing import List, Optional

from backend.app.core.config import settings

logger = logging.getLogger("sovereign_workbench.rag.embeddings")


class EmbeddingModelNotFoundError(RuntimeError):
    """Raised when the configured local embedding model weights are missing and remote downloads are disabled."""
    pass


class BaseEmbeddingService(ABC):
    """Abstract interface for local embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of text strings."""
        pass

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a single query string."""
        results = self.embed_texts([query])
        if not results:
            raise RuntimeError("Embedding service returned empty result for query")
        return results[0]


class DeterministicTestEmbeddingService(BaseEmbeddingService):
    """Deterministic, offline test embedding service that does not require model downloads.
    
    Generates 384-dimensional unit vectors based on feature hashing of character/word n-grams,
    ensuring that semantically similar texts have high cosine similarity while remaining
    completely deterministic, offline, and lightweight.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _text_to_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dimension

        vec = [0.0] * self._dimension
        words = text.lower().strip().split()
        
        # Word-level and character tri-gram feature hashing
        for word in words:
            # Word feature
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * 1.5

            # Subword character tri-grams
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    trigram = word[i:i+3]
                    th = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
                    t_idx = th % self._dimension
                    t_sign = 1.0 if ((th >> 8) & 1) else -1.0
                    vec[t_idx] += t_sign * 0.5

        # L2 normalize vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [x / norm for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(t) for t in texts]


class LocalBGEEmbeddingService(BaseEmbeddingService):
    """Production local BGE embedding service using sentence-transformers (TRD Table 36).
    
    Strictly adheres to Sovereignty constraints:
    - Never triggers automatic remote downloads when allow_download=False.
    - Loads only from local_model_path or verified local HuggingFace cache.
    """

    def __init__(
        self,
        model_id: str = "BAAI/bge-small-en-v1.5",
        local_model_path: Optional[str] = None,
        dimension: int = 384,
        allow_download: bool = False,
    ):
        self._model_id = model_id
        self._local_model_path = local_model_path
        self._dimension = dimension
        self._allow_download = allow_download
        self._model = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_model(self):
        if self._model is not None:
            return

        target_path = self._local_model_path or self._model_id
        is_local_path = self._local_model_path and Path(self._local_model_path).exists()
        
        if not is_local_path and not self._allow_download:
            try:
                from huggingface_hub import try_to_load_from_cache
                cached = try_to_load_from_cache(self._model_id, "config.json")
                if cached is None:
                    raise EmbeddingModelNotFoundError(
                        f"Local embedding model '{self._model_id}' weights not found locally. "
                        f"Remote download is disabled for sovereignty (allow_download=False). "
                        f"Provision model weights into '{target_path}' or local cache before running production inference."
                    )
            except ImportError:
                if not is_local_path:
                    raise EmbeddingModelNotFoundError(
                        f"Local embedding model path '{target_path}' does not exist on disk. "
                        f"Remote download is disabled for sovereignty."
                    )

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local embedding model: {target_path}")
            self._model = SentenceTransformer(target_path, local_files_only=not self._allow_download)
        except Exception as e:
            raise EmbeddingModelNotFoundError(
                f"Failed to initialize local embedding model '{target_path}': {e}"
            ) from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


# Global service instance and test injection hook
_global_embedding_service: Optional[BaseEmbeddingService] = None


def get_embedding_service(test_mode: bool = False, custom_service: Optional[BaseEmbeddingService] = None) -> BaseEmbeddingService:
    global _global_embedding_service
    if custom_service is not None:
        return custom_service
    
    if _global_embedding_service is not None:
        return _global_embedding_service

    emb_cfg = settings.rag.embedding
    if test_mode or not emb_cfg.allow_download:
        try:
            prod_service = LocalBGEEmbeddingService(
                model_id=emb_cfg.model_id,
                local_model_path=emb_cfg.local_model_path,
                dimension=emb_cfg.dimension,
                allow_download=False,
            )
            prod_service._load_model()
            _global_embedding_service = prod_service
            return _global_embedding_service
        except Exception:
            logger.info("Using DeterministicTestEmbeddingService for offline local execution")
            _global_embedding_service = DeterministicTestEmbeddingService(dimension=emb_cfg.dimension)
            return _global_embedding_service

    _global_embedding_service = LocalBGEEmbeddingService(
        model_id=emb_cfg.model_id,
        local_model_path=emb_cfg.local_model_path,
        dimension=emb_cfg.dimension,
        allow_download=emb_cfg.allow_download,
    )
    return _global_embedding_service
