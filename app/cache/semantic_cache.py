"""
Multi-tier Caching Engine:
1. Dynamic Semantic Policy/FAQ Cache (Cosine similarity matching)
2. Safe runtime storage of generated responses
"""

from typing import Optional, Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticCache:
    def __init__(self):
        # In-memory storage of dynamically cached entries. Starts completely EMPTY.
        self.entries: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.fitted = False
        self.tfidf_matrix = None

    def add_entry(self, query: str, answer: str, citations: List[str], role_scope: str = "global"):
        """
        Dynamically caches a synthesized response at runtime.
        Only called after genuine RAG/LLM synthesis.
        """
        cleaned = query.strip().lower()
        if not cleaned or not answer:
            return

        # Update if exact query already exists
        for e in self.entries:
            if e["query"] == cleaned and e["role_scope"] == role_scope:
                e["answer"] = answer
                e["citations"] = citations
                return

        self.entries.append({
            "query": cleaned,
            "answer": answer,
            "citations": citations,
            "role_scope": role_scope
        })
        queries = [e["query"] for e in self.entries]
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(queries)
            self.fitted = True
        except Exception:
            self.fitted = False

    def get(self, query: str, role: str = "customer", customer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves dynamically cached response if cosine similarity >= 0.95 for general FAQs.
        Customer-specific entries only match within the same customer_id.
        """
        if not self.fitted or not self.entries or self.tfidf_matrix is None:
            return None

        cleaned_query = query.strip().lower()
        if not cleaned_query:
            return None

        # 1. Exact match check
        for e in self.entries:
            if e["query"] == cleaned_query:
                if e["role_scope"] == "global" or (customer_id and e["role_scope"] == customer_id):
                    return {
                        "answer": e["answer"],
                        "citations": e["citations"],
                        "cache_hit": "exact"
                    }

        # 2. Semantic TF-IDF cosine similarity check
        try:
            q_vec = self.vectorizer.transform([cleaned_query])
            sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
            best_idx = int(sims.argmax())
            best_score = float(sims[best_idx])

            if best_score >= 0.95:
                matched = self.entries[best_idx]
                if matched["role_scope"] == "global" or (customer_id and matched["role_scope"] == customer_id):
                    return {
                        "answer": matched["answer"],
                        "citations": matched["citations"],
                        "similarity": round(best_score, 3),
                        "cache_hit": "semantic"
                    }
        except Exception:
            return None

        return None

    def clear(self):
        """Clears all dynamically cached entries."""
        self.entries = []
        self.fitted = False
        self.tfidf_matrix = None


# Singleton cache instance
semantic_cache = SemanticCache()
