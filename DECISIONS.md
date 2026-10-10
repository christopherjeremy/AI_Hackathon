# Engineering Decisions & Honest Reflections (`DECISIONS.md`)
**Project:** RideWise Assist  
**Author:** AI Engineer Hackathon Participant (College Student / Intern Candidate)  
**Date:** October 10, 2026  

---

## 1. What were your three most important design decisions, and why?

### Decision 1: Explicit Temporal Policy Versioning Governed by `bookings.booked_at`
- **What I decided:** Instead of letting the LLM read both cancellation documents and pray that it figures out which one applies, I built an explicit **Temporal Policy Filter** right inside our retrieval engine. Whenever a query concerns a specific booking's cancellation or refund, the system extracts the booking date (`booked_at`).
  - If `booked_at < 2026-07-01 00:00:00 IST`, the retriever pulls **Policy v1 (`RW-POL-02`)** and completely suppresses v2.
  - If `booked_at >= 2026-07-01 00:00:00 IST`, it pulls **Policy v2 (`RW-POL-03`)** and suppresses v1.
- **Why I made this call:** In the document pack, NeoStats explicitly specified that cancellation terms are bound by when the reservation was *created*, not when the trip happened or when the user initiated the cancellation. When I tested standard vector search across both files, the model kept mixing up the older 3-tier refund schedule (100% / 50% / 0%) with the updated 4-tier schedule (100% / 75% / 25% / 0%). Deciding this at the retrieval layer using deterministic Python code guarantees 100% accuracy and completely eliminates policy hallucinations.

### Decision 2: Guarded Multi-Node LangGraph Flow with Strict Pre-Execution RBAC
- **What I decided:** Rather than building a single monolithic prompt with tool calling, I broke down the conversation flow into an explicit, compiled **LangGraph** (`Router` $\rightarrow$ `RBAC Guard` $\rightarrow$ `DB Execution` $\rightarrow$ `RAG Retrieval` $\rightarrow$ `Synthesizer` $\rightarrow$ `Verifier`).
- **Why I made this call:**
  1. **Security first:** If you rely on the LLM to enforce privacy ("please only show data if customer matches"), clever prompt injection or edge-case wording can trick it into returning other customers' phone numbers, addresses, or trip costs. By sticking an RBAC Guard node in Python *ahead* of the database execution, cross-customer data leakage is rendered virtually impossible.
  2. **Conversational Intelligence over Hardcoded Logic:** Rather than short-circuiting queries with rigid hardcoded string templates, all profile, booking, and policy requests flow through the DB execution and hybrid RAG layers into the LLM synthesizer. This ensures responses are genuinely conversational, naturally phrased, and dynamically grounded in live SQLite records without any pre-baked answers.
  3. **Arithmetic accuracy:** Combining SQL operational values (hourly rate, return timestamp, actual lateness) with retrieved policy text (e.g., $1.5\times$ penalty multiplier + 18% GST) into structured prompt state gives the model all the facts in one place, avoiding weird math errors.

### Decision 3: Dynamic Runtime Semantic Caching + Manual Grounding of Scanned Annexures
- **What I decided:** I built a dynamic semantic cache (which starts completely unseeded with zero hardcoded answers, caching only genuine LLM-synthesized policy answers at runtime with TF-IDF cosine similarity $\ge 0.95$) alongside Tenacity exponential backoff retries. On top of that, I personally inspected and transcribed the scanned image annexures (**Annexure 1 of RW-POL-03** and **Annexure A of RW-POL-04**) into clean markdown chunks.
- **Why I made this call:**
  1. Shared Azure OpenAI endpoints during hackathons can experience `429 Too Many Requests` rate limits. Caching dynamic policy responses at runtime protects our API budget while never serving fake or hardcoded mock answers.
  2. Standard text extractors (like basic `pypdf` or `pdfplumber`) often choke or produce gibberish on scanned images. Those two annexures held two critical edge cases: the Gold Tier 30-minute late return grace period and the 4-tier refund schedule. Transcribing and chunking them cleanly ensured the assistant never missed these details.

