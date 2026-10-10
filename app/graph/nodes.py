"""
LangGraph Nodes for RideWise Assist
Implements Intent Classification, RBAC Guard, Read-Only DB Execution,
Hybrid Policy RAG with Temporal Versioning, and Dynamic LLM Synthesis.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

from app.graph.state import RideWiseState
from app.database.repository import (
    get_customer_by_id,
    get_customer_bookings,
    get_booking_details,
    get_vehicle_by_id,
    get_fleet_summary,
    get_open_damage_claims,
    STATUS_CODE_MAP
)
from app.rag.hybrid_retriever import retriever
from app.cache.semantic_cache import semantic_cache
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

# Official hub names in Bengaluru
BANGALORE_HUBS = [
    "koramangala",
    "indiranagar",
    "jayanagar",
    "hsr layout",
    "electronic city",
    "whitefield",
    "hebbal"
]


def router_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Classifies user intent and extracts entities (booking_id, vehicle_id, hub_name).
    Checks dynamic semantic cache for previously generated responses.
    Does NOT return hardcoded answers - all new queries route through LangGraph to LLM.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "general"}

    last_user_msg = messages[-1]["content"].strip()
    lower_msg = last_user_msg.lower()
    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")

    # 1. Check Dynamic Semantic Cache (only hits if query was dynamically cached from prior LLM output)
    cached = semantic_cache.get(last_user_msg, role=role, customer_id=user_id if role == "customer" else None)
    if cached:
        return {
            "intent": "cache_hit",
            "final_response": cached["answer"],
            "citations": cached["citations"],
            "cache_status": f"Cache HIT ({cached.get('cache_hit')})"
        }

    # 2. Entity Extraction
    booking_match = re.search(r"\b(B-\d{4})\b", last_user_msg, re.IGNORECASE)
    extracted_booking = booking_match.group(1).upper() if booking_match else None

    vehicle_match = re.search(r"\b(VEH\d{3})\b", last_user_msg, re.IGNORECASE)
    extracted_vehicle = vehicle_match.group(1).upper() if vehicle_match else None

    extracted_hub = None
    for hub in BANGALORE_HUBS:
        if hub in lower_msg:
            extracted_hub = hub.title()
            break

    # 3. Intent Classification
    is_greeting = any(
        lower_msg.strip() == g or lower_msg.startswith(f"{g} ")
        for g in ("hi", "hello", "hey", "help", "who are you", "what can you do", "good morning", "good afternoon", "good evening", "greetings")
    )

    # Specific DB lookup signals (concrete entities or user's private data)
    user_db_signals = (
        "my booking", "my bookings", "my ride", "my rides", "my trip", "my trips",
        "my account", "my profile", "my tier", "my kyc", "who am i", "my details",
        "show bookings", "list bookings", "all bookings", "my refund",
        "change details", "update details", "edit details", "change my", "update my", "edit my"
    )
    has_specific_db_target = bool(
        extracted_booking or extracted_vehicle or extracted_hub or
        any(k in lower_msg for k in user_db_signals) or
        (role == "support_agent" and any(k in lower_msg for k in ("fleet", "damage", "claim", "claims", "cust0")))
    )

    policy_keywords = (
        "policy", "policies", "refund", "refunds", "cancel", "cancellation",
        "penalty", "penalties", "late fee", "late return", "delay", "grace period",
        "gst", "tax", "charge", "charges", "deposit", "battery", "ev", "charging",
        "charger", "breakdown", "towing", "tier benefit", "rules", "terms"
    )
    has_policy_kw = any(w in lower_msg for w in policy_keywords)

    general_db_keywords = ("fleet", "hub", "availability", "available", "damage", "claims")
    has_general_db = any(k in lower_msg for k in general_db_keywords)

    if is_greeting and not (has_specific_db_target or has_policy_kw or has_general_db):
        intent = "greeting"
    elif has_specific_db_target and has_policy_kw:
        intent = "hybrid"
    elif has_specific_db_target or has_general_db:
        intent = "db_query"
    elif has_policy_kw:
        intent = "policy_rag"
    else:
        intent = "general"

    return {
        "intent": intent,
        "extracted_booking_id": extracted_booking,
        "extracted_vehicle_id": extracted_vehicle,
        "extracted_hub_name": extracted_hub
    }


def rbac_guard_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Role-Based Access Control Node.
    Enforces security isolation: customers cannot access another customer's records
    or internal company-wide financial metrics.
    """
    if state.get("final_response"):
        return {}

    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""

    if role == "customer":
        # Check if customer is asking for another customer's ID explicitly
        other_cust_match = re.search(r"\b(CUST\d{4})\b", last_user_msg, re.IGNORECASE)
        if other_cust_match:
            queried_id = other_cust_match.group(1).upper()
            if queried_id != user_id.upper():
                return {
                    "final_response": (
                        f"🔒 **Access Restricted**: You are authenticated as `{user_id}`. "
                        f"In accordance with RideWise Privacy Policy, you cannot access or view data "
                        f"belonging to another customer (`{queried_id}`)."
                    ),
                    "citations": ["Security: Customer Entitlement Boundary"]
                }

        # Check if customer is asking for confidential company-wide operational financials
        restricted_phrases = [
            "total revenue", "all customers", "internal metrics",
            "damage claims for all", "fleet financial", "company revenue", "financial metrics"
        ]
        if any(rp in last_user_msg.lower() for rp in restricted_phrases):
            return {
                "final_response": (
                    "🔒 **Access Restricted**: Operational fleet statistics and company-wide financial records "
                    "are internal to RideWise operations and not accessible to customer accounts."
                ),
                "citations": ["Security: RBAC Entitlement Policy"]
            }

    return {}


