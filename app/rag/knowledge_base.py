"""
RideWise Policy Knowledge Base
Pre-processed, structured policy documents with section-level chunking,
metadata tags, and transcriptions of scanned annexures.
"""

from typing import List, Dict, Any

POLICY_CHUNKS: List[Dict[str, Any]] = [
    # ------------------ RW-POL-01: Rental Agreement & Terms ------------------
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "1. Eligibility & Registration",
        "keywords": ["age", "eligibility", "driving licence", "account", "mobile", "email", "minimum age"],
        "content": (
            "Document RW-POL-01 (Version 3.0, Effective 1 January 2025). Section 1: Eligibility. "
            "1.1 The customer must be at least 18 years old and hold a valid driving licence for the class of vehicle booked. "
            "1.2 Each customer may hold one RideWise account, registered with a mobile number and email address."
        )
    },
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "2. KYC Verification",
        "keywords": ["kyc", "verified", "pending", "rejected", "verification", "driving licence status"],
        "content": (
            "Document RW-POL-01 (Version 3.0). Section 2: KYC Verification. "
            "2.1 Every account goes through KYC verification of the driving licence and identity. Three KYC statuses: "
            "(a) VERIFIED: Can book and pick up any vehicle. "
            "(b) PENDING: Can book in advance, but the vehicle is released only after KYC is verified. "
            "(c) REJECTED: Cannot rent. Any existing booking is cancelled by RideWise. "
            "2.2 If KYC is still pending at the scheduled pickup time, or is rejected, RideWise cancels the booking. "
            "A booking cancelled by RideWise is always refunded in full (100%)."
        )
    },
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "3. Hubs, Pickup & Return",
        "keywords": ["hubs", "locations", "bengaluru", "pickup", "return", "minimum rental", "koramangala", "indiranagar", "whitefield", "jayanagar", "hsr layout", "electronic city", "hebbal"],
        "content": (
            "Document RW-POL-01 (Version 3.0). Section 3: Hubs, Pickup and Return. "
            "3.1 Vehicles are picked up from and returned to the same RideWise hub. RideWise operates seven hubs, all in Bengaluru: "
            "Koramangala, Indiranagar, Jayanagar, HSR Layout, Electronic City, Whitefield, and Hebbal. "
            "3.2 The rental period runs from scheduled pickup time to scheduled return time. Rentals are booked in whole hours, with a minimum duration of 2 hours. "
            "3.3 A return after the scheduled return time is a late return and charged under the Late Return & Damage Penalty Schedule."
        )
    },
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "4. Rental Charges, Rates & GST",
        "keywords": ["rental charge", "hourly rate", "daily rate", "gst", "18%", "tax", "cheaper combination", "payment"],
        "content": (
            "Document RW-POL-01 (Version 3.0). Section 4: Rental Charges. "
            "4.1 Each vehicle has an hourly rate and a daily rate (per 24 hours). The rental charge is always the cheaper combination for the booked duration: "
            "every full 24-hour block is charged at the daily rate; and the remaining hours are charged at the hourly rate, but never more than one daily rate. "
            "4.3 GST at 18% is added to rental charges, penalties and fees. When a refund is issued, GST on the refunded amount is refunded in the same proportion. "
            "4.4 Full rental charge is paid when booking is made. A failed payment attempt is not a payment and is never charged."
        )
    },
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "5. Security Deposit & Returns",
        "keywords": ["security deposit", "deposit", "1000", "500", "gateway", "unpaid penalties", "refund"],
        "content": (
            "Document RW-POL-01 (Version 3.0). Section 5: Security Deposit. "
            "5.1 A refundable security deposit may be collected when the booking is made: "
            "(a) Bike / EV bike: ₹1,000 for any rental. "
            "(b) Scooter / EV scooter: ₹500 for rentals of 24 hours or more. "
            "5.2 The deposit is not a rental charge, carries NO GST, and is returned to the original payment method within 3 working days of vehicle return. Unpaid penalties may be recovered from it. "
            "5.3 Deposit returns are processed directly by the payment gateway and are NOT shown in RideWise booking or payment records in the database."
        )
    },
    {
        "doc_id": "RW-POL-01",
        "doc_title": "Rental Agreement & Terms",
        "version": "3.0",
        "effective_date": "2025-01-01",
        "section": "7. No-shows",
        "keywords": ["no-show", "nsh", "pickup delay", "60 minutes", "no refund"],
        "content": (
            "Document RW-POL-01 (Version 3.0). Section 7: No-shows. "
            "7.1 A booking is a no-show (status NSH) when the customer neither picks up the vehicle within 60 minutes of scheduled pickup time nor cancels before scheduled pickup. "
            "7.2 The rental charge for a no-show is NOT refunded. No additional fee is charged for a no-show."
        )
    },

    # ------------------ RW-POL-02: Cancellation Policy v1 ------------------
    {
        "doc_id": "RW-POL-02",
        "doc_title": "Cancellation and Refund Policy (Version 1)",
        "version": "1.0",
        "effective_date": "2025-01-01",
        "section": "Scope & Temporal Applicability (v1)",
        "keywords": ["cancellation policy v1", "version 1", "before 1 july 2026", "booked before", "scope v1"],
        "content": (
            "Document RW-POL-02 (Version 1, Effective 1 January 2025). "
            "Scope: This version applies to bookings MADE BEFORE 1 July 2026, 00:00 IST. "
            "The policy version is determined strictly by when the booking was MADE (booked_at timestamp in UTC/IST), "
            "NOT by when it was cancelled or when the rental starts."
        )
    },
    {
        "doc_id": "RW-POL-02",
        "doc_title": "Cancellation and Refund Policy (Version 1)",
        "version": "1.0",
        "effective_date": "2025-01-01",
        "section": "1. Customer Cancellation Refund Slabs (v1)",
        "keywords": ["cancellation refund", "24 hours", "6 hours", "100%", "50%", "0%", "slabs v1"],
        "content": (
            "Document RW-POL-02 (Version 1). Section 1: Customer Cancellation Refund Slabs (for bookings made before 1 July 2026): "
            "- 24 hours or more before scheduled pickup: 100% refund of rental charge. "
            "- 6 hours or more, but less than 24 hours before scheduled pickup: 50% refund of rental charge. "
            "- Less than 6 hours before scheduled pickup: No refund (0%). "
            "GST on the refunded amount is refunded in the same proportion. Security deposits are returned in full (100%)."
        )
    },
    {
        "doc_id": "RW-POL-02",
        "doc_title": "Cancellation and Refund Policy (Version 1)",
        "version": "1.0",
        "effective_date": "2025-01-01",
        "section": "2-4. RideWise Cancellation, No-shows & Processing (v1)",
        "keywords": ["ridewise cancel", "100%", "processing time", "working days", "refund turnaround"],
        "content": (
            "Document RW-POL-02 (Version 1). Section 2-4: "
            "2. Cancellation by RideWise: Always 100% refund, whatever the timing. "
            "3. No-shows: No refund is given. "
            "4. Refund processing: Refunds are initiated within 3 working days and credited within 5 to 7 working days to the original payment method."
        )
    },

    # ------------------ RW-POL-03: Cancellation Policy v2 ------------------
    {
        "doc_id": "RW-POL-03",
        "doc_title": "Cancellation and Refund Policy (Version 2)",
        "version": "2.0",
        "effective_date": "2026-07-01",
        "section": "Scope & Temporal Applicability (v2)",
        "keywords": ["cancellation policy v2", "version 2", "on or after 1 july 2026", "booked on or after", "scope v2", "new policy"],
        "content": (
            "Document RW-POL-03 (Version 2, Effective 1 July 2026, 00:00 IST). "
            "Scope: Replaces Version 1 for all bookings MADE ON OR AFTER 1 July 2026, 00:00 IST. "
            "Bookings made before that time continue to follow Version 1 (RW-POL-02), even if cancelled after 1 July 2026. "
            "Why it changed: Version 2 introduces a wider full-refund window (48h) and a new partial-refund slab (75% and 25%) so customers cancelling closer to pickup still receive a partial refund."
        )
    },
    {
        "doc_id": "RW-POL-03",
        "doc_title": "Cancellation and Refund Policy (Version 2)",
        "version": "2.0",
        "effective_date": "2026-07-01",
        "section": "Annexure 1: Customer Cancellation Refund Slabs (v2)",
        "keywords": ["cancellation refund v2", "48 hours", "12 hours", "2 hours", "100%", "75%", "25%", "0%", "annexure 1 v2"],
        "content": (
            "Document RW-POL-03 (Version 2). Annexure 1: Approved Refund Schedule (for bookings made on or after 1 July 2026, 00:00 IST): "
            "- 48 hours or more before scheduled pickup: 100% refund of rental charge. "
            "- 12 hours or more, but less than 48 hours before scheduled pickup: 75% refund of rental charge. "
            "- 2 hours or more, but less than 12 hours before scheduled pickup: 25% refund of rental charge. "
            "- Less than 2 hours before scheduled pickup: No refund (0%). "
            "Cancelled by RideWise: 100% refund in all cases. No-shows: No refund. "
            "GST on the refunded amount is refunded in the same proportion. Security deposits are returned in full (100%)."
        )
    },

    # ------------------ RW-POL-04: Late Return & Penalties ------------------
    {
        "doc_id": "RW-POL-04",
        "doc_title": "Late Return & Damage Penalty Schedule",
        "version": "2.1",
        "effective_date": "2025-01-01",
        "section": "1. Late Return Fee Calculation",
        "keywords": ["late return", "penalty", "hourly rate", "1.5x", "lateness", "calculation", "gst 18%"],
        "content": (
            "Document RW-POL-04 (Version 2.1, Effective 1 January 2025). Section 1: Late return fee. "
            "1.1 Lateness is measured from scheduled return time to actual return time. "
            "1.2 Each late hour, or part of an hour, is charged at 1.5 times the vehicle's hourly rate (e.g. 20 minutes late counts as 1 hour; 1 hour 10 minutes late counts as 2 hours). "
            "All penalties attract GST at 18%."
        )
    },
    {
        "doc_id": "RW-POL-04",
        "doc_title": "Late Return & Damage Penalty Schedule",
        "version": "2.1",
        "effective_date": "2025-01-01",
        "section": "Annexure A: Customer Tier Grace Periods",
        "keywords": ["tier benefits", "grace period", "standard", "silver", "gold", "30 minutes", "waiver", "annexure a"],
        "content": (
            "Document RW-POL-04 (Version 2.1). Annexure A: Customer Tier Benefits on Late Return: "
            "- STANDARD tier: None (no grace period). "
            "- SILVER tier: None (no grace period). "
            "- GOLD tier: 30 minutes grace period (up to and including 30 minutes late). "
            "Rules for GOLD tier: "
            "(a) A GOLD return up to and including 30 minutes late incurs NO late fee (₹0). "
            "(b) A GOLD return more than 30 minutes late is charged for the FULL lateness from the first minute, exactly like other tiers (e.g., 35 minutes late = 1 hour charged at 1.5x hourly rate)."
        )
    },
    {
        "doc_id": "RW-POL-04",
        "doc_title": "Late Return & Damage Penalty Schedule",
        "version": "2.1",
        "effective_date": "2025-01-01",
        "section": "1.5 Hourly Rates & Late Fees by Vehicle Model",
        "keywords": ["hourly rate table", "late fee table", "royal enfield", "activa", "ather 450x", "ola s1 pro", "ultraviolette f77", "duke 200", "cb350"],
        "content": (
            "Document RW-POL-04 (Version 2.1). Section 1.5: Hourly Rate & Late Fee per late hour (1.5x) by vehicle model: "
            "• Royal Enfield Classic 350 (Bike): Hourly ₹120, Late fee ₹180/hr. "
            "• Honda CB350 (Bike): Hourly ₹130, Late fee ₹195/hr. "
            "• KTM Duke 200 (Bike): Hourly ₹140, Late fee ₹210/hr. "
            "• Bajaj Pulsar NS200 (Bike): Hourly ₹100, Late fee ₹150/hr. "
            "• Yamaha FZ-S (Bike): Hourly ₹90, Late fee ₹135/hr. "
            "• TVS Apache RTR 160 (Bike): Hourly ₹85, Late fee ₹127.50/hr. "
            "• Honda Activa 6G (Scooter): Hourly ₹60, Late fee ₹90/hr. "
            "• Suzuki Access 125 (Scooter): Hourly ₹60, Late fee ₹90/hr. "
            "• TVS Jupiter (Scooter): Hourly ₹55, Late fee ₹82.50/hr. "
            "• Yamaha Fascino 125 (Scooter): Hourly ₹55, Late fee ₹82.50/hr. "
            "• Honda Dio (Scooter): Hourly ₹55, Late fee ₹82.50/hr. "
            "• Ather 450X (EV scooter): Hourly ₹80, Late fee ₹120/hr. "
            "• Ola S1 Pro (EV scooter): Hourly ₹75, Late fee ₹112.50/hr. "
            "• TVS iQube (EV scooter): Hourly ₹70, Late fee ₹105/hr. "
            "• Bajaj Chetak (EV scooter): Hourly ₹70, Late fee ₹105/hr. "
            "• Revolt RV400 (EV bike): Hourly ₹90, Late fee ₹135/hr. "
            "• Ultraviolette F77 (EV bike): Hourly ₹200, Late fee ₹300/hr. "
            "• Oben Rorr (EV bike): Hourly ₹100, Late fee ₹150/hr."
        )
    },
    {
        "doc_id": "RW-POL-04",
        "doc_title": "Late Return & Damage Penalty Schedule",
        "version": "2.1",
        "effective_date": "2025-01-01",
        "section": "2. EV Low-Battery Charging Fee",
        "keywords": ["low battery", "charging fee", "10%", "150", "flat fee", "ev return", "battery level"],
        "content": (
            "Document RW-POL-04 (Version 2.1). Section 2: EV Low-Battery Charging Fee: "
            "- Battery level below 10%: ₹150 flat fee per rental (+ 18% GST). "
            "- Battery level 10% or above: No fee (₹0). "
            "Note: Exactly 10% is NOT below 10%, so no fee is charged. This fee is separate from and in addition to any late return fee."
        )
    },
    {
        "doc_id": "RW-POL-04",
        "doc_title": "Late Return & Damage Penalty Schedule",
        "version": "2.1",
        "effective_date": "2025-01-01",
        "section": "3. Damage Assessment & Claim Statuses",
        "keywords": ["damage", "claim status", "open", "charged", "disputed", "waived", "lost key", "scratch", "dent"],
        "content": (
            "Document RW-POL-04 (Version 2.1). Section 3: Damage: "
            "3.1 Damage found at return is recorded in a damage report by customer or hub staff, repair cost assessed by hub. "
            "Claim status meanings: "
            "- OPEN: Damage reported; assessment/review in progress. Customer NOT yet charged. "
            "- CHARGED: Assessed cost confirmed and charged to customer. "
            "- DISPUTED: Customer has disputed the claim; under review. NOT charged until resolved. "
            "- WAIVED: RideWise decided not to charge customer (₹0). "
            "3.2 Lost keys are treated as damage and charged at replacement cost."
        )
    },

    # ------------------ RW-POL-05: EV User Guide & FAQ ------------------
    {
        "doc_id": "RW-POL-05",
        "doc_title": "EV User Guide & FAQ",
        "version": "1.4",
        "effective_date": "2025-01-01",
        "section": "1. EV Fleet Specifications & Range",
        "keywords": ["ev range", "battery kwh", "ather 450x", "ola s1 pro", "tvs iqube", "bajaj chetak", "revolt rv400", "oben rorr", "ultraviolette f77"],
        "content": (
            "Document RW-POL-05 (Version 1.4). Section 1: Our Electric Fleet Specifications: "
            "• Ather 450X (EV scooter): Battery 3.7 kWh, Typical Range 105 km, Home full charge 5h 40min. "
            "• Ola S1 Pro (EV scooter): Battery 4.0 kWh, Typical Range 115 km, Home full charge 6h 30min. "
            "• TVS iQube (EV scooter): Battery 3.4 kWh, Typical Range 95 km, Home full charge 4h 30min. "
            "• Bajaj Chetak (EV scooter): Battery 3.2 kWh, Typical Range 100 km, Home full charge 4h 50min. "
            "• Revolt RV400 (EV bike): Battery 3.24 kWh, Typical Range 100 km, Home full charge 4h 30min. "
            "• Oben Rorr (EV bike): Battery 4.4 kWh, Typical Range 130 km, Fast charge 2h. "
            "• Ultraviolette F77 (EV bike): Battery 7.1 kWh, Typical Range 180 km, Home full charge 5h. "
            "Every EV leaves the hub with at least 80% charge."
        )
    },
    {
        "doc_id": "RW-POL-05",
        "doc_title": "EV User Guide & FAQ",
        "version": "1.4",
        "effective_date": "2025-01-01",
        "section": "3. Charging Steps & Hub Charging",
        "keywords": ["how to charge", "charging steps", "hub charging free", "cable", "green light"],
        "content": (
            "Document RW-POL-05 (Version 1.4). Section 3 & Figure 1: Charging Steps: "
            "Step 1: Park at a RideWise hub or approved charger (Charging at a RideWise hub is free). "
            "Step 2: Switch off the vehicle. "
            "Step 3: Connect the RideWise charging cable. "
            "Step 4: Wait for the green light on the dashboard. "
            "Step 5: Unplug and stow the cable under the seat."
        )
    },
    {
        "doc_id": "RW-POL-05",
        "doc_title": "EV User Guide & FAQ",
        "version": "1.4",
        "effective_date": "2025-01-01",
        "section": "5. EV FAQs & Breakdown Support",
        "keywords": ["battery runs out", "breakdown", "towing", "support number", "+91 80 4000 1234", "home charging 15a", "warning light"],
        "content": (
            "Document RW-POL-05 (Version 1.4). Section 5: Frequently Asked Questions: "
            "Q: What happens if battery runs out during trip? "
            "A: Stop safely and call RideWise Support on +91 80 4000 1234. Hub team brings a charged vehicle or tows EV. Towing is free if vehicle had a fault; otherwise recovery charge may apply. "
            "Q: Can I charge at home? "
            "A: Yes. Use only RideWise charging cable supplied under seat, with properly earthed 15A socket. "
            "Q: Dashboard shows battery warning light? "
            "A: Stop riding, switch off vehicle, call RideWise Support. Do not try to open battery compartment."
        )
    }
]
