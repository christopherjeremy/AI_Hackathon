"""
LangGraph State Schema for RideWise Assist
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal

class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str

class RideWiseState(TypedDict):
    session_id: str
    role: Literal["customer", "support_agent"]
    user_identifier: str  # customer_id (e.g. CUST0001) or support staff name (e.g. "Ananya Rao")
    customer_profile: Optional[Dict[str, Any]]
    
    # Conversation history
    messages: List[Dict[str, str]]
    
    # Extraction & Routing
    intent: Optional[Literal["shortcut", "cache_hit", "db_query", "policy_rag", "hybrid", "general"]]
    extracted_booking_id: Optional[str]
    extracted_vehicle_id: Optional[str]
    extracted_hub_name: Optional[str]
    extracted_customer_id: Optional[str]
    
    # Tool Execution Context
    sql_context: Optional[Dict[str, Any]]
    retrieved_policies: Optional[List[Dict[str, Any]]]
    policy_version_applied: Optional[str]
    
    # Final Output & Auditing
    final_response: Optional[str]
    citations: Optional[List[str]]
    cache_status: Optional[str]
    error_message: Optional[str]