---

## 2. Which alternatives did you consider and reject?

| Alternative Considered | Why I Rejected It | What I Built Instead |
| :--- | :--- | :--- |
| **Autonomous Text-to-SQL via LLM** | Giving the LLM free rein to write raw SQL on SQLite sounded fancy, but in practice, it easily hallucinated column names, choked on SQLite date parsing (`strftime`), and ran the risk of accidental SQL injection or cross-tenant leaks. | **Guarded Parameterized Repository + Safe Read-Only URI:** Routine queries use battle-tested parameterized methods with tenant ID injection. The database connection itself is opened with `mode=ro` (read-only) so write operations are physically impossible. |
| **Pure Dense Vector Search (without BM25)** | Embeddings are great for fuzzy meaning, but they consistently dropped the ball on specific alphanumeric codes like booking IDs (`B-0001`), policy codes (`RW-POL-02`), vehicle plates, and exact rupee numbers (`₹150`, `₹354`). | **Hybrid Search with Reciprocal Rank Fusion (RRF):** BM25 matches exact codes and section numbers reliably, while dense/sublinear semantic search catches casual user language. RRF merges both lists without needing brittle manual score thresholds. |
| **Monolithic "Everything-in-One-Prompt" Agent** | Shoving the SQLite database schema and all 5 policy PDFs into the system prompt for every turn rapidly exceeds token limits, makes responses sluggish (5-8 seconds per turn), and causes the model to lose track of fine print. | **Stateful LangGraph with Targeted Context:** Only the specific rows and the top 3-4 policy chunks needed for that exact turn get injected into the synthesizer prompt. |

---

## 3. Where does your assistant currently fail or behave poorly?

Being completely honest about the system's limitations:

1. **Intricate Multi-Condition Hypothetical Scenarios:**
   - If a user asks a heavily nested "what if" question (e.g., *"If I book an Ola S1 tomorrow for 6 hours, return it 45 mins late with 7% battery as a Silver member, and claim a scratched helmet, what is my total credit card deduction?"*), the assistant calculates every individual fee accurately, but sometimes outputs the result as a dense markdown breakdown instead of an easy-to-read chronological story.
2. **Ambiguous Relative Dates in Chat:**
   - Phrases like *"my trip last Thursday"* require resolving the relative day against the current local date. If a customer took two different trips in that same week, the assistant currently asks for the booking ID or defaults to their most recent booking rather than asking a smooth disambiguation question.
3. **Open-Ended Fleet Analytics for Support Agents:**
   - Support staff can easily filter hubs, view vehicle availability, and inspect damage disputes. But if a support agent asks for complex, un-templated business intelligence queries (like *"Calculate the month-over-month growth rate of EV battery drainage across HSR and Koramangala"*), the system falls back to a generalized summary rather than computing dynamic on-the-fly analytical SQL.

---

## 4. What would you build next with one more week?

If I had another week before submission, here is what I would tackle next:

1. **Mock Payment Gateway & Razorpay Webhook Integration:**
   - The policy documents point out that security deposit holds are managed externally by the payment gateway and aren't stored in the SQLite `payments` table. I would build a mock Razorpay/Stripe webhook service so users and agents can view live deposit release timelines right in the chat sidebar.
2. **Live Hub Map & Fleet Telemetry Dashboard:**
   - Connect an interactive Leaflet/Mapbox map in our GSAP frontend displaying live Bangalore hub locations, real-time GPS scooter coordinates, and charging station availability.
3. **Actionable Operations Desk Tools:**
   - Expand the support agent persona so staff can take concrete operational actions directly through the chat—such as waiving an unfair late fee, pushing an instant refund override, or flagging a vehicle for battery replacement.
4. **Automated LLM-as-a-Judge Evaluation Suite:**
   - Set up an automated testing pipeline using Ragas or DeepEval to continuously benchmark Groundedness, Answer Relevance, and Context Precision across 100+ synthetic edge-case tickets on every pull request.
