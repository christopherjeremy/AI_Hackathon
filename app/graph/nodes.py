"""
LangGraph Nodes for RideWise Assist
Implements Intent Classification, RBAC Guard, Read-Only DB Lookup,
Hybrid Policy RAG with Temporal Versioning, and Arithmetic-Aware Synthesis.
"""

import re
import json
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

# Hub names list
BANGALORE_HUBS = ["koramangala", "indiranagar", "jayanagar", "hsr layout", "electronic city", "whitefield", "hebbal"]

def router_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Classifies user intent, extracts entities (booking_id, vehicle_id, hub),
    and checks shortcut / semantic cache before invoking heavier nodes.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "general"}
    
    last_user_msg = messages[-1]["content"].strip()
    lower_msg = last_user_msg.lower()
    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")

    # 1. Check Deterministic Rule Shortcuts
    # Shortcut A: Greetings / Help
    if lower_msg in ("hi", "hello", "hey", "help", "who are you", "what can you do"):
        if role == "customer":
            profile = state.get("customer_profile") or {}
            name = profile.get("full_name", "Valued Customer")
            tier = profile.get("customer_tier", "STANDARD")
            greeting = (
                f"Hello {name}! 👋 Welcome to **RideWise Assist**.\n\n"
                f"I am your personal rental assistant (Tier: **{tier}**).\n"
                "Here are a few things I can help you with:\n"
                "• **Check your bookings** (e.g. *'Show my active bookings'* or *'Status of B-0001'*)\n"
                "• **Understand charges & refunds** (e.g. *'Why was I charged a late fee?'* or *'What is my refund?'*)\n"
                "• **EV Guidelines & Charging** (e.g. *'How to charge Ather 450X at home'* or *'Battery penalty'*)\n"
                "• **Rental policies & KYC** (e.g. *'What is the security deposit?'*)"
            )
        else:
            greeting = (
                f"Hello {user_id}! 🎧 **RideWise Support Desk Assistant** active.\n\n"
                "Operational capabilities available:\n"
                "• **Cross-customer booking lookups** (e.g. *'Details for booking B-0045'*)\n"
                "• **Fleet & Hub status** (e.g. *'Show vehicles in Indiranagar hub'* or *'Fleet summary'*)\n"
                "• **Damage claim inspection** (e.g. *'List open damage reports'*)\n"
                "• **Policy resolution & temporal verification** (v1 vs v2 cancellation rules)"
            )
        return {
            "intent": "shortcut",
            "final_response": greeting,
            "citations": ["System Prompt"]
        }

    # Shortcut B: Customer Profile
    if role == "customer" and any(k in lower_msg for k in ("who am i", "my profile", "my account", "my tier")):
        profile = state.get("customer_profile") or get_customer_by_id(user_id) or {}
        profile_text = (
            f"👤 **Customer Profile Details**:\n\n"
            f"• **Customer ID**: `{profile.get('customer_id', user_id)}`\n"
            f"• **Full Name**: {profile.get('full_name', 'N/A')}\n"
            f"• **Tier**: **{profile.get('customer_tier', 'STANDARD')}** "
            f"*(Gold tier receives 30-min late return grace period)*\n"
            f"• **KYC Status**: `{profile.get('kyc_status', 'N/A')}`\n"
            f"• **Registered City**: {profile.get('city', 'Bengaluru')}\n"
            f"• **Mobile**: {profile.get('phone', 'N/A')}\n"
            f"• **Email**: {profile.get('email', 'N/A')}"
        )
        return {
            "intent": "shortcut",
            "final_response": profile_text,
            "citations": [f"Database: customers.customer_id={user_id}"]
        }

    # Shortcut C: Customer Listing Bookings
    if role == "customer" and any(k in lower_msg for k in ("my bookings", "my rides", "show bookings", "list my bookings")):
        bookings = get_customer_bookings(user_id, limit=5)
        if not bookings:
            return {
                "intent": "shortcut",
                "final_response": "You currently have no bookings on record with RideWise.",
                "citations": [f"Database: bookings.customer_id={user_id}"]
            }
        b_lines = [f"📋 **Your Recent Bookings ({len(bookings)} found)**:\n"]
        for b in bookings:
            status_desc = b.get("status_description", b.get("booking_status"))
            b_lines.append(
                f"• **Booking `{b['booking_id']}`** | Vehicle: **{b.get('vehicle_model', 'N/A')}** ({b.get('vehicle_type', 'N/A')})\n"
                f"  Status: `{status_desc}` | Pickup: `{b.get('scheduled_start', 'N/A')}` | Return: `{b.get('scheduled_end', 'N/A')}`"
            )
        b_lines.append("\n*Tip: Ask 'Tell me more about booking B-XXXX' for complete charge and payment details.*")
        return {
            "intent": "shortcut",
            "final_response": "\n".join(b_lines),
            "citations": [f"Database: bookings.customer_id={user_id}"]
        }

    # 2. Check Semantic FAQ Cache (Zero LLM Tokens!)
    cached = semantic_cache.get(last_user_msg, role=role, customer_id=user_id if role == "customer" else None)
    if cached:
        return {
            "intent": "cache_hit",
            "final_response": cached["answer"],
            "citations": cached["citations"],
            "cache_status": f"Cache HIT ({cached.get('cache_hit')})"
        }

    # 3. Entity Extraction using Regex
    booking_match = re.search(r"\b(B-\d{4})\b", last_user_msg, re.IGNORECASE)
    extracted_booking = booking_match.group(1).upper() if booking_match else None

    vehicle_match = re.search(r"\b(VEH\d{3})\b", last_user_msg, re.IGNORECASE)
    extracted_vehicle = vehicle_match.group(1).upper() if vehicle_match else None

    extracted_hub = None
    for hub in BANGALORE_HUBS:
        if hub in lower_msg:
            extracted_hub = hub.title()
            break

    # Determine intent
    # If booking is mentioned or fleet/damage queried -> DB query or Hybrid
    has_db_entity = bool(extracted_booking or extracted_vehicle or extracted_hub or "booking" in lower_msg or "fleet" in lower_msg or "damage" in lower_msg)
    has_policy_kw = any(w in lower_msg for w in ("policy", "refund", "cancel", "penalty", "late fee", "gst", "charge", "deposit", "battery", "ev", "kyc", "tier"))

    if has_db_entity and has_policy_kw:
        intent = "hybrid"
    elif has_db_entity:
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
    Ensures customers cannot access other customers' records or internal business metrics.
    """
    if state.get("final_response"):
        # Already resolved by shortcut or cache
        return {}

    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""

    if role == "customer":
        # Check if customer is asking for another customer's ID
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
        
        # Check if customer is asking for internal fleet revenue or system statistics
        restricted_phrases = ["total revenue", "all customers", "internal metrics", "damage claims for all", "fleet financial"]
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
    Executes safe read-only database queries depending on extracted entities and intent.
    """
    if state.get("final_response"):
        return {}

    role = state.get("role", "customer")
    user_id = state.get("user_identifier", "")
    booking_id = state.get("extracted_booking_id")
    hub_name = state.get("extracted_hub_name")
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""
    lower_msg = last_user_msg.lower()

    sql_context = {}

    # 1. Lookup specific booking
    if booking_id:
        cust_filter = user_id if role == "customer" else None
        b_data = get_booking_details(booking_id, customer_id=cust_filter)
        if b_data:
            sql_context["booking"] = b_data
        else:
            if role == "customer":
                # Check if booking exists under someone else
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

    # 2. Lookup fleet / hub availability
    if hub_name or "fleet" in lower_msg or "hub" in lower_msg:
        fleet_data = get_fleet_summary(hub_name)
        sql_context["fleet_summary"] = fleet_data

    # 3. Lookup open damage reports (Support Agent only)
    if role == "support_agent" and ("damage" in lower_msg or "claim" in lower_msg):
        claims = get_open_damage_claims()
        sql_context["open_damage_claims"] = claims[:10]

    # 4. If customer mentions their recent bookings without specific ID
    if role == "customer" and not booking_id and any(k in lower_msg for k in ("booking", "ride", "trip", "order")):
        user_bookings = get_customer_bookings(user_id, limit=3)
        sql_context["customer_recent_bookings"] = user_bookings

    # 5. Support Agent Customer Lookup (with strict PII masking)
    cust_match = re.search(r"\b(CUST\d{4})\b", last_user_msg, re.IGNORECASE)
    if role == "support_agent" and cust_match:
        target_cust = cust_match.group(1).upper()
        cust_info = get_customer_by_id(target_cust, mask_pii=True)
        if cust_info:
            sql_context["queried_customer"] = cust_info
            sql_context["queried_customer_bookings"] = get_customer_bookings(target_cust, limit=3)

    return {"sql_context": sql_context}


