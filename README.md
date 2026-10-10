# RideWise Assist 🛴💨

> **NeoStats AI Engineer Intern Hackathon Project**  
> A full-stack, enterprise-ready conversational AI assistant built for RideWise Mobility. It brings together operational SQLite database records and messy PDF policy docs into one clean, reliable assistant—complete with strict customer privacy (RBAC), automatic policy versioning (v1 vs. v2), dynamic runtime semantic caching, and an interactive frontend.

Built with Python, FastAPI, LangGraph, Azure OpenAI (`gpt-oss-120b`), and a custom GSAP web interface.

---

## 💡 Why We Built It This Way

When people interact with rental mobility services, they usually need answers that blend **their live ride data** (*"Why did my card get charged ₹354 extra on booking B-0001?"*) with **nuanced company policies** (*"Was I within the late return grace period for my membership tier?"*).

Most simple chatbots either:
1. Dump the entire database schema and all policy PDFs into the prompt (which burns tokens, blows past rate limits, and hallucinates calculations), or
2. Run unchecked text-to-SQL that accidentally exposes someone else's trip history or trips over SQLite date strings.

We engineered **RideWise Assist** as a modular, deterministic state graph. It knows who is talking, checks their permissions before touching the database, pulls only the exact policy clauses relevant to their booking date, and verifies all citations before spitting out an answer.

---

## 🏛️ System Architecture

Here is how a user query travels through the system:

```text
                                  +------------------------------------+
                                  |          Frontend Client           |
                                  |  • GSAP Animated Web UI (Port 8000)|
                                  |  • Streamlit Interface (Port 8501) |
                                  +-----------------+------------------+
                                                    |
                                                    | HTTP REST API
                                                    v
                                  +------------------------------------+
                                  |         FastAPI Backend            |
                                  |    (Session Store, Auth, Routing)  |
                                  +-----------------+------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                      LangGraph Workflow Engine                                          |
|                                                                                                         |
|  +--------------------+   +--------------------+   +---------------------+   +-----------------------+  |
|  |   1. Router Node   |-->| 2. RBAC Guard Node |-->| 3. DB Execution Node|-->|  4. Hybrid RAG Engine  |  |
|  | (Intent & Dynamic  |   | (Customer Isolation|   | (Safe Parameterized |   | (BM25 + Semantic      |  |
|  |  Semantic Cache)   |   |  & Staff Checks)   |   |  Read-Only SQL)     |   |  + Temporal Filter)   |  |
|  +--------------------+   +--------------------+   +---------------------+   +-----------+-----------+  |
|                                                                                          |              |
|                                                                                          v              |
|                                                        +---------------------+   +---------------+      |
|                                                        |  6. Verifier Node   |<--| 5. Synthesizer|      |
|                                                        | (Fact & Citation    |   | (Azure LLM    |      |
|                                                        |  Integrity Check)   |   |  Reasoning)   |      |
|                                                        +---------------------+   +---------------+      |
+---------------------------------------------------------------------------------------------------------+
                                   |                                    |
                                   v                                    v
                 +------------------------------------+   +------------------------------------+
                 |    Operational Database (DB)       |   |      Knowledge Base (Policies)     |
                 |  SQLite: ridewise.db (Read-Only)   |   |  5 PDF Documents + 2 Transcribed   |
                 |  Customers, Bookings, Vehicles,    |   |  Scanned Annexures (Refund Slabs   |
                 |  Payments, Damage Reports          |   |  & Gold Tier Grace Periods)        |
                 +------------------------------------+   +------------------------------------+
```

---

## ✨ Standout Features

### 1. Dual Personas & Hard RBAC Isolation
- **Customer Portal (`CUST0001` - `CUST0010`):** Customers get instant access to their own bookings, vehicle details, and payment receipts. If a customer tries to snoop on booking `B-0002` (which belongs to someone else) or asks for company-wide revenue metrics, the RBAC Guard intercepts it immediately and explains why access is denied. No customer data leaks. Ever.
- **Operations Support Desk (`Ananya Rao`, `Vikram Malhotra`, etc.):** Fleet managers and support agents can look up vehicle availability across Bangalore hubs (Indiranagar, Koramangala, Whitefield), track pending maintenance tickets, inspect damage disputes, and help customers troubleshoot issues across the board.

