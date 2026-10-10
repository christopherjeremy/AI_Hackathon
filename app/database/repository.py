import sqlite3
from typing import Dict, List, Optional, Any
from app.database.connection import get_db_connection

# Booking status code mapping to human-friendly descriptions
STATUS_CODE_MAP = {
    "UPC": "Upcoming",
    "ONG": "Ongoing",
    "CMP": "Completed",
    "CNL_U": "Cancelled by customer",
    "CNL_S": "Cancelled by RideWise",
    "NSH": "No-show"
}

def mask_phone(phone: Optional[str]) -> str:
    """Masks phone number: e.g. '9845012345' -> '98450****5'"""
    if not phone:
        return "**********"
    p = str(phone).strip()
    if len(p) >= 7:
        return p[:4] + "****" + p[-2:]
    return p[:2] + "****"

def mask_email(email: Optional[str]) -> str:
    """Masks email address: e.g. 'aarav.sharma@gmail.com' -> 'aa***@gmail.com'"""
    if not email or "@" not in email:
        return "***@***.***"
    parts = email.split("@")
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "***"
    else:
        masked_user = user[:2] + "***" + user[-1]
    return f"{masked_user}@{domain}"

def mask_customer_pii(customer_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Returns a shallow copy of customer dictionary with phone, email and driving licence masked."""
    if not customer_dict:
        return customer_dict
    masked = dict(customer_dict)
    if "phone" in masked:
        masked["phone"] = mask_phone(masked["phone"])
    if "email" in masked:
        masked["email"] = mask_email(masked["email"])
    if "driving_license_no" in masked and masked["driving_license_no"]:
        dl = str(masked["driving_license_no"])
        masked["driving_license_no"] = dl[:4] + "******" + dl[-2:] if len(dl) > 6 else "********"
    return masked

def get_customer_by_id(customer_id: str, mask_pii: bool = False) -> Optional[Dict[str, Any]]:
    """Fetch customer details by customer_id. Optionally masks PII."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id.strip().upper(),))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if mask_pii:
            res = mask_customer_pii(res)
        return res
    finally:
        conn.close()

def search_customers_by_name(name_query: str, mask_pii: bool = False, limit: int = 5) -> List[Dict[str, Any]]:
    """Search customers by full_name substring. Optionally masks PII."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM customers WHERE LOWER(full_name) LIKE ? ORDER BY customer_id LIMIT ?",
            (f"%{name_query.strip().lower()}%", limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if mask_pii:
                d = mask_customer_pii(d)
            results.append(d)
        return results
    finally:
        conn.close()


def get_customer_bookings(customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch all bookings for a given customer with vehicle details."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                b.booking_id,
                b.customer_id,
                b.vehicle_id,
                v.model AS vehicle_model,
                v.vehicle_type,
                v.registration_no,
                v.hub_name,
                v.hourly_rate,
                v.daily_rate,
                b.booked_at,
                b.scheduled_start,
                b.scheduled_end,
                b.actual_return_at,
                b.cancelled_at,
                b.booking_status,
                b.return_battery_pct
            FROM bookings b
            LEFT JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE b.customer_id = ?
            ORDER BY b.booked_at DESC
            LIMIT ?
        """, (customer_id.strip().upper(), limit))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["status_description"] = STATUS_CODE_MAP.get(item["booking_status"], item["booking_status"])
            result.append(item)
        return result
    finally:
        conn.close()

