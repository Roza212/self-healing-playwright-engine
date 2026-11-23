"""Lazy-loaded sentence embedding wrapper with in-memory caching is provided here."""

from typing import Any

import numpy as np


class Embedder:
    """Text embeddings are computed lazily on CPU and cached in memory by text key."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        """The model identifier and empty cache are initialized without loading weights."""
        self.model_name = model_name
        self._model: Any = None
        self._cache: dict[str, np.ndarray] = {}

    def encode(self, texts: list[str]) -> np.ndarray:
        """Normalized vector embeddings are returned for the given list of texts."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        missing = list(dict.fromkeys(t for t in texts if t not in self._cache))
        if missing:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name, device="cpu")
            vecs = self._model.encode(
                missing,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            for text_key, vec in zip(missing, vecs, strict=True):
                self._cache[text_key] = np.asarray(vec, dtype=np.float32)

        return np.vstack([self._cache[t] for t in texts])