### 2. Time-Aware Policy Versioning (v1 vs. v2)
RideWise revised its cancellation rules midway through 2026. Applying the wrong version results in angry customers or lost revenue:
- **Booked before July 1, 2026 (00:00 IST):** Governed by **Policy v1 (`RW-POL-02`)** — 3 refund tiers (100%, 50%, 0%).
- **Booked on or after July 1, 2026 (00:00 IST):** Governed by **Policy v2 (`RW-POL-03`)** — 4 refund tiers (100%, 75%, 25%, 0%).
- The retriever checks `bookings.booked_at` first, then explicitly pulls only the matching version so the model never gets confused between the two schedules.

### 3. Digitized Scanned Annexures (No Hallucinations)
Two critical pieces of the business rules were stuck in image-only scanned annexures:
- **Annexure 1 of RW-POL-03:** The detailed 4-slab refund matrix ($\ge 48\text{h}: 100\%$, $12\text{--}48\text{h}: 75\%$, $2\text{--}12\text{h}: 25\%$, $<2\text{h}: 0\%$).
- **Annexure A of RW-POL-04:** Tier perks, notably that **Gold Tier members get a 30-minute grace period** on late vehicle returns.
We transcribed and grounded both into structured knowledge chunks so the assistant cites exact sections rather than guessing.

### 4. Hybrid Search with Reciprocal Rank Fusion (RRF)
- **BM25 Lexical Search** catches exact alphanumeric identifiers (`B-0001`, `VEH004`, `RW-POL-02`, section numbers, rupee amounts).
- **Sublinear TF-IDF Semantic Search** captures colloquial phrasing and conversational intent.
- **RRF** blends both rankings cleanly without needing hand-tuned similarity thresholds.

### 5. Dynamic Runtime Caching & Rate-Limit Shield
- **100% LLM Grounded Answers:** All user queries (greetings, profile details, booking status, and policy questions) are dynamically synthesized by the Azure OpenAI LLM grounded in live SQLite records and retrieved policy chunks. Zero answers are hardcoded.
- **Dynamic Semantic FAQ Cache:** When general policy questions are answered, they are dynamically indexed into an in-memory TF-IDF cosine similarity cache ($\ge 0.95$). Subsequent identical or semantically equivalent questions resolve from the dynamic cache in ~2ms.
- **Tenacity Exponential Backoff:** Gracefully handles Azure OpenAI `429 Too Many Requests` spikes with jittered retries so conversations never crash mid-sentence.

### 6. Interactive Frontend with GSAP Motion
- Glassmorphic, modern dashboard styled in dark emerald and slate.
- Micro-interactions powered by GSAP: smooth persona switching, staggered chat bubbles, typing indicators, quick-prompt pills, and collapsible citation badges.
- Also includes a plug-and-play **Streamlit** interface for quick testing and evaluation.

---