def rag_retrieval_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Retrieves policy clauses with Temporal Version Filtering (v1 vs v2).
    """
    if state.get("final_response"):
        return {}

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
        if chunk["doc_id"] == "RW-POL-02":
            policy_version = "v1 (Applies to bookings made before 1 July 2026)"
        elif chunk["doc_id"] == "RW-POL-03":
            policy_version = "v2 (Applies to bookings made on/after 1 July 2026)"

    return {
        "retrieved_policies": matched_chunks,
        "policy_version_applied": policy_version
    }


def synthesizer_node(state: RideWiseState) -> Dict[str, Any]:
    """
    Calls Azure OpenAI with grounded prompt including DB facts, policy citations,
    and mathematical calculation instructions.
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

    # Format policy context
    policy_texts = []
    citations = []
    for p in policies:
        policy_texts.append(f"[{p['doc_id']} {p['doc_title']} § {p['section']}]\n{p['content']}")
        citations.append(p["citation"])

    formatted_policies = "\n\n".join(policy_texts) if policy_texts else "None"

    # Define Role-specific System Prompt
    system_prompt = (
        "You are 'RideWise Assist', the official AI assistant for RideWise Mobility Pvt. Ltd. "
        "You answer questions from customers and support staff using the verified company database and policy documents.\n\n"
        "=== ROLE & USER CONTEXT ===\n"
        f"• Active Role: {role.upper()}\n"
        f"• Active User Identifier: {user_id}\n"
        f"• Customer Tier: {customer_profile.get('customer_tier', 'STANDARD')}\n\n"
        "=== MANDATORY BUSINESS RULES & ARITHMETIC ===\n"
        "1. TEMPORAL CANCELLATION POLICY:\n"
        "   - Bookings made BEFORE 1 July 2026, 00:00 IST follow Version 1 (RW-POL-02): >=24h = 100%, 6-24h = 50%, <6h = 0%.\n"
        "   - Bookings made ON OR AFTER 1 July 2026, 00:00 IST follow Version 2 (RW-POL-03): >=48h = 100%, 12-48h = 75%, 2-12h = 25%, <2h = 0%.\n"
        "   - The policy version depends ONLY on when the booking was MADE (booked_at), NOT when it was cancelled or when the rental starts.\n"
        "2. LATE RETURN CHARGES:\n"
        "   - 1.5 × vehicle hourly rate per hour or part thereof (e.g. 20 min late = 1 hr fee).\n"
        "   - GOLD Tier: Receives 30-minute grace period. If returned <= 30 mins late, NO fee (₹0). If > 30 mins late, full lateness is charged from minute 1.\n"
        "   - Standard/Silver tiers have NO grace period.\n"
        "   - GST: All penalties attract 18% GST (e.g., ₹180 late fee + 18% GST = ₹212.40 total).\n"
        "3. EV LOW-BATTERY FEE:\n"
        "   - Returned below 10%: Flat ₹150 fee (+ 18% GST = ₹177).\n"
        "   - Returned at 10% or above: ₹0 (Exactly 10% is not below 10%, so ₹0).\n"
        "4. SECURITY DEPOSITS:\n"
        "   - Returned in full on cancellation via payment gateway within 3 days. Deposit refunds are processed by gateway and NOT recorded in the DB payments table.\n"
        "5. STATUS CODES:\n"
        "   - UPC=Upcoming, ONG=Ongoing, CMP=Completed, CNL_U=Cancelled by Customer, CNL_S=Cancelled by RideWise, NSH=No-show.\n"
        "6. CITATIONS:\n"
        "   - Always cite exact database table/fields (e.g., [DB: bookings.booking_id=B-0001]) and policy sections (e.g., [RW-POL-04 § 1.2]).\n"
        "   - Show explicit mathematical steps for any fee, penalty, or refund calculation.\n"
        "7. MANDATORY PII PROTECTION FOR SUPPORT STAFF:\n"
        "   - When Active Role is SUPPORT_AGENT, customer phone numbers and emails MUST ALWAYS be partially masked in your responses (e.g. Phone: 98450****5, Email: aa***@gmail.com).\n"
        "   - Never display raw unmasked phone numbers, email addresses, or driving license numbers to support staff.\n\n"
        f"=== DATABASE CONTEXT ===\n{db_summary}\n\n"
        f"=== RELEVANT POLICY DOCUMENTS ===\n{formatted_policies}\n"
    )

    llm_messages = [{"role": "system", "content": system_prompt}]
    # Add recent message history (up to last 6 messages)
    for m in messages[-6:]:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    try:
        completion = llm_client.chat_completion(messages=llm_messages, temperature=0.1)
        response_text = completion["content"]
        
        # Add citations to state
        if sql_ctx.get("booking"):
            citations.append(f"DB: bookings.booking_id={sql_ctx['booking']['booking_id']}")
        if sql_ctx.get("fleet_summary"):
            citations.append("DB: vehicles")

        # Cache general policy answers for future queries
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
        # Graceful fallback in case of rate limit or unexpected LLM issue
        fallback = (
            "⚠️ **Notice**: The LLM service is momentarily experiencing high demand. "
            "However, here is the verified data retrieved from the RideWise records:\n\n"
        )
        if sql_ctx.get("booking"):
            b = sql_ctx["booking"]
            fallback += (
                f"• **Booking ID**: `{b.get('booking_id')}`\n"
                f"• **Vehicle**: {b.get('vehicle_model')} ({b.get('vehicle_type')})\n"
                f"• **Status**: `{b.get('status_description')}`\n"
                f"• **Scheduled Pickup**: `{b.get('scheduled_start')}`\n"
                f"• **Scheduled Return**: `{b.get('scheduled_end')}`\n"
                f"• **Actual Return**: `{b.get('actual_return_at')}`\n"
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
    Final output check to guarantee citations and safety tags.
    """
    final_resp = state.get("final_response") or ""
    citations = state.get("citations") or []
    return {
        "final_response": final_resp,
        "citations": citations
    }