def get_customer_penalties(customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:

    """Fetch all penalties and fines charged to a customer across their bookings."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.payment_id,
                p.booking_id,
                p.payment_type,
                p.amount,
                p.gst_amount,
                (p.amount + COALESCE(p.gst_amount, 0)) AS total_charged,
                p.payment_status,
                p.remarks,
                p.paid_at,
                b.vehicle_id,
                v.model AS vehicle_model
            FROM payments p
            JOIN bookings b ON p.booking_id = b.booking_id
            LEFT JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE b.customer_id = ? AND p.payment_type = 'PENALTY'
            ORDER BY p.paid_at DESC
            LIMIT ?
        """, (customer_id.strip().upper(), limit))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_booking_details(booking_id: str, customer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive details of a booking including payments and damage reports.
    If customer_id is provided, enforces that the booking belongs to this customer.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if customer_id:
            cursor.execute("""
                SELECT 
                    b.*,
                    v.model AS vehicle_model,
                    v.vehicle_type,
                    v.registration_no,
                    v.hub_name,
                    v.hourly_rate,
                    v.daily_rate,
                    v.battery_capacity_kwh,
                    c.full_name AS customer_name,
                    c.customer_tier
                FROM bookings b
                LEFT JOIN vehicles v ON b.vehicle_id = v.vehicle_id
                LEFT JOIN customers c ON b.customer_id = c.customer_id
                WHERE b.booking_id = ? AND b.customer_id = ?
            """, (booking_id.strip().upper(), customer_id.strip().upper()))
        else:
            cursor.execute("""
                SELECT 
                    b.*,
                    v.model AS vehicle_model,
                    v.vehicle_type,
                    v.registration_no,
                    v.hub_name,
                    v.hourly_rate,
                    v.daily_rate,
                    v.battery_capacity_kwh,
                    c.full_name AS customer_name,
                    c.customer_tier
                FROM bookings b
                LEFT JOIN vehicles v ON b.vehicle_id = v.vehicle_id
                LEFT JOIN customers c ON b.customer_id = c.customer_id
                WHERE b.booking_id = ?
            """, (booking_id.strip().upper(),))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        booking_data = dict(row)
        booking_data["status_description"] = STATUS_CODE_MAP.get(booking_data["booking_status"], booking_data["booking_status"])

        # Fetch payments for this booking
        cursor.execute("SELECT * FROM payments WHERE booking_id = ? ORDER BY paid_at ASC", (booking_data["booking_id"],))
        payments = [dict(p) for p in cursor.fetchall()]
        booking_data["payments"] = payments

        # Fetch damage reports for this booking
        cursor.execute("SELECT * FROM damage_reports WHERE booking_id = ?", (booking_data["booking_id"],))
        damages = [dict(d) for d in cursor.fetchall()]
        booking_data["damage_reports"] = damages

        return booking_data
    finally:
        conn.close()

def get_vehicle_by_id(vehicle_id: str) -> Optional[Dict[str, Any]]:
    """Fetch vehicle info by vehicle_id."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_all_customer_penalties_summary(limit: int = 15) -> List[Dict[str, Any]]:
    """Aggregate all penalties and fines customer-wise across the fleet (Support Agent only)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                b.customer_id,
                c.full_name,
                c.customer_tier,
                COUNT(p.payment_id) AS penalty_count,
                SUM(p.amount) AS total_penalty_ex_gst,
                SUM(COALESCE(p.gst_amount, 0)) AS total_gst,
                SUM(p.amount + COALESCE(p.gst_amount, 0)) AS total_charged
            FROM payments p
            JOIN bookings b ON p.booking_id = b.booking_id
            JOIN customers c ON b.customer_id = c.customer_id
            WHERE p.payment_type = 'PENALTY'
            GROUP BY b.customer_id, c.full_name, c.customer_tier
            ORDER BY total_charged DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_customers_by_kyc_status(kyc_status: str = "PENDING", mask_pii: bool = True, limit: int = 25) -> List[Dict[str, Any]]:
    """Fetch customers by KYC verification status (Support Agent only)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT customer_id, full_name, phone, email, city, kyc_status, customer_tier, created_at
            FROM customers
            WHERE UPPER(kyc_status) = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (kyc_status.strip().upper(), limit))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if mask_pii:
                d = mask_customer_pii(d)
            results.append(d)
        return results
    finally:
        conn.close()


def get_fleet_summary(hub_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch vehicle availability summary across hubs."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if hub_name:
            cursor.execute("""
                SELECT hub_name, vehicle_type, status, count(*) AS count
                FROM vehicles
                WHERE LOWER(hub_name) = LOWER(?)
                GROUP BY hub_name, vehicle_type, status
            """, (hub_name.strip(),))
        else:
            cursor.execute("""
                SELECT hub_name, vehicle_type, status, count(*) AS count
                FROM vehicles
                GROUP BY hub_name, vehicle_type, status

                ORDER BY hub_name, vehicle_type
            """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_open_damage_claims() -> List[Dict[str, Any]]:
    """Fetch all open or disputed damage claims (Support Agent only)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.*,
                b.customer_id,
                v.model AS vehicle_model,
                v.registration_no
            FROM damage_reports d
            LEFT JOIN bookings b ON d.booking_id = b.booking_id
            LEFT JOIN vehicles v ON d.vehicle_id = v.vehicle_id
            WHERE d.claim_status IN ('OPEN', 'DISPUTED')
            ORDER BY d.reported_at DESC
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def execute_readonly_sql(sql_query: str, role: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a validated read-only SQL query with strict RBAC enforcement.
    Blocks any modifying statements.
    For customers, restricts queries so they cannot inspect unauthorized data.
    """
    # Strict validation
    cleaned_sql = sql_query.strip()
    first_token = cleaned_sql.split()[0].upper() if cleaned_sql else ""
    if first_token not in ("SELECT", "WITH", "EXPLAIN"):
        return {"error": "Security Alert: Only SELECT queries are permitted on this database."}
    
    forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH", "PRAGMA"]
    upper_sql = cleaned_sql.upper()
    for kw in forbidden_keywords:
        # Check whole word match
        if f" {kw} " in f" {upper_sql} ":
            return {"error": f"Security Alert: Disallowed operation '{kw}' detected."}

    # RBAC Enforcement for Customer
    if role == "customer":
        if not customer_id:
            return {"error": "Authentication required for customer queries."}
        # Customer cannot query entire customer table or fleet operational internal aggregates
        if "FROM CUSTOMERS" in upper_sql and f"'{customer_id.upper()}'" not in upper_sql:
            return {"error": "Access Denied: You may only query your own customer record."}

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(cleaned_sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        # Cap row output to prevent context window explosion
        max_rows = 25
        result_rows = [dict(zip(cols, r)) for r in rows[:max_rows]]
        # Mask PII for support staff
        if role == "support_agent":
            for row_dict in result_rows:
                if "phone" in row_dict and row_dict["phone"]:
                    row_dict["phone"] = mask_phone(row_dict["phone"])
                if "email" in row_dict and row_dict["email"]:
                    row_dict["email"] = mask_email(row_dict["email"])
                if "driving_license_no" in row_dict and row_dict["driving_license_no"]:
                    dl = str(row_dict["driving_license_no"])
                    row_dict["driving_license_no"] = dl[:4] + "******" + dl[-2:] if len(dl) > 6 else "********"
        return {
            "columns": cols,
            "rows": result_rows,
            "total_count": len(rows),
            "truncated": len(rows) > max_rows
        }
    except Exception as e:
        return {"error": f"SQL Execution error: {str(e)}"}
    finally:
        conn.close()