## 🚀 Quickstart Guide (Up and Running in 3 Minutes)

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### Step 1: Clone the Repo & Install Packages
```bash
git clone <repository-url>
cd Hackathon

# Create a virtual environment (recommended)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Set Up Your `.env` File
Copy the provided template to create your local `.env`:
```bash
cp .env.example .env
```
Open `.env` and verify the credentials:
```ini
AZURE_OPENAI_ENDPOINT=https://your-resource-name.services.ai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=<your_provided_api_key>
AZURE_OPENAI_MODEL_NAME=gpt-oss-120b
AZURE_OPENAI_DEPLOYMENT_NAME=Neo-Hackathon
DATABASE_PATH=Neostats Hackathon AI Usecase/ridewise.db
POLICIES_DIR=Neostats Hackathon AI Usecase
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```
*(Note: `.env` is listed in `.gitignore` and is never committed to GitHub.)*

---

## 🏃 Running the Application

### Option A: Modern Web App (Recommended)
Launch the FastAPI backend and web client with one command:
```bash
python run.py
```
Then open your browser to **[http://localhost:8000](http://localhost:8000)**.

### Option B: Streamlit Interface
If you want to test in the classic Streamlit view:
```bash
streamlit run ui/streamlit_app.py
```
Then open your browser to **[http://localhost:8501](http://localhost:8501)**.

---

## 🧪 Try These Test Scenarios

Here are a few quick scenarios you can test right away in the UI:

| Scenario | Role Selected | What to Ask / Click | What Should Happen |
| :--- | :--- | :--- | :--- |
| **RBAC Security** | Customer `CUST0001` (Aarav Sharma) | *"Can you show me the booking details for B-0002?"* | **Blocked.** The assistant politely tells Aarav that booking `B-0002` belongs to someone else (`CUST0003`) and keeps Aarav's view isolated. |
| **Gold Grace Period** | Customer `CUST0001` (Gold Member) | *"Why wasn't I charged a late fee on booking B-0001?"* | **Grounded answer.** Explains that the 20-minute delay was covered under the Gold tier's 30-minute grace period (Annexure A, RW-POL-04). |
| **Temporal Policy (v2)** | Customer `CUST0001` | *"How much refund would I get if I cancelled B-0001 right now?"* | **v2 Applied.** Recognizes the booking was made in August 2026 $\rightarrow$ applies the 4-tier schedule from Policy v2 (`RW-POL-03`) instead of v1. |
| **EV Battery Rule** | Anyone | *"What happens if I return an EV scooter with exactly 10% battery?"* | **Zero fee.** Accurately references Section 4.2 of the EV Guide & Fee Schedule: the penalty only triggers if returned *below* 10%. Exactly 10% incurs ₹0 fee. |
| **Fleet Operations** | Support Agent (Ananya Rao) | *"Show me all available vehicles in Indiranagar hub"* | **Full operational view.** Lists bikes, scooters, and EVs stationed at Indiranagar with live plate and status details. |

---

## 📁 Repository Layout

```text
├── .env.example                  # Environment configuration template (safe to commit)
├── .gitignore                    # Keeps .env, cache files, and databases out of Git
├── README.md                     # You are here! Complete setup and overview guide
├── DECISIONS.md                  # Honest architectural decisions, tradeoffs & what's next
├── requirements.txt              # Pinned Python package dependencies
├── run.py                        # Single-command launcher (FastAPI + static UI)
├── app/
│   ├── config.py                 # Pydantic settings & environment loader
│   ├── database/
│   │   ├── connection.py         # Read-only SQLite connector (URI mode=ro)
│   │   └── repository.py         # Safe parameterized SQL queries & RBAC checks
│   ├── rag/
│   │   ├── knowledge_base.py     # Transcribed policy corpus & scanned annexures
│   │   └── hybrid_retriever.py   # BM25 + Sublinear TF-IDF + RRF + Date-based filter
│   ├── cache/
│   │   └── semantic_cache.py     # Dynamic runtime semantic cache (starts empty, caches LLM output)
│   ├── llm/
│   │   └── client.py             # Azure OpenAI client with Tenacity backoff retries
│   ├── graph/
│   │   ├── state.py              # LangGraph typed conversation state
│   │   ├── nodes.py              # Individual agent nodes (Router, RBAC, SQL, RAG, etc.)
│   │   └── workflow.py           # Compiled LangGraph StateGraph pipeline
│   └── main.py                   # FastAPI REST API & static file serving
└── ui/
    ├── index.html                # Modern dashboard UI
    ├── static/
    │   ├── style.css             # Glassmorphic emerald styling & animations
    │   └── app.js                # Frontend logic, GSAP animations, and API calls
    └── streamlit_app.py          # Companion Streamlit interface
```

---

## 👥 Authors & Acknowledgments

- Built by a college student engineer for the **NeoStats AI Engineer Intern Hackathon (October 2026)**.
- Designed with care for clean software engineering principles, realistic edge-case handling, and snappy user experience.
