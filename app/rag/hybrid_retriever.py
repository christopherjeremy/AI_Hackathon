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

class HybridPolicyRetriever:
    def __init__(self, chunks: List[Dict[str, Any]] = None):
        self.chunks = chunks or POLICY_CHUNKS
        
        # Prepare text representation for BM25 (content + keywords + section)
        self.corpus_texts = [
            f"{c['doc_title']} {c['section']} {' '.join(c['keywords'])} {c['content']}"
            for c in self.chunks
        ]
        
        # Initialize BM25
        tokenized_corpus = [self._tokenize(text) for text in self.corpus_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # Initialize Semantic TF-IDF Vectorizer with word & sub-word n-grams
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w\.\%₹\-]+\b",
            lowercase=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_texts)

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and split on non-alphanumeric except ₹, %, -
        cleaned = re.sub(r"[^\w\s₹\%\.\-]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 1]

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

        # 3. Reciprocal Rank Fusion (RRF)
        # Sort indices by BM25
        bm25_ranked = np.argsort(bm25_scores)[::-1]
        bm25_ranks = {idx: rank + 1 for rank, idx in enumerate(bm25_ranked)}

        # Sort indices by Semantic
        semantic_ranked = np.argsort(semantic_scores)[::-1]
        semantic_ranks = {idx: rank + 1 for rank, idx in enumerate(semantic_ranked)}

        rrf_scores = []
        for i, chunk in enumerate(self.chunks):
            # Check temporal policy filter
            doc_id = chunk["doc_id"]
            if target_v1 and doc_id == "RW-POL-03":
                # Demote or skip v2 when booking is strictly under v1
                score = 0.0
            elif target_v2 and doc_id == "RW-POL-02":
                # Demote or skip v1 when booking is strictly under v2
                score = 0.0
            else:
                r_bm25 = bm25_ranks[i]
                r_sem = semantic_ranks[i]
                # Standard RRF formula with k=60
                score = (1.0 / (60 + r_bm25)) + (1.0 / (60 + r_sem))
                
                # Bonus if exact doc_id or vehicle model matches
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
