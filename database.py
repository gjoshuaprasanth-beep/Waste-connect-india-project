"""
WasteConnect India - SQLite Database Layer & Seed Data
Supports:
1. Hospital (Bio-Medical Waste Management Rules 2016)
2. Pharmaceutical Manufacturing (Hazardous & Other Wastes Rules 2016)
3. Authorized Waste Management Providers (CBWTF & TSDF facilities)
4. Platform Administrator (Compliance, Verification & Audit)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wasteconnect.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Organizations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        org_type TEXT NOT NULL, -- 'hospital', 'pharma', 'provider', 'admin'
        reg_number TEXT NOT NULL, -- SPCB CTO / NABH / Factory License
        state TEXT NOT NULL,
        city TEXT NOT NULL,
        address TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        contact_phone TEXT NOT NULL,
        authorized_waste_types TEXT NOT NULL, -- JSON array
        verification_status TEXT NOT NULL DEFAULT 'verified', -- 'verified', 'pending', 'suspended'
        spcb_license_expiry TEXT,
        daily_capacity_mt REAL DEFAULT 0,
        compliance_rating REAL DEFAULT 4.8,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL, -- 'hospital_admin', 'pharma_manager', 'provider_operator', 'platform_admin'
        org_id TEXT NOT NULL,
        designation TEXT NOT NULL,
        phone TEXT NOT NULL,
        avatar TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (org_id) REFERENCES organizations(id)
    );
    """)

    # 3. Collection Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collection_requests (
        id TEXT PRIMARY KEY,
        generator_org_id TEXT NOT NULL,
        generator_type TEXT NOT NULL, -- 'hospital', 'pharma'
        assigned_provider_id TEXT,
        request_type TEXT NOT NULL, -- 'biomedical', 'pharma_hazardous'
        waste_category TEXT NOT NULL,
        waste_description TEXT NOT NULL,
        estimated_quantity_kg REAL NOT NULL,
        actual_collected_quantity_kg REAL,
        packaging_type TEXT NOT NULL,
        pickup_location TEXT NOT NULL,
        gps_coordinates TEXT,
        preferred_date TEXT NOT NULL,
        scheduled_date TEXT,
        transporter_name TEXT,
        vehicle_number TEXT,
        driver_name TEXT,
        driver_phone TEXT,
        status TEXT NOT NULL, -- Draft, Submitted, Under Review, Accepted, Scheduled, Collected, Received at Facility, Closed, Rejected, Disputed
        status_reason TEXT,
        hazard_details TEXT, -- JSON with chemical composition, UN number, flash point
        manifest_number TEXT,
        treatment_method TEXT,
        created_by_user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (generator_org_id) REFERENCES organizations(id),
        FOREIGN KEY (assigned_provider_id) REFERENCES organizations(id),
        FOREIGN KEY (created_by_user_id) REFERENCES users(id)
    );
    """)

    # 4. Status History Table (Audit of Request Lifecycle)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS request_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changed_by_user_id TEXT NOT NULL,
        changed_by_name TEXT NOT NULL,
        comment TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (request_id) REFERENCES collection_requests(id)
    );
    """)

    # 5. Messages Table (Request-Specific Message Center)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        sender_user_id TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        sender_org_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message_text TEXT NOT NULL,
        attachment_name TEXT,
        attachment_url TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (request_id) REFERENCES collection_requests(id)
    );
    """)

    # 6. Documents Table (Manifests, MSDS, TREMCARD, Weight Slips)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_size TEXT NOT NULL,
        uploaded_by_org TEXT NOT NULL,
        verification_status TEXT NOT NULL DEFAULT 'verified',
        created_at TEXT NOT NULL,
        FOREIGN KEY (request_id) REFERENCES collection_requests(id)
    );
    """)

    # 7. Audit Logs Table (Admin Security & Regulatory Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        org_name TEXT NOT NULL,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    conn.commit()
    seed_initial_data(conn)
    conn.close()
    print("Database initialized successfully at", DB_PATH)