def db_execution_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Executes safe read-only database queries and populates `sql_context`.
    No canned answers are generated here; all structured facts are passed to the synthesizer.
    """
    if state.get("final_response"):
        return {}

    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")
    booking_id = state.get("extracted_booking_id")
    vehicle_id = state.get("extracted_vehicle_id")
    hub_name = state.get("extracted_hub_name")
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""
    lower_msg = last_user_msg.lower()

    sql_context: Dict[str, Any] = {}

    # 1. Include customer profile if active role is customer
    if role == "customer":
        profile = state.get("customer_profile") or get_customer_by_id(user_id)
        if profile:
            sql_context["customer_profile"] = profile

    # 2. Specific booking lookup
    if booking_id:
        cust_filter = user_id if role == "customer" else None
        b_data = get_booking_details(booking_id, customer_id=cust_filter)
        if b_data:
            sql_context["booking"] = b_data
        else:
            if role == "customer":
                # Verify if booking exists under another customer (cross-tenant isolation)
                existing = get_booking_details(booking_id)
                if existing:
                    return {
                        "final_response": (
                            f"🔒 **Access Restricted**: Booking `{booking_id}` does not belong to your account (`{user_id}`). "
                            "You may only view bookings made under your own profile."
                        ),
                        "citations": ["Security: Data Isolation"]
                    }
                else:
                    sql_context["booking_not_found"] = f"Booking {booking_id} was not found in the RideWise database."
            else:
                sql_context["booking_not_found"] = f"Booking {booking_id} was not found in the RideWise database."

    # 3. Customer bookings list (if customer asks about bookings or trips)
    if role == "customer":
        booking_keywords = ("booking", "bookings", "ride", "rides", "trip", "trips", "recent", "history", "my rides", "my bookings", "orders")
        if not booking_id and (any(k in lower_msg for k in booking_keywords) or state.get("intent") in ("db_query", "hybrid")):
            user_bookings = get_customer_bookings(user_id, limit=5)
            sql_context["customer_recent_bookings"] = user_bookings

    # 4. Specific vehicle lookup
    if vehicle_id:
        v_data = get_vehicle_by_id(vehicle_id)
        if v_data:
            sql_context["vehicle_details"] = v_data

    # 5. Fleet / Hub availability lookup
    fleet_keywords = ("fleet", "hub", "availability", "available", "vehicles", "scooters", "bikes")
    if hub_name or any(k in lower_msg for k in fleet_keywords):
        fleet_data = get_fleet_summary(hub_name)
        sql_context["fleet_summary"] = fleet_data

    # 6. Open damage reports (Support Agent only)
    if role == "support_agent" and any(k in lower_msg for k in ("damage", "claim", "claims", "repairs", "open claims")):
        claims = get_open_damage_claims()
        sql_context["open_damage_claims"] = claims[:10]

    # 7. Support Agent Customer Lookup (with strict PII masking)
    cust_match = re.search(r"\b(CUST\d{4})\b", last_user_msg, re.IGNORECASE)
    if role == "support_agent" and cust_match:
        target_cust = cust_match.group(1).upper()
        cust_info = get_customer_by_id(target_cust, mask_pii=True)
        if cust_info:
            sql_context["queried_customer"] = cust_info
            sql_context["queried_customer_bookings"] = get_customer_bookings(target_cust, limit=5)

    return {"sql_context": sql_context}


def rag_retrieval_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Retrieves policy clauses with Temporal Version Filtering (v1 vs v2).
    Skips retrieval for pure greetings to keep system prompt lean.
    """
    if state.get("final_response"):
        return {}

    intent = state.get("intent")
    if intent == "greeting":
        return {
            "retrieved_policies": [],
            "policy_version_applied": None
        }

    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""
    sql_ctx = state.get("sql_context") or {}
    booking_data = sql_ctx.get("booking")

    booked_at = None
    if booking_data:
        booked_at = booking_data.get("booked_at")

    # Perform hybrid retrieval with temporal filtering
    matched_chunks = retriever.retrieve(
        query=last_user_msg,
        top_k=4,
        booked_at=booked_at
    )

    policy_version = None
    for chunk in matched_chunks:
        if chunk.get("doc_id") == "RW-POL-02":
            policy_version = "v1 (Applies to bookings made before 1 July 2026)"
        elif chunk.get("doc_id") == "RW-POL-03":
            policy_version = "v2 (Applies to bookings made on/after 1 July 2026)"

    return {
        "retrieved_policies": matched_chunks,
        "policy_version_applied": policy_version
    }


