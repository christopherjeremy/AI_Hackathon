"""
FastAPI Backend Application for RideWise Assist
Exposes REST endpoints for authentication, multi-turn chat, session resets,
and serves the GSAP animated frontend.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.database.repository import (
    get_customer_by_id,
    get_customer_bookings,
    get_fleet_summary,
    get_booking_details,
    get_open_damage_claims
)
from app.graph.workflow import ridewise_app
from app.graph.state import RideWiseState

app = FastAPI(
    title="RideWise Assist API",
    description="Production-grade Conversational AI Assistant Backend for RideWise Mobility",
    version="1.0.0"
)

# Enable CORS for cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for multi-turn conversation memory
# Structure: { session_id: { "role": str, "user_identifier": str, "messages": list, "customer_profile": dict } }
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

# ----------------- Request / Response Models -----------------

class LoginRequest(BaseModel):
    role: Literal["customer", "support_agent"]
    customer_id: Optional[str] = Field(None, description="Format: CUST0001 (required for customer)")
    staff_name: Optional[str] = Field(None, description="Staff member name (required for support_agent)")

class LoginResponse(BaseModel):
    success: bool
    role: str
    user_identifier: str
    display_name: str
    customer_profile: Optional[Dict[str, Any]] = None
    session_id: str
    welcome_message: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    citations: List[str]
    intent: Optional[str] = None
    cache_status: Optional[str] = None

class ResetSessionRequest(BaseModel):
    session_id: str

# ----------------- API Endpoints -----------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RideWise Assist API",
        "llm_model": settings.AZURE_OPENAI_MODEL_NAME,
        "database": "connected (read-only)"
    }

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    Authenticates a customer by customer_id or registers support staff by name.
    """
    import uuid
    session_id = str(uuid.uuid4())

    if req.role == "customer":
        if not req.customer_id or not req.customer_id.strip():
            raise HTTPException(status_code=400, detail="Customer ID is required (e.g. CUST0001)")
        
        cid = req.customer_id.strip().upper()
        cust = get_customer_by_id(cid)
        if not cust:
            raise HTTPException(
                status_code=404,
                detail=f"Customer ID '{cid}' not found in RideWise database. Please check and try again (e.g. CUST0001 to CUST0200)."
            )
        
        # Initialize session
        welcome = (
            f"Hello **{cust['full_name']}**! 👋 Welcome back to RideWise.\n"
            f"You are a **{cust['customer_tier']}** tier member (KYC: **{cust['kyc_status']}**).\n"
            "How can I assist you with your rentals, bookings, or policies today?"
        )
        
        SESSION_STORE[session_id] = {
            "role": "customer",
            "user_identifier": cid,
            "display_name": cust["full_name"],
            "customer_profile": cust,
            "messages": [
                {"role": "assistant", "content": welcome}
            ]
        }

        return LoginResponse(
            success=True,
            role="customer",
            user_identifier=cid,
            display_name=cust["full_name"],
            customer_profile=cust,
            session_id=session_id,
            welcome_message=welcome
        )

    else:
        # Support Agent
        staff = req.staff_name.strip() if req.staff_name else "Operations Agent"
        welcome = (
            f"Welcome, **{staff}**! 🎧 **Support Desk Operational Console** is active.\n"
            "You have cross-customer booking lookup, fleet status, and damage claim review access."
        )

        SESSION_STORE[session_id] = {
            "role": "support_agent",
            "user_identifier": staff,
            "display_name": staff,
            "customer_profile": None,
            "messages": [
                {"role": "assistant", "content": welcome}
            ]
        }

        return LoginResponse(
            success=True,
            role="support_agent",
            user_identifier=staff,
            display_name=staff,
            customer_profile=None,
            session_id=session_id,
            welcome_message=welcome
        )

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Processes user message through LangGraph workflow with conversation memory.
    """
    session = SESSION_STORE.get(req.session_id)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please select your role and log in again."
        )

    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Append user message to session history
    session["messages"].append({"role": "user", "content": user_msg})

    # Prepare LangGraph state
    graph_input: RideWiseState = {
        "session_id": req.session_id,
        "role": session["role"],
        "user_identifier": session["user_identifier"],
        "customer_profile": session.get("customer_profile"),
        "messages": session["messages"],
        "intent": None,
        "extracted_booking_id": None,
        "extracted_vehicle_id": None,
        "extracted_hub_name": None,
        "sql_context": None,
        "retrieved_policies": None,
        "policy_version_applied": None,
        "final_response": None,
        "citations": None,
        "cache_status": None,
        "error_message": None
    }

    # Execute LangGraph
    result = ridewise_app.invoke(graph_input)

    ai_reply = result.get("final_response") or "I could not generate an answer. Please rephrase your query."
    citations = result.get("citations") or []

    # Save assistant response to session history
    session["messages"].append({"role": "assistant", "content": ai_reply})

    return ChatResponse(
        session_id=req.session_id,
        response=ai_reply,
        citations=citations,
        intent=result.get("intent"),
        cache_status=result.get("cache_status")
    )

@app.post("/api/chat/reset")
def reset_session(req: ResetSessionRequest):
    """
    Clears session chat history while preserving the authenticated user.
    """
    session = SESSION_STORE.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    welcome = (
        f"Conversation reset. Hello **{session['display_name']}**, how can I assist you?"
    )
    session["messages"] = [{"role": "assistant", "content": welcome}]
    return {"success": True, "session_id": req.session_id, "message": welcome}

@app.get("/api/customer/{customer_id}/bookings")
def get_customer_bookings_api(customer_id: str):
    bookings = get_customer_bookings(customer_id)
    return {"customer_id": customer_id, "bookings": bookings}

@app.get("/api/fleet")
def get_fleet_api(hub_name: Optional[str] = None):
    summary = get_fleet_summary(hub_name)
    return {"fleet": summary}

# ----------------- Frontend Static Files Mounting -----------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "ui"

if (FRONTEND_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "RideWise Assist API is running. Streamlit or Frontend UI can be started."}
