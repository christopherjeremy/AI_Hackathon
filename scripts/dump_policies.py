import pypdf
import glob
import os
import json

policies = [
    ("01_Rental_Agreement_and_Terms.pdf", "RW-POL-01", "Rental Agreement & Terms", "3.0", "2025-01-01"),
    ("02_Cancellation_and_Refund_Policy_v1.pdf", "RW-POL-02", "Cancellation and Refund Policy v1", "1.0", "2025-01-01"),
    ("03_Cancellation_and_Refund_Policy_v2.pdf", "RW-POL-03", "Cancellation and Refund Policy v2", "2.0", "2026-07-01"),
    ("04_Late_Return_and_Damage_Penalty_Schedule.pdf", "RW-POL-04", "Late Return and Damage Penalty Schedule", "2.1", "2025-01-01"),
    ("05_EV_User_Guide_and_FAQ.pdf", "RW-POL-05", "EV User Guide & FAQ", "1.4", "2025-01-01")
]

for filename, doc_id, title, version, eff_date in policies:
    path = os.path.join("Neostats Hackathon AI Usecase", filename)
    reader = pypdf.PdfReader(path)
    full_text = ""
    for page_idx, p in enumerate(reader.pages):
        full_text += f"\n--- Page {page_idx+1} ---\n" + p.extract_text()
    
    out_path = os.path.join("scripts", f"{doc_id}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"DOC_ID: {doc_id}\nTITLE: {title}\nVERSION: {version}\nEFFECTIVE: {eff_date}\n\n")
        f.write(full_text)
    print(f"Dumped {doc_id}: {len(full_text)} characters")
