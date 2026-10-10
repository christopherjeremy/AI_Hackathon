"""
Streamlit Chat Interface for RideWise Assist
Alternative native chat interface for evaluators preferring Streamlit.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'app' can always be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import uuid
from app.graph.workflow import ridewise_app
from app.database.repository import get_customer_by_id, get_customer_bookings, get_fleet_summary

st.set_page_config(
    page_title="RideWise Assist",
    page_icon="⚡",
    layout="wide"
)

# Initialize session states
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "role" not in st.session_state:
    st.session_state.role = "customer"
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "user_identifier" not in st.session_state:
    st.session_state.user_identifier = None
if "customer_profile" not in st.session_state:
    st.session_state.customer_profile = None

# Sidebar - Compact No-Scroll Layout
with st.sidebar:
    st.subheader("⚡ RideWise Assist")
    st.caption("NeoStats AI Engineer Hackathon")

    role_choice = st.radio(
        "Role:",
        ["Customer", "Support Staff"],
        horizontal=True,
        index=0 if st.session_state.role == "customer" else 1,
        label_visibility="collapsed"
    )

    new_role = "customer" if role_choice == "Customer" else "support_agent"
    if new_role != st.session_state.role:
        st.session_state.role = new_role
        st.session_state.is_authenticated = False
        st.session_state.user_identifier = None
        st.session_state.customer_profile = None
        st.session_state.messages = []
        st.rerun()

    if not st.session_state.is_authenticated:
        if st.session_state.role == "customer":
            col_in, col_btn = st.columns([3, 2])
            with col_in:
                cust_id_input = st.text_input("Customer ID", value="CUST0001", label_visibility="collapsed", placeholder="CUST0001")
            with col_btn:
                auth_clicked = st.button("Log In", use_container_width=True)
            if auth_clicked:
                cust = get_customer_by_id(cust_id_input.strip().upper())
                if cust:
                    st.session_state.is_authenticated = True
                    st.session_state.user_identifier = cust_id_input.strip().upper()
                    st.session_state.customer_profile = cust
                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": f"Hello **{cust['full_name']}**! Authenticated as **{cust['customer_tier']}** tier member."
                    }]
                    st.rerun()
                else:
                    st.error("ID not found (Try CUST0001 - CUST0200)")
        else:
            col_in, col_btn = st.columns([3, 2])
            with col_in:
                staff_name_input = st.text_input("Staff Name", value="Ananya Rao", label_visibility="collapsed", placeholder="Name")
            with col_btn:
                staff_clicked = st.button("Log In", use_container_width=True)
            if staff_clicked:
                st.session_state.is_authenticated = True
                st.session_state.user_identifier = staff_name_input.strip()
                st.session_state.customer_profile = None
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": f"Welcome Operator **{staff_name_input.strip()}**. Global fleet scope enabled."
                }]
                st.rerun()
    else:
        # Compact Session Info
        if st.session_state.role == "customer" and st.session_state.customer_profile:
            p = st.session_state.customer_profile
            st.info(f"👤 **{p['full_name']}** (`{p['customer_id']}`)\n\nTier: **{p['customer_tier']}** | KYC: **{p['kyc_status']}**")
        else:
            st.info(f"🎧 Operator **{st.session_state.user_identifier}**\n\nScope: **Global Fleet & All Hubs**")

        # Action Buttons in a single row
        col_reset, col_logout = st.columns(2)
        with col_reset:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()
        with col_logout:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.is_authenticated = False
                st.session_state.user_identifier = None
                st.session_state.customer_profile = None
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()

# Main Chat Display
st.subheader("RideWise Conversational Operations Desk")


# Display message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "citations" in msg and msg["citations"]:
            with st.expander("📚 Sources & Citations"):
                for c in msg["citations"]:
                    st.code(c)

# Chat Input
if not st.session_state.is_authenticated:
    st.info("👈 Please authenticate in the sidebar with your Customer ID or Staff credentials to start chatting.")
    user_input = None
else:
    user_input = st.chat_input("Ask a question about bookings, refunds, penalties, EV guide...")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)


    # Process through LangGraph
    graph_input = {
        "session_id": st.session_state.session_id,
        "role": st.session_state.role,
        "user_identifier": st.session_state.user_identifier,
        "customer_profile": st.session_state.customer_profile,
        "messages": st.session_state.messages,
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

    with st.spinner("Analyzing operational records and policies..."):
        res = ridewise_app.invoke(graph_input)
        reply = res.get("final_response", "No response generated.")
        citations = res.get("citations", [])
        err_detail = res.get("error_message")

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "citations": citations,
        "error_message": err_detail
    })

    with st.chat_message("assistant"):
        st.markdown(reply)
        if citations:
            with st.expander("📚 Sources & Citations"):
                for c in citations:
                    st.code(c)
        if err_detail:
            with st.expander("⚠️ Diagnostics & Error Log"):
                st.warning(f"Engine Exception: {err_detail}")

