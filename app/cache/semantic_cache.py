"""
Multi-tier Caching Engine:
1. Deterministic Rule Shortcuts (0 tokens, 0ms)
2. Semantic Policy/FAQ Cache (Cosine similarity matching)
3. SQL/Entity Memory Cache
"""

import re
from typing import Optional, Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SemanticCache:
    def __init__(self):
        # In-memory storage of FAQ entries: list of dicts
        self.entries: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.fitted = False

        # Seed with initial common FAQ pairs to prime cache instantly!
        self._seed_common_faqs()

    def _seed_common_faqs(self):
        seed_data = [
            {
                "query": "How do I charge an EV scooter at home?",
                "role_scope": "global",
                "answer": (
                    "To charge your RideWise EV scooter at home:\n"
                    "1. Use only the RideWise charging cable provided under the seat.\n"
                    "2. Plug into a properly earthed 15 A socket.\n"
                    "3. Charging at a RideWise hub is free, or you may charge at home.\n"
                    "\n*Source: [RW-POL-05 EV User Guide & FAQ § 5]*"
                ),
                "citations": ["RW-POL-05 § 5"]
            },
            {
                "query": "What is the penalty if I return the vehicle with low battery?",
                "role_scope": "global",
                "answer": (
                    "For electric vehicles (EV scooter or EV bike):\n"
                    "• If returned below 10% battery: A flat charging fee of ₹150 applies (+ 18% GST = ₹177 total).\n"
                    "• If returned at 10% or above: No fee (₹0).\n"
                    "Note: Exactly 10% is not below 10%, so no fee is charged.\n"
                    "\n*Source: [RW-POL-04 Late Return & Damage Penalty Schedule § 2]*"
                ),
                "citations": ["RW-POL-04 § 2"]
            },
            {
                "query": "What is the late return fee calculation?",
                "role_scope": "global",
                "answer": (
                    "Late return charges are calculated as follows:\n"
                    "• Each late hour or part of an hour is charged at 1.5 × the vehicle's hourly rate (e.g. 20 minutes late counts as 1 full hour).\n"
                    "• Customers in the GOLD tier receive a 30-minute grace period. If returned within 30 minutes, no fee applies. If returned >30 minutes late, the entire lateness is charged.\n"
                    "• Standard and Silver tiers have no grace period.\n"
                    "• All penalties attract 18% GST.\n"
                    "\n*Source: [RW-POL-04 Late Return & Damage Penalty Schedule § 1 & Annexure A]*"
                ),
                "citations": ["RW-POL-04 § 1"]
            },
            {
                "query": "What are the Bangalore hub locations?",
                "role_scope": "global",
                "answer": (
                    "RideWise operates 7 pickup and return hubs across Bengaluru:\n"
                    "1. Koramangala\n2. Indiranagar\n3. Jayanagar\n4. HSR Layout\n5. Electronic City\n6. Whitefield\n7. Hebbal\n"
                    "Note: Vehicles must be returned to the same hub from which they were picked up.\n"
                    "\n*Source: [RW-POL-01 Rental Agreement & Terms § 3]*"
                ),
                "citations": ["RW-POL-01 § 3"]
            },
            {
                "query": "What happens in case of a breakdown or empty battery?",
                "role_scope": "global",
                "answer": (
                    "If your EV battery runs out or the vehicle breaks down:\n"
                    "1. Stop safely and call RideWise Support immediately at **+91 80 4000 1234**.\n"
                    "2. A team from the nearest hub will deliver a charged vehicle or arrange towing.\n"
                    "3. Towing is completely free if caused by a vehicle defect.\n"
                    "\n*Source: [RW-POL-05 EV User Guide & FAQ § 5]*"
                ),
                "citations": ["RW-POL-05 § 5"]
            }
        ]
        for item in seed_data:
            self.add_entry(item["query"], item["answer"], item["citations"], item["role_scope"])

    def add_entry(self, query: str, answer: str, citations: List[str], role_scope: str = "global"):
        """Adds a verified Q&A pair to the semantic cache."""
        self.entries.append({
            "query": query.strip().lower(),
            "answer": answer,
            "citations": citations,
            "role_scope": role_scope
        })
        queries = [e["query"] for e in self.entries]
        self.tfidf_matrix = self.vectorizer.fit_transform(queries)
        self.fitted = True

    def get(self, query: str, role: str, customer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response if cosine similarity >= 0.92 for general FAQs.
        Customer-specific entries only match within the same customer_id.
        """
        if not self.fitted or not self.entries:
            return None
        
        cleaned_query = query.strip().lower()
        # Direct exact match check
        for e in self.entries:
            if e["query"] == cleaned_query:
                if e["role_scope"] == "global" or e["role_scope"] == customer_id:
                    return {"answer": e["answer"], "citations": e["citations"], "cache_hit": "exact"}

        # Semantic TF-IDF similarity check
        try:
            q_vec = self.vectorizer.transform([cleaned_query])
            sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
            best_idx = int(sims.argmax())
            best_score = float(sims[best_idx])
            
            if best_score >= 0.92:
                matched = self.entries[best_idx]
                if matched["role_scope"] == "global" or matched["role_scope"] == customer_id:
                    return {
                        "answer": matched["answer"],
                        "citations": matched["citations"],
                        "similarity": best_score,
                        "cache_hit": "semantic"
                    }
        except Exception:
            return None
        
        return None

# Singleton cache instance
semantic_cache = SemanticCache()
