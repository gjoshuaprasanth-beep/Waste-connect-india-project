"""
WasteConnect India - High-Performance Standard Library HTTP Server & REST API
Supports Role-Based Access Control, SQLite Relational Store, and SPA Static Hosting.
Zero external pip dependencies required.
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
import sqlite3

from database import DB_PATH, get_connection, init_db

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Current in-memory session (defaults to Dr. Anita Rao, Hospital Admin)
CURRENT_SESSION = {
    "user_id": "USER-HOSP-001"
}

class WasteConnectHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching for local prototype demo
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_json(self, data, status_code=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message, status_code=400):
        self._send_json({"error": message, "success": False}, status_code=status_code)

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _get_current_user(self):
        # Allow override via custom header or fallback to session
        header_user_id = self.headers.get("X-User-Id")
        user_id = header_user_id if header_user_id else CURRENT_SESSION.get("user_id", "USER-HOSP-001")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.*, o.name as org_name, o.org_type, o.reg_number as org_reg, 
                   o.state as org_state, o.city as org_city, o.address as org_address,
                   o.authorized_waste_types, o.verification_status, o.daily_capacity_mt,
                   o.compliance_rating
            FROM users u
            JOIN organizations o ON u.org_id = o.id
            WHERE u.id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        try:
            d["authorized_waste_types"] = json.loads(d["authorized_waste_types"])
        except Exception:
            d["authorized_waste_types"] = []
        return d

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            self._handle_api_get(path, query)
        else:
            # Fallback SPA routing: if requesting root or a non-file path, serve index.html
            if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_post(path)
        else:
            self._send_error("Not Found", 404)

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_patch(path)
        else:
            self._send_error("Not Found", 404)

    # ========================== API GET ROUTING ==========================
    def _handle_api_get(self, path, query):
        current_user = self._get_current_user()
        if not current_user:
            return self._send_error("Unauthorized session", 401)

        # 1. Current Session
        if path == "/api/auth/current":
            return self._send_json({"success": True, "user": current_user})

        # 2. Available Preset Demo Users for 1-Click Role Switcher
        if path == "/api/auth/users":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.full_name, u.role, u.designation, u.avatar, u.email,
                       o.name as org_name, o.org_type, o.verification_status
                FROM users u
                JOIN organizations o ON u.org_id = o.id
                ORDER BY u.role
            """)
            users = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self._send_json({"success": True, "users": users})

        # 3. Dashboard Statistics (Role-tailored)
        if path == "/api/dashboard/stats":
            return self._get_dashboard_stats(current_user)

        # 4. Collection Requests List
        if path == "/api/requests":
            return self._get_requests_list(current_user, query)

        # 5. Single Request Details
        if path.startswith("/api/requests/") and not path.endswith("/messages") and not path.endswith("/status"):
            req_id = path.split("/")[3]
            return self._get_request_details(req_id, current_user)

        # 6. Request Messages
        if path.startswith("/api/requests/") and path.endswith("/messages"):
            req_id = path.split("/")[3]
            return self._get_request_messages(req_id, current_user)

        # 7. Providers Directory
        if path == "/api/providers":
            return self._get_providers_list(query)

        # 8. Organizations (Admin / Directory)
        if path == "/api/organizations":
            return self._get_organizations_list(current_user, query)

        # 9. Documents Vault
        if path == "/api/documents":
            return self._get_documents_list(current_user, query)

        # 10. Admin Audit Logs
        if path == "/api/audit-logs":
            if current_user["role"] != "platform_admin":
                return self._send_error("Forbidden: Platform Admin only", 403)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
            logs = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self._send_json({"success": True, "logs": logs})

        # 11. Disputes & Exceptions Radar
        if path == "/api/disputes":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.*, g.name as generator_name, p.name as provider_name
                FROM collection_requests r
                JOIN organizations g ON r.generator_org_id = g.id
                LEFT JOIN organizations p ON r.assigned_provider_id = p.id
                WHERE r.status IN ('Disputed', 'Rejected')
                ORDER BY r.updated_at DESC
            """)
            disputes = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self._send_json({"success": True, "disputes": disputes})

        # 12. Formatted Official Manifest Generator Preview
        if path.startswith("/api/manifest/"):
            req_id = path.split("/")[3]
            return self._get_manifest_data(req_id)

        # 13. GPS Vehicle & Route Live Tracking
        if path.startswith("/api/tracking/"):
            req_id = path.split("/")[3]
            return self._get_tracking_data(req_id)

        # 14. SPCB Form 4 & Form 10 Annual Returns Report
        if path == "/api/reports/annual":
            return self._get_annual_returns_report(current_user, query)

        self._send_error(f"API endpoint GET {path} not found", 404)

    # ========================== API POST ROUTING ==========================
    def _handle_api_post(self, path):
        current_user = self._get_current_user()
        data = self._read_json()

        # Switch Active User Role
        if path == "/api/auth/switch":
            new_user_id = data.get("user_id")
            if not new_user_id:
                return self._send_error("user_id required")
            CURRENT_SESSION["user_id"] = new_user_id
            updated_user = self._get_current_user()
            return self._send_json({"success": True, "user": updated_user, "message": f"Switched to {updated_user['full_name']} ({updated_user['role']})"})

        # Login endpoint
        if path == "/api/auth/login":
            email = data.get("email", "").strip()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            if row:
                CURRENT_SESSION["user_id"] = row["id"]
                user = self._get_current_user()
                return self._send_json({"success": True, "user": user})
            return self._send_error("Invalid email or user not found", 401)

        # Create New Collection Request
        if path == "/api/requests":
            return self._create_collection_request(current_user, data)

        # Add Message to Request
        if path.startswith("/api/requests/") and path.endswith("/messages"):
            req_id = path.split("/")[3]
            return self._create_request_message(req_id, current_user, data)

        # Upload / Attach Document
        if path == "/api/documents":
            return self._create_document(current_user, data)

        # Resolve Dispute
        if path.startswith("/api/disputes/") and path.endswith("/resolve"):
            req_id = path.split("/")[3]
            return self._resolve_dispute(req_id, current_user, data)

        # Barcode Scanner Simulation
        if path == "/api/barcode/scan":
            return self._simulate_barcode_scan(current_user, data)

        self._send_error(f"API endpoint POST {path} not found", 404)

    # ========================== API PATCH ROUTING ==========================
    def _handle_api_patch(self, path):
        current_user = self._get_current_user()
        data = self._read_json()

        # Update Request Status & Workflow Step
        if path.startswith("/api/requests/") and path.endswith("/status"):
            req_id = path.split("/")[3]
            return self._update_request_status(req_id, current_user, data)

        # Admin Provider Verification
        if path.startswith("/api/organizations/") and path.endswith("/verify"):
            if current_user["role"] != "platform_admin":
                return self._send_error("Admin access required", 403)
            org_id = path.split("/")[3]
            return self._verify_provider_organization(org_id, current_user, data)

        self._send_error(f"API endpoint PATCH {path} not found", 404)

    # ========================== WORKFLOW IMPLEMENTATION ==========================
    def _get_dashboard_stats(self, user):
        role = user["role"]
        org_id = user["org_id"]
        conn = get_connection()
        cursor = conn.cursor()

        # Base filter according to RBAC
        where_clause = ""
        params = []
        if role in ("hospital_admin", "pharma_manager"):
            where_clause = "WHERE generator_org_id = ?"
            params = [org_id]
        elif role == "provider_operator":
            where_clause = "WHERE assigned_provider_id = ? OR assigned_provider_id IS NULL"
            params = [org_id]
        # Admin has no WHERE filter

        # 1. Total Requests
        query_total = f"SELECT COUNT(*) FROM collection_requests {where_clause}"
        cursor.execute(query_total, params)
        total_requests = cursor.fetchone()[0]

        # 2. Pending Approvals (Draft, Submitted, Under Review)
        p_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status IN ('Draft', 'Submitted', 'Under Review')"
        cursor.execute(f"SELECT COUNT(*) FROM collection_requests {p_clause}", params)
        pending_approvals = cursor.fetchone()[0]

        # 3. Scheduled Pickups
        s_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status = 'Scheduled'"
        cursor.execute(f"SELECT COUNT(*) FROM collection_requests {s_clause}", params)
        scheduled_pickups = cursor.fetchone()[0]

        # 4. Completed / Closed Collections
        c_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status = 'Closed'"
        cursor.execute(f"SELECT COUNT(*) FROM collection_requests {c_clause}", params)
        completed_collections = cursor.fetchone()[0]

        # 5. In-Transit / Collected / At Facility
        t_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status IN ('Collected', 'Received at Facility')"
        cursor.execute(f"SELECT COUNT(*) FROM collection_requests {t_clause}", params)
        in_transit = cursor.fetchone()[0]

        # 6. Disputes / Missing attention
        d_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status IN ('Disputed', 'Rejected')"
        cursor.execute(f"SELECT COUNT(*) FROM collection_requests {d_clause}", params)
        attention_required = cursor.fetchone()[0]

        # 7. Total Quantity Handled (in kg & MT)
        q_clause = ("WHERE" if not where_clause else where_clause + " AND") + " status = 'Closed'"
        cursor.execute(f"SELECT COALESCE(SUM(COALESCE(actual_collected_quantity_kg, estimated_quantity_kg)), 0) FROM collection_requests {q_clause}", params)
        total_kg_treated = cursor.fetchone()[0]

        # 8. Category Breakdown
        cat_query = f"SELECT waste_category, COUNT(*) as count, SUM(estimated_quantity_kg) as total_kg FROM collection_requests {where_clause} GROUP BY waste_category"
        cursor.execute(cat_query, params)
        category_breakdown = [dict(r) for r in cursor.fetchall()]

        # 9. Recent Activity List
        rec_query = f"""
            SELECT r.id, r.request_type, r.waste_category, r.status, r.estimated_quantity_kg, 
                   r.preferred_date, r.updated_at, g.name as generator_name, p.name as provider_name
            FROM collection_requests r
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            {where_clause}
            ORDER BY r.updated_at DESC LIMIT 6
        """
        cursor.execute(rec_query, params)
        recent_activity = [dict(r) for r in cursor.fetchall()]

        # 10. Provider metrics if provider role
        provider_metrics = None
        if role == "provider_operator":
            cursor.execute("SELECT daily_capacity_mt, compliance_rating, verification_status FROM organizations WHERE id = ?", (org_id,))
            prov_row = cursor.fetchone()
            if prov_row:
                provider_metrics = dict(prov_row)

        conn.close()

        return self._send_json({
            "success": True,
            "metrics": {
                "total_requests": total_requests,
                "pending_approvals": pending_approvals,
                "scheduled_pickups": scheduled_pickups,
                "in_transit": in_transit,
                "completed_collections": completed_collections,
                "attention_required": attention_required,
                "total_kg_treated": round(total_kg_treated, 1),
                "total_mt_treated": round(total_kg_treated / 1000.0, 2)
            },
            "category_breakdown": category_breakdown,
            "recent_activity": recent_activity,
            "provider_metrics": provider_metrics
        })

    def _get_requests_list(self, user, query):
        role = user["role"]
        org_id = user["org_id"]
        status_filter = query.get("status", [None])[0]
        type_filter = query.get("type", [None])[0]
        search = query.get("search", [None])[0]

        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT r.*, g.name as generator_name, g.city as generator_city, g.reg_number as generator_reg,
                   p.name as provider_name, p.city as provider_city
            FROM collection_requests r
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            WHERE 1=1
        """
        params = []

        # RBAC Filters
        if role in ("hospital_admin", "pharma_manager"):
            sql += " AND r.generator_org_id = ?"
            params.append(org_id)
        elif role == "provider_operator":
            # Providers see requests assigned to them OR submitted unassigned matching their capabilities
            sql += " AND (r.assigned_provider_id = ? OR (r.assigned_provider_id IS NULL AND r.status IN ('Submitted', 'Under Review')))"
            params.append(org_id)

        if status_filter and status_filter != "all":
            sql += " AND r.status = ?"
            params.append(status_filter)

        if type_filter and type_filter != "all":
            sql += " AND r.request_type = ?"
            params.append(type_filter)

        if search:
            sql += " AND (r.id LIKE ? OR r.waste_description LIKE ? OR r.waste_category LIKE ? OR g.name LIKE ?)"
            s_param = f"%{search}%"
            params.extend([s_param, s_param, s_param, s_param])

        sql += " ORDER BY r.updated_at DESC"
        cursor.execute(sql, params)
        requests = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Parse JSON hazard details
        for r in requests:
            if r.get("hazard_details"):
                try:
                    r["hazard_details"] = json.loads(r["hazard_details"])
                except Exception:
                    pass

        return self._send_json({"success": True, "requests": requests, "count": len(requests)})

    def _get_request_details(self, req_id, user):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.*, 
                   g.name as generator_name, g.org_type as generator_org_type, g.reg_number as generator_reg, 
                   g.address as generator_address, g.city as generator_city, g.state as generator_state,
                   g.contact_phone as generator_phone, g.contact_email as generator_email,
                   p.name as provider_name, p.reg_number as provider_reg, p.address as provider_address,
                   p.city as provider_city, p.contact_phone as provider_phone,
                   u.full_name as creator_name, u.designation as creator_designation
            FROM collection_requests r
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            JOIN users u ON r.created_by_user_id = u.id
            WHERE r.id = ?
        """, (req_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return self._send_error("Request not found", 404)

        req = dict(row)
        if req.get("hazard_details"):
            try:
                req["hazard_details"] = json.loads(req["hazard_details"])
            except Exception:
                pass

        # Permission check: hospitals/pharma only their own, providers only their assigned/available
        if user["role"] in ("hospital_admin", "pharma_manager") and req["generator_org_id"] != user["org_id"]:
            conn.close()
            return self._send_error("Access denied to this request record", 403)

        # Status History
        cursor.execute("""
            SELECT * FROM request_status_history
            WHERE request_id = ?
            ORDER BY id ASC
        """, (req_id,))
        history = [dict(h) for h in cursor.fetchall()]

        # Documents
        cursor.execute("""
            SELECT * FROM documents
            WHERE request_id = ?
            ORDER BY created_at DESC
        """, (req_id,))
        documents = [dict(d) for d in cursor.fetchall()]

        conn.close()
        return self._send_json({
            "success": True,
            "request": req,
            "history": history,
            "documents": documents
        })

    def _create_collection_request(self, user, data):
        # Only hospital or pharma can create
        if user["role"] not in ("hospital_admin", "pharma_manager", "platform_admin"):
            return self._send_error("Only waste generator organizations can create collection requests", 403)

        conn = get_connection()
        cursor = conn.cursor()

        # Generate unique ID
        now = datetime.now()
        t_now = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) FROM collection_requests")
        count = cursor.fetchone()[0] + 1
        req_id = f"REQ-2026-{1000 + count}"

        generator_org_id = user["org_id"]
        generator_type = "hospital" if user["role"] == "hospital_admin" else "pharma"
        request_type = data.get("request_type", "biomedical" if generator_type == "hospital" else "pharma_hazardous")

        waste_category = data.get("waste_category")
        if not waste_category:
            conn.close()
            return self._send_error("waste_category is mandatory")

        # Regulatory separation rule: Hospital cannot create HazChem without pharma role, and vice versa
        if generator_type == "hospital" and not waste_category.startswith("BMW-"):
            conn.close()
            return self._send_error("Biomedical rules require color-coded categories: Yellow, Red, White, or Blue.")
        if generator_type == "pharma" and not waste_category.startswith("HAZ-"):
            conn.close()
            return self._send_error("Industrial pharma requires Hazardous Waste Rules 2016 classification (HAZ-).")

        assigned_provider_id = data.get("assigned_provider_id")
        estimated_quantity_kg = float(data.get("estimated_quantity_kg", 0))
        waste_description = data.get("waste_description", "Standard sorted waste consignment")
        packaging_type = data.get("packaging_type", "Barcoded Bags / Drums")
        pickup_location = data.get("pickup_location", user.get("org_address", "Main facility yard"))
        preferred_date = data.get("preferred_date", (now + timedelta(days=1)).strftime("%Y-%m-%d"))
        hazard_details = data.get("hazard_details")
        hazard_json = json.dumps(hazard_details) if hazard_details else None

        manifest_prefix = "CPCB-BMW-2026-" if request_type == "biomedical" else "FORM10-HAZ-2026-"
        manifest_number = f"{manifest_prefix}{5000 + count}"

        initial_status = "Submitted"

        cursor.execute("""
            INSERT INTO collection_requests (
                id, generator_org_id, generator_type, assigned_provider_id, request_type,
                waste_category, waste_description, estimated_quantity_kg, packaging_type,
                pickup_location, preferred_date, status, status_reason, hazard_details,
                manifest_number, created_by_user_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id, generator_org_id, generator_type, assigned_provider_id, request_type,
            waste_category, waste_description, estimated_quantity_kg, packaging_type,
            pickup_location, preferred_date, initial_status, "New request submitted by generator",
            hazard_json, manifest_number, user["id"], t_now, t_now
        ))

        # Add to history
        cursor.execute("""
            INSERT INTO request_status_history (request_id, old_status, new_status, changed_by_user_id, changed_by_name, comment, timestamp)
            VALUES (?, 'Draft', ?, ?, ?, ?, ?)
        """, (req_id, initial_status, user["id"], user["full_name"], "Initial submission with verified generator authorization", t_now))

        # Add initial system document (Draft Manifest)
        doc_id = f"DOC-{count + 100}"
        doc_title = "Form 10 Hazardous Consignment Note (Draft)" if request_type == "pharma_hazardous" else "CPCB Bio-Medical Waste Barcode Manifest"
        cursor.execute("""
            INSERT INTO documents (id, request_id, doc_type, doc_name, file_size, uploaded_by_org, verification_status, created_at)
            VALUES (?, ?, ?, ?, '350 KB', ?, 'verified', ?)
        """, (doc_id, req_id, "Form 10 Manifest" if request_type == "pharma_hazardous" else "BMW Barcode Manifest", f"{manifest_number}.pdf", user["org_name"], t_now))

        # Add initial automated greeting in chat
        msg_id = f"MSG-SYS-{count + 100}"
        cursor.execute("""
            INSERT INTO messages (id, request_id, sender_user_id, sender_name, sender_org_name, sender_role, message_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id, req_id, user["id"], user["full_name"], user["org_name"], user["role"],
            f"Consignment {req_id} initiated ({estimated_quantity_kg} kg of {waste_category}). Awaiting provider schedule confirmation.",
            t_now
        ))

        # Admin Audit log
        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, 'CREATE_REQUEST', 'REQUEST', ?, ?, ?)
        """, (user["id"], user["full_name"], user["org_name"], req_id, f"Created {request_type} request for {estimated_quantity_kg} kg of {waste_category}", t_now))

        conn.commit()
        conn.close()

        return self._send_json({"success": True, "request_id": req_id, "message": "Collection request submitted successfully!"}, 201)

    def _update_request_status(self, req_id, user, data):
        new_status = data.get("status")
        comment = data.get("comment", "")
        now = datetime.now()
        t_now = now.strftime("%Y-%m-%d %H:%M:%S")

        valid_statuses = [
            "Draft", "Submitted", "Under Review", "Accepted", "Scheduled",
            "Collected", "Received at Facility", "Closed", "Rejected", "Disputed"
        ]
        if new_status not in valid_statuses:
            return self._send_error(f"Invalid status '{new_status}'")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM collection_requests WHERE id = ?", (req_id,))
        req = cursor.fetchone()
        if not req:
            conn.close()
            return self._send_error("Request not found", 404)

        old_status = req["status"]

        # Optional transporter & payload fields when advancing status
        updates = ["status = ?", "updated_at = ?", "status_reason = ?"]
        params = [new_status, t_now, comment or f"Status changed to {new_status}"]

        # If provider accepts or assigns:
        if "assigned_provider_id" in data:
            updates.append("assigned_provider_id = ?")
            params.append(data["assigned_provider_id"])
        elif user["role"] == "provider_operator" and not req["assigned_provider_id"]:
            updates.append("assigned_provider_id = ?")
            params.append(user["org_id"])

        if "vehicle_number" in data and data["vehicle_number"]:
            updates.append("vehicle_number = ?")
            params.append(data["vehicle_number"])
        if "driver_name" in data and data["driver_name"]:
            updates.append("driver_name = ?")
            params.append(data["driver_name"])
        if "driver_phone" in data and data["driver_phone"]:
            updates.append("driver_phone = ?")
            params.append(data["driver_phone"])
        if "transporter_name" in data and data["transporter_name"]:
            updates.append("transporter_name = ?")
            params.append(data["transporter_name"])
        if "scheduled_date" in data and data["scheduled_date"]:
            updates.append("scheduled_date = ?")
            params.append(data["scheduled_date"])
        if "actual_collected_quantity_kg" in data and data["actual_collected_quantity_kg"] is not None:
            updates.append("actual_collected_quantity_kg = ?")
            params.append(float(data["actual_collected_quantity_kg"]))
        if "treatment_method" in data and data["treatment_method"]:
            updates.append("treatment_method = ?")
            params.append(data["treatment_method"])

        params.append(req_id)
        sql = f"UPDATE collection_requests SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)

        # Insert history record
        cursor.execute("""
            INSERT INTO request_status_history (request_id, old_status, new_status, changed_by_user_id, changed_by_name, comment, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req_id, old_status, new_status, user["id"], user["full_name"], comment or f"Advanced workflow to {new_status}", t_now))

        # Auto-create documents upon completion
        if new_status == "Closed":
            cert_id = f"DOC-DEST-{req_id[-4:]}"
            cursor.execute("""
                INSERT INTO documents (id, request_id, doc_type, doc_name, file_size, uploaded_by_org, verification_status, created_at)
                VALUES (?, ?, 'Destruction Certificate', ?, '540 KB', ?, 'verified', ?)
            """, (cert_id, req_id, f"Destruction_Certificate_{req_id}.pdf", user["org_name"], t_now))

        if new_status == "Collected" and data.get("actual_collected_quantity_kg"):
            slip_id = f"DOC-WT-{req_id[-4:]}"
            cursor.execute("""
                INSERT INTO documents (id, request_id, doc_type, doc_name, file_size, uploaded_by_org, verification_status, created_at)
                VALUES (?, ?, 'Weighbridge Slip', ?, '210 KB', ?, 'verified', ?)
            """, (slip_id, req_id, f"Weighbridge_Slip_{req_id}_{data.get('actual_collected_quantity_kg')}kg.pdf", user["org_name"], t_now))

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, 'UPDATE_STATUS', 'REQUEST', ?, ?, ?)
        """, (user["id"], user["full_name"], user["org_name"], req_id, f"Status updated from {old_status} to {new_status}. {comment}", t_now))

        # Send automatic notification message into chat
        cursor.execute("""
            INSERT INTO messages (id, request_id, sender_user_id, sender_name, sender_org_name, sender_role, message_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"MSG-SYS-{datetime.now().microsecond}", req_id, user["id"], user["full_name"], user["org_name"], user["role"],
            f"Status updated to '{new_status}'. {comment if comment else ''}",
            t_now
        ))

        conn.commit()
        conn.close()

        return self._send_json({"success": True, "message": f"Request status updated to {new_status}"})

    def _get_request_messages(self, req_id, user):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE request_id = ?
            ORDER BY created_at ASC
        """, (req_id,))
        messages = [dict(m) for m in cursor.fetchall()]
        conn.close()
        return self._send_json({"success": True, "messages": messages})

    def _create_request_message(self, req_id, user, data):
        message_text = data.get("message_text", "").strip()
        attachment_name = data.get("attachment_name")
        attachment_url = data.get("attachment_url")

        if not message_text and not attachment_name:
            return self._send_error("Message text or attachment required")

        now = datetime.now()
        t_now = now.strftime("%Y-%m-%d %H:%M:%S")
        msg_id = f"MSG-{now.strftime('%y%m%d%H%M%S%f')[:14]}"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (id, request_id, sender_user_id, sender_name, sender_org_name, sender_role, message_text, attachment_name, attachment_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, req_id, user["id"], user["full_name"], user["org_name"], user["role"], message_text, attachment_name, attachment_url, t_now))
        conn.commit()
        conn.close()

        return self._send_json({"success": True, "message_id": msg_id, "created_at": t_now})

    def _get_providers_list(self, query):
        waste_type = query.get("type", [None])[0]
        status = query.get("status", [None])[0]

        conn = get_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM organizations WHERE org_type = 'provider'"
        params = []

        if status:
            sql += " AND verification_status = ?"
            params.append(status)

        cursor.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        filtered = []
        for r in rows:
            try:
                r["authorized_waste_types"] = json.loads(r["authorized_waste_types"])
            except Exception:
                r["authorized_waste_types"] = []

            # Regulatory filtering by capabilities
            if waste_type:
                if waste_type == "biomedical" and not any(t.startswith("BMW-") for t in r["authorized_waste_types"]):
                    continue
                if waste_type == "pharma_hazardous" and not any(t.startswith("HAZ-") for t in r["authorized_waste_types"]):
                    continue
            filtered.append(r)

        return self._send_json({"success": True, "providers": filtered, "count": len(filtered)})

    def _get_organizations_list(self, user, query):
        org_type = query.get("type", [None])[0]
        conn = get_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM organizations WHERE 1=1"
        params = []
        if org_type:
            sql += " AND org_type = ?"
            params.append(org_type)
        cursor.execute(sql, params)
        orgs = [dict(r) for r in cursor.fetchall()]
        conn.close()

        for o in orgs:
            try:
                o["authorized_waste_types"] = json.loads(o["authorized_waste_types"])
            except Exception:
                pass

        return self._send_json({"success": True, "organizations": orgs})

    def _verify_provider_organization(self, org_id, user, data):
        new_status = data.get("verification_status") # verified, suspended, pending
        capacity = data.get("daily_capacity_mt")
        expiry = data.get("spcb_license_expiry")

        conn = get_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        if new_status:
            updates.append("verification_status = ?")
            params.append(new_status)
        if capacity is not None:
            updates.append("daily_capacity_mt = ?")
            params.append(float(capacity))
        if expiry:
            updates.append("spcb_license_expiry = ?")
            params.append(expiry)

        if not updates:
            conn.close()
            return self._send_error("No fields to update")

        params.append(org_id)
        sql = f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, 'VERIFY_PROVIDER', 'ORGANIZATION', ?, ?, ?)
        """, (user["id"], user["full_name"], user["org_name"], org_id, f"Updated provider verification status to {new_status}", now))

        conn.commit()
        conn.close()

        return self._send_json({"success": True, "message": f"Provider {org_id} status updated to {new_status}"})

    def _get_documents_list(self, user, query):
        role = user["role"]
        org_id = user["org_id"]
        doc_type = query.get("type", [None])[0]

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT d.*, r.waste_category, r.request_type, g.name as generator_name, p.name as provider_name
            FROM documents d
            JOIN collection_requests r ON d.request_id = r.id
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            WHERE 1=1
        """
        params = []
        if role in ("hospital_admin", "pharma_manager"):
            sql += " AND r.generator_org_id = ?"
            params.append(org_id)
        elif role == "provider_operator":
            sql += " AND r.assigned_provider_id = ?"
            params.append(org_id)

        if doc_type:
            sql += " AND d.doc_type = ?"
            params.append(doc_type)

        sql += " ORDER BY d.created_at DESC"
        cursor.execute(sql, params)
        docs = [dict(d) for d in cursor.fetchall()]
        conn.close()

        return self._send_json({"success": True, "documents": docs})

    def _create_document(self, user, data):
        req_id = data.get("request_id")
        doc_type = data.get("doc_type", "Weighbridge Slip")
        doc_name = data.get("doc_name", f"Document_{req_id}.pdf")
        file_size = data.get("file_size", "450 KB")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc_id = f"DOC-{datetime.now().strftime('%m%d%H%M%S')}"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (id, request_id, doc_type, doc_name, file_size, uploaded_by_org, verification_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'verified', ?)
        """, (doc_id, req_id, doc_type, doc_name, file_size, user["org_name"], now))

        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, 'UPLOAD_DOCUMENT', 'DOCUMENT', ?, ?, ?)
        """, (user["id"], user["full_name"], user["org_name"], doc_id, f"Uploaded {doc_type}: {doc_name} for {req_id}", now))

        conn.commit()
        conn.close()

        return self._send_json({"success": True, "document_id": doc_id, "message": "Document uploaded successfully"})

    def _get_manifest_data(self, req_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, 
                   g.name as generator_name, g.reg_number as generator_reg, g.address as generator_address,
                   g.city as generator_city, g.state as generator_state, g.contact_phone as generator_phone,
                   p.name as provider_name, p.reg_number as provider_reg, p.address as provider_address,
                   p.city as provider_city, p.state as provider_state, p.contact_phone as provider_phone
            FROM collection_requests r
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            WHERE r.id = ?
        """, (req_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return self._send_error("Request not found", 404)

        data = dict(row)
        if data.get("hazard_details"):
            try:
                data["hazard_details"] = json.loads(data["hazard_details"])
            except Exception:
                pass

        # Manifest Format details
        is_biomedical = data["request_type"] == "biomedical"
        manifest_meta = {
            "format_name": "FORM 10 - HAZARDOUS WASTE MANIFEST (Rule 20(1))" if not is_biomedical else "CPCB BIO-MEDICAL WASTE COLLECTION MANIFEST (Rule 13)",
            "statutory_act": "Hazardous and Other Wastes Rules, 2016" if not is_biomedical else "Bio-Medical Waste Management Rules, 2016",
            "copies_color_codes": [
                "Copy 1 (White): Retained by Generator",
                "Copy 2 (Yellow): Retained by Transporter",
                "Copy 3 (Pink): Retained by TSDF/CBWTF Facility",
                "Copy 4 (Orange): Returned to Generator after Treatment",
                "Copy 5 (Green): Forwarded to SPCB by Facility"
            ] if not is_biomedical else [
                "Copy 1: Generator Record (Barcoded)",
                "Copy 2: CBWTF Reception & Weighbridge Scan",
                "Copy 3: SPCB Annual Return Record"
            ],
            "barcode_value": f"*WC-{data['id']}-{data['manifest_number']}*",
            "verified_date": data.get("scheduled_date") or data.get("preferred_date"),
            "regulatory_disclaimer": "WasteConnect India facilitates electronic manifest generation. Physical custody transfer requires authorized signatory stamps."
        }

        return self._send_json({"success": True, "manifest": data, "meta": manifest_meta})

    def _get_tracking_data(self, req_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, g.name as generator_name, g.city as gen_city, p.name as provider_name, p.city as prov_city
            FROM collection_requests r
            JOIN organizations g ON r.generator_org_id = g.id
            LEFT JOIN organizations p ON r.assigned_provider_id = p.id
            WHERE r.id = ?
        """, (req_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return self._send_error("Request not found", 404)

        req = dict(row)
        is_biomedical = req["request_type"] == "biomedical"

        tracking_info = {
            "request_id": req["id"],
            "status": req["status"],
            "transporter": req.get("transporter_name") or "Authorized Dedicated Carrier",
            "vehicle_number": req.get("vehicle_number") or "DL-1L-AA-4019 (GPS Active)",
            "driver_name": req.get("driver_name") or "Kishan Lal",
            "driver_phone": req.get("driver_phone") or "+91 98711 00223",
            "speed_kmh": 36 if req["status"] in ("Collected", "Scheduled") else 0,
            "engine_status": "Running (GPS Live)" if req["status"] in ("Collected", "Scheduled") else "Stationary",
            "compartment_temp_c": 4.5 if is_biomedical else 26.0,
            "temp_status": "Optimal Cold Chain Compliant" if is_biomedical else "Ambient HazMat Compliant",
            "route": {
                "origin": f"{req['generator_name']}, {req['gen_city']}",
                "destination": f"{req['provider_name']}, {req['prov_city']}",
                "total_distance_km": 24.5 if is_biomedical else 42.0,
                "distance_covered_km": 16.8 if req["status"] == "Collected" else (24.5 if req["status"] in ("Received at Facility", "Closed") else 0),
                "eta_minutes": 18 if req["status"] == "Collected" else 0
            },
            "checkpoints": [
                {"name": "Generator Security Gate Checkpoint", "time": "09:35 AM", "status": "Passed", "weight_kg": req.get("actual_collected_quantity_kg") or req["estimated_quantity_kg"]},
                {"name": "SPCB Transit RFID Sensor (Corridor Toll)", "time": "10:04 AM", "status": "Logged", "speed_kmh": 42},
                {"name": "Facility Entrance Weighbridge Slip #9921", "time": "10:28 AM", "status": "Reached" if req["status"] in ("Received at Facility", "Closed") else "In-Transit", "reading_kg": req.get("actual_collected_quantity_kg") or req["estimated_quantity_kg"]}
            ]
        }
        return self._send_json({"success": True, "tracking": tracking_info})

    def _get_annual_returns_report(self, user, query):
        conn = get_connection()
        cursor = conn.cursor()
        year = query.get("year", ["2026"])[0]

        # Aggregate total weight by category for current user's org or platform wide
        where_clause = ""
        params = []
        if user["role"] in ("hospital_admin", "pharma_manager"):
            where_clause = "WHERE generator_org_id = ?"
            params = [user["org_id"]]
        elif user["role"] == "provider_operator":
            where_clause = "WHERE assigned_provider_id = ?"
            params = [user["org_id"]]

        cursor.execute(f"""
            SELECT waste_category, 
                   COUNT(*) as consignment_count,
                   SUM(estimated_quantity_kg) as total_est_kg,
                   SUM(COALESCE(actual_collected_quantity_kg, estimated_quantity_kg)) as total_actual_kg
            FROM collection_requests
            {where_clause}
            GROUP BY waste_category
        """, params)
        rows = [dict(r) for r in cursor.fetchall()]

        total_kg = sum(r["total_actual_kg"] for r in rows) if rows else 0

        # CPCB compliance indicators
        report = {
            "year": year,
            "reporting_organization": user["org_name"],
            "authorization_cto_number": user.get("org_reg") or "SPCB/BMW/DL/2022/9481",
            "statutory_form": "Form 4 (Annual Bio-Medical Report)" if user["role"] == "hospital_admin" else "Form 10 (Hazardous Waste Annual Statement)",
            "statutory_deadline": f"June 30, {year}",
            "submission_status": "Ready for Digital SPCB Submission",
            "authorized_capacity_mt": user.get("daily_capacity_mt", 1.0),
            "total_consignments": sum(r["consignment_count"] for r in rows),
            "total_weight_kg": round(total_kg, 1),
            "total_weight_mt": round(total_kg / 1000.0, 3),
            "categories_summary": rows,
            "certified_officer": user["full_name"],
            "designation": user["designation"]
        }
        conn.close()
        return self._send_json({"success": True, "report": report})

    def _resolve_dispute(self, req_id, user, data):
        resolved_weight = data.get("resolved_weight_kg")
        resolution_notes = data.get("resolution_notes", "Discrepancy audited and settled.")
        
        if not resolved_weight:
            return self._send_error("resolved_weight_kg is required")

        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE collection_requests
            SET status = 'Received at Facility',
                actual_collected_quantity_kg = ?,
                status_reason = ?,
                updated_at = ?
            WHERE id = ?
        """, (float(resolved_weight), f"Dispute resolved by {user['full_name']}. {resolution_notes}", now, req_id))

        cursor.execute("""
            INSERT INTO request_status_history (request_id, old_status, new_status, changed_by_user_id, changed_by_name, comment, timestamp)
            VALUES (?, 'Disputed', 'Received at Facility', ?, ?, ?, ?)
        """, (req_id, user["id"], user["full_name"], f"Dispute settled at {resolved_weight} kg. {resolution_notes}", now))

        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name, org_name, action, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, 'RESOLVE_DISPUTE', 'REQUEST', ?, ?, ?)
        """, (user["id"], user["full_name"], user["org_name"], req_id, f"Settled weight at {resolved_weight} kg. Notes: {resolution_notes}", now))

        conn.commit()
        conn.close()
        return self._send_json({"success": True, "message": f"Dispute for {req_id} resolved at {resolved_weight} kg."})

    def _simulate_barcode_scan(self, user, data):
        raw_barcode = data.get("barcode", f"CPCB-BMW-2026-{datetime.now().strftime('%H%M%S')}-YEL")
        waste_cat = "BMW-Yellow-Anatomical"
        if "RED" in raw_barcode.upper(): waste_cat = "BMW-Red-Plastic"
        elif "WHT" in raw_barcode.upper() or "WHITE" in raw_barcode.upper(): waste_cat = "BMW-White-Sharps"
        elif "BLU" in raw_barcode.upper() or "BLUE" in raw_barcode.upper(): waste_cat = "BMW-Blue-Glass"

        scan_result = {
            "barcode": raw_barcode,
            "verification": "VALID CPCB BARCODE FORMAT",
            "detected_category": waste_cat,
            "tare_weight_kg": 0.45,
            "bag_micron": 55,
            "non_chlorinated_certified": True,
            "scanned_by": user["full_name"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return self._send_json({"success": True, "scan": scan_result})



def run_server(port=PORT):
    init_db()
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ("127.0.0.1", port)
    
    # Allow socket reuse so restarts don't fail with Address In Use
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(server_address, WasteConnectHandler)
    print(f"==================================================")
    print(f" WasteConnect India Server Active on http://127.0.0.1:{port}")
    print(f" Serving Static UI from: {STATIC_DIR}")
    print(f" Database: {DB_PATH}")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