def synthesizer_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Generates dynamic, grounded answers using Azure OpenAI.
    Synthesizes conversational responses using live DB context, retrieved policy clauses,
    explicit arithmetic steps, and verified citations.
    """
    if state.get("final_response"):
        return {}

    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")
    customer_profile = state.get("customer_profile") or {}
    sql_ctx = state.get("sql_context") or {}
    policies = state.get("retrieved_policies") or []
    messages = state.get("messages", [])
    policy_ver = state.get("policy_version_applied")

    # Format DB context
    db_summary = json.dumps(sql_ctx, indent=2, default=str) if sql_ctx else "None"

    # Format policy context and citations
    policy_texts = []
    citations = []
    for p in policies:
        policy_texts.append(f"[{p['doc_id']} {p['doc_title']} § {p['section']}]\n{p['content']}")
        citations.append(p["citation"])

    formatted_policies = "\n\n".join(policy_texts) if policy_texts else "None"

    # Build Comprehensive Role & Instruction Prompt
    system_prompt = (
        "You are 'RideWise Assist', the official AI assistant for RideWise Mobility Pvt. Ltd. "
        "You answer questions from customers and support staff dynamically and conversationally, "
        "grounded strictly on verified company database records and official policy documents.\n\n"
        "=== ACTIVE USER & ROLE ===\n"
        f"• Active Role: {role.upper()}\n"
        f"• Active User Identifier: {user_id}\n"
        f"• Customer Full Name: {customer_profile.get('full_name', 'N/A')}\n"
        f"• Customer Tier: {customer_profile.get('customer_tier', 'STANDARD')}\n\n"
        "=== BEHAVIORAL & RESPONSE GUIDELINES ===\n"
        "1. GREETINGS & CASUAL INTROS:\n"
        "   - When the user greets you (e.g. 'hi', 'hello', 'who are you'), reply warmly and introduce yourself as RideWise Assist.\n"
        "   - Personalize the greeting with the user's name and tier (for customer) or staff role (for support agent).\n"
        "   - Mention key things you can help with (checking bookings, explaining charges/refunds, EV guidelines, Bangalore hub locations).\n\n"
        "2. USER PROFILE & DETAILS:\n"
        "   - When a customer asks about their profile, tier, KYC, or account details, explain them clearly from the database context.\n"
        "   - Cite [DB: customers.customer_id={user_id}].\n\n"
        "3. ACCOUNT & CONTACT DETAIL MODIFICATIONS:\n"
        "   - Customers CANNOT modify or edit personal/contact details (name, phone, email, address, KYC) via the AI assistant chat.\n"
        "   - DO NOT hallucinate fake OTP steps, form links, or imaginary database write operations.\n"
        "   - Clearly inform the customer that accounts and KYC records are strictly read-only in self-service, and they must reach out to RideWise Support directly at support@ridewise.example or +91 80 4000 1234 (7:00 AM - 11:00 PM IST) [RW-POL-01 § 9].\n\n"
        "4. BOOKING LISTS & INQUIRIES:\n"
        "   - When a customer asks for their bookings or rides, summarize their recent bookings from the database context with booking ID, vehicle model, status, and dates.\n"
        "   - Cite [DB: bookings.customer_id={user_id}].\n\n"
        "5. TEMPORAL CANCELLATION RULES:\n"
        "   - Bookings made BEFORE 1 July 2026, 00:00 IST follow Version 1 (RW-POL-02): >=24h = 100%, 6-24h = 50%, <6h = 0%.\n"
        "   - Bookings made ON OR AFTER 1 July 2026, 00:00 IST follow Version 2 (RW-POL-03): >=48h = 100%, 12-48h = 75%, 2-12h = 25%, <2h = 0%.\n"
        "   - The cancellation policy version depends ONLY on when the booking was MADE (booked_at), NOT when it was cancelled or scheduled.\n\n"
        "6. LATE RETURN CHARGES & TIERS:\n"
        "   - 1.5 × vehicle hourly rate per hour or part thereof (e.g. 20 min late counts as 1 full hour).\n"
        "   - GOLD Tier: Receives a 30-minute grace period. If returned <= 30 mins late, fee is ₹0. If > 30 mins late, the entire lateness is charged.\n"
        "   - Standard and Silver tiers have NO grace period.\n"
        "   - GST: All penalties attract 18% GST (e.g., ₹180 late fee + 18% GST = ₹212.40 total).\n\n"
        "7. EV LOW-BATTERY FEE:\n"
        "   - Returned below 10%: Flat ₹150 fee (+ 18% GST = ₹177 total).\n"
        "   - Returned at 10% or above: ₹0 (Exactly 10% is not below 10%, so ₹0).\n\n"
        "8. SECURITY DEPOSITS:\n"
        "   - Held via payment gateway and refunded in full within 3 days upon cancellation/trip completion. Deposit releases are handled by gateway and are not recorded as rows in the SQLite payments table.\n\n"
        "9. STATUS CODES:\n"
        "   - UPC=Upcoming, ONG=Ongoing, CMP=Completed, CNL_U=Cancelled by Customer, CNL_S=Cancelled by RideWise, NSH=No-show.\n\n"
        "10. CITATIONS & ARITHMETIC:\n"
        "   - ONLY cite documents and sections that directly support your answer. DO NOT spam or list irrelevant policy citations.\n"
        "   - Show explicit mathematical steps for any fee, penalty, or refund calculation.\n\n"
        "11. MANDATORY PII PROTECTION FOR SUPPORT AGENTS:\n"
        "   - When Active Role is SUPPORT_AGENT, customer phone numbers and emails MUST ALWAYS be partially masked in responses (e.g. Phone: 98450****5, Email: aa***@gmail.com).\n\n"
        "12. STRICT GROUNDING & ZERO HALLUCINATION DIRECTIVE:\n"
        "   - You must NEVER extrapolate, invent, or assume any feature, service, API, portal, OTP flow, or policy rule that is not explicitly stated in the DATABASE CONTEXT or RELEVANT POLICY DOCUMENTS.\n"
        "   - If a requested action or piece of information is not present in the provided context, state truthfully and concisely that it is not available or not supported, and refer the user to official support.\n\n"
        f"=== DATABASE CONTEXT ===\n{db_summary}\n\n"
        f"=== RELEVANT POLICY DOCUMENTS ===\n{formatted_policies}\n"
    )

    llm_messages = [{"role": "system", "content": system_prompt}]
    # Include up to last 6 conversational messages for multi-turn context
    for m in messages[-6:]:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    try:
        completion = llm_client.chat_completion(messages=llm_messages, temperature=0.0)
        response_text = completion["content"]

        # Gather relevant citations
        if sql_ctx.get("booking"):
            citations.append(f"DB: bookings.booking_id={sql_ctx['booking']['booking_id']}")
        if sql_ctx.get("customer_profile"):
            cid = sql_ctx["customer_profile"].get("customer_id") or user_id
            citations.append(f"DB: customers.customer_id={cid}")
        if sql_ctx.get("customer_recent_bookings"):
            citations.append(f"DB: bookings.customer_id={user_id}")
        if sql_ctx.get("fleet_summary"):
            citations.append("DB: vehicles")
        if sql_ctx.get("open_damage_claims"):
            citations.append("DB: damage_reports")

        # Dynamically cache policy/FAQ responses for future semantic matches
        if state.get("intent") == "policy_rag" and response_text:
            semantic_cache.add_entry(
                query=messages[-1]["content"],
                answer=response_text,
                citations=citations,
                role_scope="global"
            )

        return {
            "final_response": response_text,
            "citations": list(set(citations))
        }

    except Exception as e:
        logger.error(f"Synthesizer LLM error: {e}")
        # Safe fallback only in case of network/provider downtime
        fallback = (
            "⚠️ **Notice**: The LLM service is momentarily experiencing high demand. "
            "Here is the verified data retrieved from RideWise records:\n\n"
        )
        if sql_ctx.get("booking"):
            b = sql_ctx["booking"]
            fallback += (
                f"• **Booking ID**: `{b.get('booking_id')}`\n"
                f"• **Vehicle**: {b.get('vehicle_model')} ({b.get('vehicle_type')})\n"
                f"• **Status**: `{b.get('status_description')}`\n"
                f"• **Scheduled Pickup**: `{b.get('scheduled_start')}`\n"
                f"• **Scheduled Return**: `{b.get('scheduled_end')}`\n"
            )
        elif policies:
            fallback += f"• **Applicable Policy**: {policies[0]['doc_title']} ({policies[0]['section']})\n"
            fallback += f"{policies[0]['content'][:300]}..."
        else:
            fallback += "Please try your question again in a moment."

        return {
            "final_response": fallback,
            "citations": ["System Fallback Safety Engine"],
            "error_message": str(e)
        }


def verifier_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Final output check to guarantee citations and response integrity.
    Filters out spurious policy citations that have nothing to do with the generated answer.
    """
    final_resp = state.get("final_response") or ""
    raw_citations = state.get("citations") or []
    intent = state.get("intent", "general")

    filtered_citations = []
    for c in raw_citations:
        # Keep DB citations if DB data was relevant
        if c.startswith("DB:"):
            filtered_citations.append(c)
            continue

        # For policy citations, check if relevant to the response or intent
        c_lower = c.lower()
        resp_lower = final_resp.lower()
        if "rw-pol-01" in c_lower:
            if any(k in resp_lower for k in ("support", "contact", "email", "phone", "kyc", "terms", "deposit", "agreement")):
                filtered_citations.append(c)
        elif "rw-pol-02" in c_lower or "rw-pol-03" in c_lower:
            if any(k in resp_lower for k in ("cancel", "cancellation", "refund", "slab")):
                filtered_citations.append(c)
        elif "rw-pol-04" in c_lower:
            if any(k in resp_lower for k in ("late return", "late fee", "grace period", "damage", "scratch", "dent", "penalty schedule")):
                filtered_citations.append(c)
        elif "rw-pol-05" in c_lower:
            if any(k in resp_lower for k in ("battery", "charging", "ev", "range", "soc")):
                filtered_citations.append(c)
        else:
            filtered_citations.append(c)

    # Fallback to keep at least 1 citation if raw had any
    if not filtered_citations and raw_citations:
        filtered_citations = [raw_citations[0]]

    return {
        "final_response": final_resp,
        "citations": list(dict.fromkeys(filtered_citations))
    }
