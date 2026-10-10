"""
Hybrid Policy Retriever (BM25 + Dense Semantic TF-IDF + Reciprocal Rank Fusion + Temporal Filtering)
"""

import re
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.rag.knowledge_base import POLICY_CHUNKS

from sklearn.feature_extraction import text

# Conversational stop words and standard English stopwords to avoid spurious matches
STOP_WORDS = set(text.ENGLISH_STOP_WORDS).union({
    "want", "tell", "show", "please", "need", "give", "can", "let", "know",
    "would", "like", "able", "way", "help", "thank", "thanks", "hello", "hi"
})

class HybridPolicyRetriever:
    def __init__(self, chunks: List[Dict[str, Any]] = None):
        self.chunks = chunks or POLICY_CHUNKS
        
        # Prepare text representation for BM25 (content + keywords + section)
        self.corpus_texts = [
            f"{c['doc_title']} {c['section']} {' '.join(c['keywords'])} {c['content']}"
            for c in self.chunks
        ]
        
        # Initialize BM25 with stop words removed
        tokenized_corpus = [self._tokenize(text) for text in self.corpus_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # Initialize Semantic TF-IDF Vectorizer with word & sub-word n-grams
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w\.\%₹\-]+\b",
            lowercase=True,
            stop_words="english"
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_texts)

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and split on non-alphanumeric except ₹, %, -
        cleaned = re.sub(r"[^\w\s₹\%\.\-]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 1 and w not in STOP_WORDS]

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        booked_at: Optional[str] = None,
        force_policy_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant policy clauses using Hybrid RRF.
        Applies temporal filtering:
        - booked_at < 2026-07-01 -> Prefer/Enforce RW-POL-02 (v1)
        - booked_at >= 2026-07-01 -> Prefer/Enforce RW-POL-03 (v2)
        """
        # Determine temporal policy constraint if booked_at is provided
        target_v1 = False
        target_v2 = False
        
        if force_policy_version == "v1":
            target_v1 = True
        elif force_policy_version == "v2":
            target_v2 = True
        elif booked_at:
            # Check if booked_at is before 2026-07-01
            # Format: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
            date_prefix = booked_at.split()[0]
            if date_prefix < "2026-07-01":
                target_v1 = True
            else:
                target_v2 = True

        # 1. BM25 Sparse Search
        query_tokens = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(query_tokens) if query_tokens else np.zeros(len(self.chunks))

        # 2. Semantic Dense Search
        query_vec = self.vectorizer.transform([query])
        semantic_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 3. Reciprocal Rank Fusion (RRF) with strict relevance gating
        # Only rank chunks that have meaningful signal:
        # - BM25: score > 0.5
        # - Semantic: cosine similarity >= 0.12
        bm25_hits = [(score, idx) for idx, score in enumerate(bm25_scores) if score > 0.5]
        bm25_hits.sort(key=lambda x: x[0], reverse=True)
        bm25_ranks = {idx: rank + 1 for rank, (score, idx) in enumerate(bm25_hits)}

        sem_hits = [(score, idx) for idx, score in enumerate(semantic_scores) if score >= 0.12]
        sem_hits.sort(key=lambda x: x[0], reverse=True)
        sem_ranks = {idx: rank + 1 for rank, (score, idx) in enumerate(sem_hits)}

        rrf_scores = []
        for i, chunk in enumerate(self.chunks):
            # Check temporal policy filter
            doc_id = chunk["doc_id"]
            if target_v1 and doc_id == "RW-POL-03":
                continue
            elif target_v2 and doc_id == "RW-POL-02":
                continue

            r_bm25 = bm25_ranks.get(i)
            r_sem = sem_ranks.get(i)

            # Skip chunk entirely if it didn't pass BM25 or semantic relevance threshold
            if r_bm25 is None and r_sem is None:
                continue

            score = 0.0
            if r_bm25 is not None:
                score += 1.0 / (60 + r_bm25)
            if r_sem is not None:
                score += 1.0 / (60 + r_sem)

            # Bonus if exact doc_id matches query
            if doc_id.lower() in query.lower():
                score += 0.05

            rrf_scores.append((score, i))

        # Sort by final RRF score
        rrf_scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in rrf_scores[:top_k]:
            if score <= 0.0:
                continue
            chunk = dict(self.chunks[idx])
            chunk["retrieval_score"] = float(score)
            chunk["citation"] = f"[{chunk['doc_id']} {chunk['doc_title']} § {chunk['section']}]"
            results.append(chunk)

        return results

# Singleton instance
retriever = HybridPolicyRetriever()