def seed_initial_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM organizations;")
    if cursor.fetchone()[0] > 0:
        return # Data already seeded

    now = datetime.now()
    t_now = now.strftime("%Y-%m-%d %H:%M:%S")
    d_today = now.strftime("%Y-%m-%d")
    d_yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    d_tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    d_nextweek = (now + timedelta(days=5)).strftime("%Y-%m-%d")

    # --- SEED ORGANIZATIONS ---
    orgs = [
        # Hospital Generator
        (
            "ORG-HOSP-001",
            "Apollo Multispeciality Hospital",
            "hospital",
            "SPCB/BMW/DL/2022/9481",
            "Delhi",
            "New Delhi",
            "Sarita Vihar, Mathura Road, New Delhi 110076",
            "compliance@apollohospitals-delhi.com",
            "+91 11 2692 5858",
            json.dumps(["BMW-Yellow-Anatomical", "BMW-Red-Plastic", "BMW-White-Sharps", "BMW-Blue-Glass"]),
            "verified",
            "2028-12-31",
            0.8,
            4.9,
            t_now
        ),
        (
            "ORG-HOSP-002",
            "Manipal Super Specialty Hospital",
            "hospital",
            "KSPCB/BMW/KA/2021/4120",
            "Karnataka",
            "Bengaluru",
            "98 HAL Old Airport Road, Kodihalli, Bengaluru 560017",
            "ehs@manipalhospitals.com",
            "+91 80 2502 4444",
            json.dumps(["BMW-Yellow-Anatomical", "BMW-Red-Plastic", "BMW-White-Sharps", "BMW-Blue-Glass"]),
            "verified",
            "2027-09-30",
            0.6,
            4.8,
            t_now
        ),
        # Pharmaceutical Manufacturing Generator
        (
            "ORG-PHARM-001",
            "SunCure Pharmaceuticals API Plant",
            "pharma",
            "GPCB/HAZ/GJ/2023/1104",
            "Gujarat",
            "Dahej",
            "Plot No. Z-44, SEZ Industrial Estate, Dahej, Bharuch 392130",
            "regulatory@suncurepharma.com",
            "+91 2641 258900",
            json.dumps(["HAZ-Pharma-Solvent", "HAZ-Pharma-API-Reject", "HAZ-Pharma-ETP-Sludge", "HAZ-Pharma-Cytotoxic", "HAZ-Pharma-Contaminated-PPE"]),
            "verified",
            "2029-03-31",
            12.5,
            4.95,
            t_now
        ),
        (
            "ORG-PHARM-002",
            "Biocon Biosimilar Manufacturing Unit 3",
            "pharma",
            "KSPCB/IND/KA/2020/7892",
            "Karnataka",
            "Bengaluru",
            "20th KM Hosur Road, Electronic City, Bengaluru 560100",
            "waste.mgmt@biocon.com",
            "+91 80 2808 2808",
            json.dumps(["HAZ-Pharma-Solvent", "HAZ-Pharma-API-Reject", "HAZ-Pharma-ETP-Sludge"]),
            "verified",
            "2028-06-30",
            8.0,
            4.7,
            t_now
        ),
        # Waste Management Providers
        (
            "ORG-PROV-001",
            "EcoClean BioMed Solutions CBWTF",
            "provider",
            "DPCC/CBWTF/DL/2019/008",
            "Delhi",
            "New Delhi",
            "Okhla Industrial Area Phase-I, New Delhi 110020",
            "ops@ecocleanbiomed.in",
            "+91 11 4160 3322",
            json.dumps(["BMW-Yellow-Anatomical", "BMW-Red-Plastic", "BMW-White-Sharps", "BMW-Blue-Glass"]),
            "verified",
            "2027-11-15",
            15.0,
            4.92,
            t_now
        ),
        (
            "ORG-PROV-002",
            "Gujarat Enviro Haz-Waste TSDF Ltd",
            "provider",
            "GPCB/TSDF/GJ/2018/042",
            "Gujarat",
            "Dahej",
            "Plot 18/B GIDC Petrochemical Complex, Dahej 392130",
            "dispatch@gujendatenviro.com",
            "+91 2641 229100",
            json.dumps(["HAZ-Pharma-Solvent", "HAZ-Pharma-API-Reject", "HAZ-Pharma-ETP-Sludge", "HAZ-Pharma-Contaminated-PPE"]),
            "verified",
            "2030-05-20",
            75.0,
            4.88,
            t_now
        ),
        (
            "ORG-PROV-003",
            "Apex Green Medical & Industrial TSDF",
            "provider",
            "MPCB/MULTI/MH/2024/099",
            "Maharashtra",
            "Navi Mumbai",
            "TTC Industrial Area, MIDC Mahape, Navi Mumbai 400710",
            "contact@apexgreen.in",
            "+91 22 2778 1199",
            json.dumps(["BMW-Yellow-Anatomical", "BMW-Red-Plastic", "HAZ-Pharma-Solvent", "HAZ-Pharma-API-Reject"]),
            "pending", # Provider pending regulatory verification
            "2026-12-31",
            25.0,
            4.5,
            t_now
        ),
        # Platform Administrator Organization
        (
            "ORG-ADMIN-001",
            "WasteConnect India Central Compliance Directorate",
            "admin",
            "GOI/MOEFCC/TECH/2025/WC-01",
            "Delhi",
            "New Delhi",
            "Paryavaran Bhawan, CGO Complex, Lodhi Road, New Delhi 110003",
            "admin@wasteconnect.in",
            "+91 11 2436 0000",
            json.dumps(["ALL_CATEGORIES_MONITORING"]),
            "verified",
            "2035-12-31",
            999.0,
            5.0,
            t_now
        )
    ]

    cursor.executemany("""
    INSERT INTO organizations (id, name, org_type, reg_number, state, city, address, contact_email, contact_phone, authorized_waste_types, verification_status, spcb_license_expiry, daily_capacity_mt, compliance_rating, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orgs)

    # --- SEED USERS ---
    users = [
        (
            "USER-HOSP-001",
            "anita.rao@apollo.com",
            "demo123",
            "Dr. Anita Rao",
            "hospital_admin",
            "ORG-HOSP-001",
            "Chief Medical Superintendent & EHS Lead",
            "+91 98112 34567",
            "👩‍⚕️",
            t_now
        ),
        (
            "USER-PHARM-001",
            "rajesh.sharma@suncure.com",
            "demo123",
            "Rajesh Sharma",
            "pharma_manager",
            "ORG-PHARM-001",
            "Senior VP - EHS & Industrial Waste Operations",
            "+91 98250 88991",
            "👨‍🔬",
            t_now
        ),
        (
            "USER-PROV-001",
            "vikram.mehra@ecoclean.in",
            "demo123",
            "Vikram Mehra",
            "provider_operator",
            "ORG-PROV-001",
            "Operations Director - CBWTF Logistics",
            "+91 98101 22334",
            "🚛",
            t_now
        ),
        (
            "USER-PROV-002",
            "sunita.patel@gujendatenviro.com",
            "demo123",
            "Sunita Patel",
            "provider_operator",
            "ORG-PROV-002",
            "Plant Manager & TSDF Incineration In-Charge",
            "+91 97240 55667",
            "🏭",
            t_now
        ),
        (
            "USER-ADMIN-001",
            "arjun.nambiar@wasteconnect.in",
            "demo123",
            "Arjun Nambiar",
            "platform_admin",
            "ORG-ADMIN-001",
            "National Compliance & Regulatory Auditor",
            "+91 99990 11223",
            "🛡️",
            t_now
        )
    ]

    cursor.executemany("""
    INSERT INTO users (id, email, password_hash, full_name, role, org_id, designation, phone, avatar, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users)

    # --- SEED COLLECTION REQUESTS ---
    requests = [
        # 1. Hospital - Completed Biomedical Request
        (
            "REQ-2026-0814",
            "ORG-HOSP-001",
            "hospital",
            "ORG-PROV-001",
            "biomedical",
            "BMW-Yellow-Anatomical",
            "Pathological tissues, soiled surgical dressings, and discarded cotton swabs from OT 1 & 4",
            124.5,
            122.8,
            "Barcoded Non-Chlorinated Biohazard Yellow Bags (50 Micron)",
            "Apollo Hospital Delhi, Central Biomedical Holding Cell Basement-2",
            "28.5355° N, 77.2910° E",
            d_yesterday,
            d_yesterday,
            "EcoClean Dedicated BioMed Logistics",
            "DL-1L-AA-4019 (GPS Tracked)",
            "Kishan Lal",
            "+91 98711 00223",
            "Closed",
            "Treatment completed via high-temperature incineration chamber #2 at 1050°C. Ash sampled and logged.",
            json.dumps({"autoclave_batch": "AC-2026-992", "incinerator_temp_c": 1055, "barcode_verified": True}),
            "CPCB-BMW-2026-9921",
            "High-Temperature Dual-Chamber Incineration",
            "USER-HOSP-001",
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 2. Hospital - In Transit / Collected
        (
            "REQ-2026-0819",
            "ORG-HOSP-001",
            "hospital",
            "ORG-PROV-001",
            "biomedical",
            "BMW-Red-Plastic",
            "Autoclaved disposable syringes without needles, IV bottles, tubing, catheters and gloves",
            86.0,
            88.2,
            "Red Non-Chlorinated Autoclavable Puncture-Resistant Polybags",
            "Apollo Hospital Delhi, Ward Block C Biomedical Chute Room",
            "28.5355° N, 77.2910° E",
            d_today,
            d_today,
            "EcoClean Dedicated BioMed Logistics",
            "DL-1L-AA-4019 (GPS Tracked)",
            "Kishan Lal",
            "+91 98711 00223",
            "Collected",
            "Pickup weighed at generator facility gate. Manifest signed digitally. Vehicle en-route to Okhla CBWTF.",
            json.dumps({"barcode_count": 14, "pre_treatment_autoclave": "Completed at generator"}),
            "CPCB-BMW-2026-9984",
            "Autoclaving & Shredding for Polymer Recycling",
            "USER-HOSP-001",
            (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 3. Hospital - Scheduled for tomorrow
        (
            "REQ-2026-0822",
            "ORG-HOSP-001",
            "hospital",
            "ORG-PROV-001",
            "biomedical",
            "BMW-White-Sharps",
            "Contaminated needles, scalpels, surgical blades and lancets in puncture-proof translucent containers",
            34.0,
            None,
            "Tamper-Proof Translucent White Puncture & Leak-Proof Containers",
            "Apollo Hospital Delhi, Central Biomedical Storage Unit",
            "28.5355° N, 77.2910° E",
            d_tomorrow,
            d_tomorrow,
            "EcoClean Dedicated BioMed Logistics",
            "DL-1L-BB-5521",
            "Ramesh Chandra",
            "+91 98110 99441",
            "Scheduled",
            "Assigned to EcoClean morning route 4B. Barcode scans confirmed.",
            json.dumps({"sharps_container_count": 8, "tamper_evident_seal": "Verified"}),
            "CPCB-BMW-2026-1002",
            "Encapsulation / Dry Heat Sterilization & Shredding",
            "USER-HOSP-001",
            (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 4. Hospital - Submitted (Pending Provider Review)
        (
            "REQ-2026-0825",
            "ORG-HOSP-001",
            "hospital",
            "ORG-PROV-001",
            "biomedical",
            "BMW-Blue-Glass",
            "Broken ampoules, antibiotic vials, expired saline glassware, metallic orthopedic implants",
            42.0,
            None,
            "Cardboard Box with Blue Puncture-Resistant Inner Lining",
            "Apollo Hospital Delhi, Gate 3 Waste Sorting Room",
            "28.5355° N, 77.2910° E",
            d_nextweek,
            None,
            None,
            None,
            None,
            None,
            "Submitted",
            "Hospital submitted new batch request. Awaiting CBWTF schedule acceptance.",
            json.dumps({"glassware_disinfected": "1% Sodium Hypochlorite wash"}),
            "CPCB-BMW-2026-1019",
            "Disinfection & Glass Recycling",
            "USER-HOSP-001",
            (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 5. Pharma - Closed / Treated Hazardous Waste
        (
            "REQ-2026-0810",
            "ORG-PHARM-001",
            "pharma",
            "ORG-PROV-002",
            "pharma_hazardous",
            "HAZ-Pharma-Solvent",
            "Distillation solvent residue containing spent Dichloromethane (DCM) and Acetone from Metformin API synthesis",
            3200.0,
            3240.0,
            "UN-Standard 200L Mild Steel Epoxy-Coated Closed-Head Drums (16 Drums)",
            "SunCure Dahej SEZ, Tank Farm Yard Bay 4",
            "21.7142° N, 72.5898° E",
            d_yesterday,
            d_yesterday,
            "Gujarat Enviro HazMat Transporters (SPCB Authorized)",
            "GJ-06-AZ-9912 (HazChem Class 3)",
            "Bhavin Jadeja",
            "+91 94270 11982",
            "Closed",
            "Thermal co-processing achieved in cement kiln at 1450°C. Form 10 closed and signed by TSDF In-charge.",
            json.dumps({"flash_point_c": 18, "un_number": "UN 1993", "hazchem_code": "3WE", "msds_attached": True, "calorific_value_kcal_kg": 4200}),
            "FORM10-HAZ-2026-4412",
            "Co-Processing in Cement Kiln / High Temp Incineration",
            "USER-PHARM-001",
            (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 6. Pharma - Received at Facility (Weighbridge Verified)
        (
            "REQ-2026-0816",
            "ORG-PHARM-001",
            "pharma",
            "ORG-PROV-002",
            "pharma_hazardous",
            "HAZ-Pharma-API-Reject",
            "Off-specification ciprofloxacin active pharmaceutical ingredient batches, expired trial intermediates",
            750.0,
            745.0,
            "UN Certified Composite Intermediate Bulk Container (IBC) Totes",
            "SunCure Dahej SEZ, HazWaste Storage Shed 2",
            "21.7142° N, 72.5898° E",
            d_today,
            d_today,
            "Gujarat Enviro HazMat Transporters",
            "GJ-06-AZ-9912",
            "Bhavin Jadeja",
            "+91 94270 11982",
            "Received at Facility",
            "Arrived at Dahej TSDF weighbridge slip #99014. Undergoing laboratory verification before rotary kiln charging.",
            json.dumps({"un_number": "UN 3249", "toxicity_class": "Class 6.1 Toxic", "msds_attached": True}),
            "FORM10-HAZ-2026-4488",
            "Rotary Kiln Incineration at 1200°C",
            "USER-PHARM-001",
            (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 7. Pharma - Under Review / Acceptance Pending
        (
            "REQ-2026-0828",
            "ORG-PHARM-001",
            "pharma",
            "ORG-PROV-002",
            "pharma_hazardous",
            "HAZ-Pharma-ETP-Sludge",
            "Dewatered biological sludge cake from biological effluent treatment plant (ETP), heavy metal traces",
            4800.0,
            None,
            "HDPE High-Density Jumbo Bags on Heavy Duty Wooden Pallets (8 Bags)",
            "SunCure Dahej SEZ, ETP Sludge Dewatering Yard",
            "21.7142° N, 72.5898° E",
            d_nextweek,
            None,
            None,
            None,
            None,
            None,
            "Under Review",
            "TSDF reviewing chemical leachate analysis report for Secured Landfill (SLF) cell compatibility.",
            json.dumps({"moisture_pct": 32, "heavy_metals_ppm": {"Pb": 12, "Cd": 2, "Cr": 8}, "landfill_cell": "SLF Cell 4"}),
            "FORM10-HAZ-2026-4501",
            "Direct Secured Landfill (TSDF SLF Cell)",
            "USER-PHARM-001",
            (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        ),
        # 8. Pharma - Disputed / Exceptional Case (Quantity Discrepancy)
        (
            "REQ-2026-0808",
            "ORG-PHARM-001",
            "pharma",
            "ORG-PROV-002",
            "pharma_hazardous",
            "HAZ-Pharma-Cytotoxic",
            "Discarded oncology therapeutic intermediates & contaminated filter media",
            600.0,
            490.0,
            "Double-Lined Purple UN-Approved Hazardous Drums",
            "SunCure Dahej SEZ, High Potency Isolation Facility",
            "21.7142° N, 72.5898° E",
            (now - timedelta(days=4)).strftime("%Y-%m-%d"),
            (now - timedelta(days=4)).strftime("%Y-%m-%d"),
            "Gujarat Enviro HazMat Transporters",
            "GJ-06-BY-1102",
            "Dinesh Solanki",
            "+91 98980 44221",
            "Disputed",
            "Weighbridge reported 490 kg vs Generator estimated 600 kg. Re-calibration audit requested before Form 10 signoff.",
            json.dumps({"dispute_type": "Quantity Mismatch > 15%", "flagged_by": "System Auto-Audit"}),
            "FORM10-HAZ-2026-4390",
            "Plasma Gasification / Hazardous Incineration",
            "USER-PHARM-001",
            (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            t_now
        )
    ]

    cursor.executemany("""
    INSERT INTO collection_requests (
        id, generator_org_id, generator_type, assigned_provider_id, request_type, waste_category,
        waste_description, estimated_quantity_kg, actual_collected_quantity_kg, packaging_type,
        pickup_location, gps_coordinates, preferred_date, scheduled_date, transporter_name,
        vehicle_number, driver_name, driver_phone, status, status_reason, hazard_details,
        manifest_number, treatment_method, created_by_user_id, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, requests)

    # --- SEED REQUEST STATUS HISTORY ---
    history = [
        ("REQ-2026-0814", "Draft", "Submitted", "USER-HOSP-001", "Dr. Anita Rao", "Biomedical request initiated with CPCB barcode series.", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0814", "Submitted", "Accepted", "USER-PROV-001", "Vikram Mehra", "EcoClean verified yellow category & accepted slot.", (now - timedelta(days=2, hours=-2)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0814", "Accepted", "Scheduled", "USER-PROV-001", "Vikram Mehra", "Vehicle DL-1L-AA-4019 assigned for 09:30 AM pickup.", (now - timedelta(days=1, hours=20)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0814", "Scheduled", "Collected", "USER-PROV-001", "Vikram Mehra", "Weighed 122.8 kg at Apollo basement cell. Barcode scanned.", (now - timedelta(days=1, hours=14)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0814", "Collected", "Received at Facility", "USER-PROV-001", "Vikram Mehra", "Consignment arrived at Okhla CBWTF weighbridge.", (now - timedelta(days=1, hours=10)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0814", "Received at Facility", "Closed", "USER-PROV-001", "Vikram Mehra", "Incineration completed at 1050°C. Destruction Certificate issued.", t_now),

        ("REQ-2026-0819", "Draft", "Submitted", "USER-HOSP-001", "Dr. Anita Rao", "Submitted red bag recyclable biomedical plastic request.", (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0819", "Submitted", "Accepted", "USER-PROV-001", "Vikram Mehra", "Slot accepted by CBWTF dispatch.", (now - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0819", "Accepted", "Scheduled", "USER-PROV-001", "Vikram Mehra", "Dispatched vehicle DL-1L-AA-4019.", (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0819", "Scheduled", "Collected", "USER-PROV-001", "Vikram Mehra", "Collected 88.2 kg. Barcode verification complete.", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),

        ("REQ-2026-0816", "Draft", "Submitted", "USER-PHARM-001", "Rajesh Sharma", "Submitted hazardous API reject consignment with MSDS.", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0816", "Submitted", "Accepted", "USER-PROV-002", "Sunita Patel", "Gujarat Enviro validated HazChem profile.", (now - timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0816", "Accepted", "Scheduled", "USER-PROV-002", "Sunita Patel", "Transporter GJ-06-AZ-9912 deployed.", (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0816", "Scheduled", "Collected", "USER-PROV-002", "Sunita Patel", "Gate weighbridge reading 745 kg. Form 10 Copy 2 signed.", (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
        ("REQ-2026-0816", "Collected", "Received at Facility", "USER-PROV-002", "Sunita Patel", "Consignment logged at TSDF gate. Awaiting rotary kiln queue.", t_now)
    ]

    cursor.executemany("""
    INSERT INTO request_status_history (request_id, old_status, new_status, changed_by_user_id, changed_by_name, comment, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, history)

    # --- SEED MESSAGES ---
    messages = [
        (
            "MSG-001",
            "REQ-2026-0814",
            "USER-HOSP-001",
            "Dr. Anita Rao",
            "Apollo Multispeciality Hospital",
            "hospital_admin",
            "Please ensure driver brings the certified electronic weighing scale for baseline check at basement storage.",
            None,
            None,
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-002",
            "REQ-2026-0814",
            "USER-PROV-001",
            "Vikram Mehra",
            "EcoClean BioMed Solutions CBWTF",
            "provider_operator",
            "Understood Dr. Rao. Our driver Kishan Lal has the SPCB-calibrated Bluetooth scale and barcode reader handy.",
            "SPCB_Scale_Calibration_Cert.pdf",
            "/docs/scale-cert.pdf",
            (now - timedelta(days=2, hours=-1)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-003",
            "REQ-2026-0814",
            "USER-PROV-001",
            "Vikram Mehra",
            "EcoClean BioMed Solutions CBWTF",
            "provider_operator",
            "Pickup completed successfully. Total net weight 122.8 kg recorded. Incinerator chamber #2 scheduled for tonight.",
            "Weight_Slip_APOLLO_0814.pdf",
            "/docs/weight-slip.pdf",
            (now - timedelta(days=1, hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-004",
            "REQ-2026-0810",
            "USER-PHARM-001",
            "Rajesh Sharma",
            "SunCure Pharmaceuticals API Plant",
            "pharma_manager",
            "The 16 solvent drums are grounded and nitrogen-blanketed in Bay 4. TREMCARD Form 9 is attached.",
            "TREMCARD_Solvent_Mixture.pdf",
            "/docs/tremcard.pdf",
            (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-005",
            "REQ-2026-0810",
            "USER-PROV-002",
            "Sunita Patel",
            "Gujarat Enviro Haz-Waste TSDF Ltd",
            "provider_operator",
            "Solvent profile tested in TSDF lab. Calorific value is 4200 kcal/kg, ideal for co-processing. Cement kiln dispatch confirmed.",
            "TSDF_Lab_Fingerprint_Analysis.pdf",
            "/docs/lab-analysis.pdf",
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-006",
            "REQ-2026-0808",
            "USER-PROV-002",
            "Sunita Patel",
            "Gujarat Enviro Haz-Waste TSDF Ltd",
            "provider_operator",
            "Discrepancy noted: Factory weighment showed 600 kg, but TSDF incoming weighbridge shows 490 kg gross tare difference. Requesting joint audit.",
            "Weighbridge_Discrepancy_Slip.pdf",
            "/docs/discrepancy.pdf",
            (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "MSG-007",
            "REQ-2026-0808",
            "USER-PHARM-001",
            "Rajesh Sharma",
            "SunCure Pharmaceuticals API Plant",
            "pharma_manager",
            "We have opened an internal QA investigation to verify if drum #7 and #8 remained in the intermediate airlock. Will update within 24 hours.",
            None,
            None,
            (now - timedelta(days=3, hours=10)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]

    cursor.executemany("""
    INSERT INTO messages (id, request_id, sender_user_id, sender_name, sender_org_name, sender_role, message_text, attachment_name, attachment_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, messages)

    # --- SEED DOCUMENTS ---
    docs = [
        ("DOC-001", "REQ-2026-0814", "BMW Barcode Manifest", "CPCB_Barcode_Manifest_REQ-0814.pdf", "420 KB", "ORG-PROV-001", "verified", t_now),
        ("DOC-002", "REQ-2026-0814", "Destruction Certificate", "Final_Destruction_Cert_Incineration_0814.pdf", "680 KB", "ORG-PROV-001", "verified", t_now),
        ("DOC-003", "REQ-2026-0814", "Weighbridge Slip", "Okhla_CBWTF_Weighbridge_Slip_122kg.pdf", "180 KB", "ORG-PROV-001", "verified", t_now),
        ("DOC-004", "REQ-2026-0810", "Form 10 Manifest", "Form10_Hazardous_Consignment_4412.pdf", "1.2 MB", "ORG-PROV-002", "verified", t_now),
        ("DOC-005", "REQ-2026-0810", "TREMCARD Form 9", "TREMCARD_HazChem_Solvents_GPCB.pdf", "310 KB", "ORG-PHARM-001", "verified", t_now),
        ("DOC-006", "REQ-2026-0810", "MSDS", "Material_Safety_Data_Sheet_SpentSolvents.pdf", "950 KB", "ORG-PHARM-001", "verified", t_now),
        ("DOC-007", "REQ-2026-0816", "Form 10 Manifest", "Form10_Copy2_InTransit_REQ-0816.pdf", "850 KB", "ORG-PROV-002", "verified", t_now),
        ("DOC-008", "REQ-2026-0828", "MSDS", "ETP_Sludge_TCLP_Leachate_Report.pdf", "1.4 MB", "ORG-PHARM-001", "pending_review", t_now),
        ("DOC-009", "REQ-2026-0808", "Weighbridge Slip", "TSDF_Disputed_Weight_Receipt_490kg.pdf", "210 KB", "ORG-PROV-002", "flagged", t_now)
    ]

    cursor.executemany("""
    INSERT INTO documents (id, request_id, doc_type, doc_name, file_size, uploaded_by_org, verification_status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, docs)

    # --- SEED AUDIT LOGS ---
    audit = [
        ("USER-ADMIN-001", "Arjun Nambiar", "WasteConnect India Central Compliance Directorate", "VERIFY_PROVIDER", "ORGANIZATION", "ORG-PROV-001", "Approved annual SPCB CTO renewal for EcoClean CBWTF (Okhla). Capacity validated at 15.0 MT/day.", (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-HOSP-001", "Dr. Anita Rao", "Apollo Multispeciality Hospital", "CREATE_REQUEST", "REQUEST", "REQ-2026-0814", "Created biomedical waste collection order for 124.5 kg Yellow anatomical waste.", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-PROV-001", "Vikram Mehra", "EcoClean BioMed Solutions CBWTF", "UPDATE_STATUS", "REQUEST", "REQ-2026-0814", "Updated status to 'Closed' following completion of incineration cycle at 1050°C.", t_now),
        ("USER-PHARM-001", "Rajesh Sharma", "SunCure Pharmaceuticals API Plant", "CREATE_REQUEST", "REQUEST", "REQ-2026-0810", "Generated Form 10 draft for 3200 kg spent solvent drums with TREMCARD.", (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-ADMIN-001", "Arjun Nambiar", "WasteConnect India Central Compliance Directorate", "FLAG_DISPUTE", "REQUEST", "REQ-2026-0808", "System flagged >15% quantity variance between generator and TSDF weighbridge for investigation.", (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")),
        ("USER-ADMIN-001", "Arjun Nambiar", "WasteConnect India Central Compliance Directorate", "AUDIT_REVIEW", "ORGANIZATION", "ORG-PROV-003", "Apex Green Multi-TSDF application placed under review pending verification of SPCB hazardous consent.", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    ]

    cursor.executemany("""
    INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, audit)

    conn.commit()
    print("Seed data loaded successfully!")

if __name__ == "__main__":
    init_db()
