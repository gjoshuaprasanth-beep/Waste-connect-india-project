# WasteConnect India
## A Functional Waste Management Coordination Platform

WasteConnect India is an enterprise-grade digital B2B waste coordination platform connecting hospitals, pharmaceutical manufacturing companies, and authorized waste management providers through one centralized, role-isolated digital system.

Designed and engineered per statutory Indian environmental frameworks:
- **Bio-Medical Waste Management Rules, 2016** (Ministry of Environment, Forest and Climate Change / CPCB)
- **Hazardous and Other Wastes (Management & Transboundary Movement) Rules, 2016** (Form 10 Manifest System)

---

## 🛠️ Technology Stack

- **Frontend**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS
- **UI & Icons**: Reusable Component System, Lucide React
- **Data Visualizations & Analytics**: Recharts
- **Backend**: Node.js with Express
- **Database Engine**: Relational SQLite with Drizzle ORM Schema, WAL mode, foreign key enforcement
- **Authentication**: Secure JWT token-based auth with bcrypt password hashing and server-side role verification
- **File Uploads & Documents**: Express Multer storage with type validation and organization-level access isolation

---

## 👥 User Roles & Seeded Demo Accounts

The platform includes convenient 1-click demo access and seeded accounts for college faculty, investor, and customer demonstrations:

| Role | Organization Type | Demo Email | Password | Primary Workflow |
| :--- | :--- | :--- | :--- | :--- |
| **🏥 Hospital / Lab** | Hospital (Bio-Medical Waste) | `hospital@wasteconnect.in` | `password123` | Submit Yellow/Red/White/Blue BMW requests, find verified CBWTFs, track barcode pickups |
| **💊 Pharma Mfg** | Pharmaceutical Plant | `pharma@wasteconnect.in` | `password123` | Form 10 Hazardous Waste Manifests, spent solvents, off-spec APIs, MSDS documents |
| **🚛 Waste Provider** | Authorized CBWTF / TSDF | `provider@wasteconnect.in` | `password123` | Review requests, propose pickup schedules, log weighbridge slips, record collected weight |
| **🏭 TSDF Operator** | Hazardous TSDF Operator | `tsdf@wasteconnect.in` | `password123` | Cement kiln co-processing, rotary kiln incineration, issue destruction certificates |
| **🛡️ Administrator** | Central Regulatory Authority | `admin@wasteconnect.in` | `password123` | Verify SPCB provider permits, approve/suspend accounts, monitor system audit logs |

---

## 🔄 Complete Service Request Lifecycle

The application enforces strict, auditable status transitions with timestamping and user tracking:

```
[Draft] ➔ [Submitted] ➔ [Under Review] ➔ [Accepted] ➔ [Pickup Scheduled] ➔ [Collected] ➔ [Received at Facility] ➔ [Completed]
                                   ↘ [Rejected]                                                     ↘ [Cancelled]
```

1. **Submission**: Hospital or Pharma initiates consignment with category, estimated weight, packaging, storage requirements, and pickup address.
2. **Provider Matching**: Rule-based matching evaluates provider verification status, SPCB category authorization, and service area coverage.
3. **Provider Review & Schedule**: Provider reviews specs and accepts with proposed date, time slot, vehicle registration number, and driver details (or rejects with reason).
4. **Schedule Confirmation**: Generator confirms the scheduled collection.
5. **Collection**: Provider arrives on-site, records actual electronic weighbridge weight (kg), container count, and weighbridge slip number.
6. **Facility Receipt**: Consignment gate pass verified upon arrival at treatment facility.
7. **Disposal & Closure**: Waste treated via incineration, autoclaving, or co-processing, and a formal Destruction Certificate is archived.

---

## 🏛️ India-Specific Design & Regulatory Considerations

1. **Biomedical vs Industrial Hazardous Separation**:
   - Hospitals can only submit Bio-Medical categories (Yellow, Red, White, Blue per BMW Rules 2016 Schedule I).
   - Pharmaceutical manufacturers can only submit industrial hazardous categories (Spent Solvents, Off-Spec APIs, ETP Sludge, Cytotoxic residues per Hazardous Waste Rules 2016).
2. **Statutory Manifests**:
   - Bio-Medical requests receive CPCB tracking numbers (`CPCB-BMW-2026-XXXX`).
   - Pharmaceutical hazardous requests receive statutory 7-copy Form 10 Manifest references (`FORM10-HAZ-2026-XXXX`).
3. **Provider Eligibility & Authorization**:
   - Provider authorizations are recorded on a per-category basis with SPCB permit numbers and expiry dates.
   - Pending, rejected, or unverified providers are strictly excluded from generator search results.
4. **Statutory Non-Certification Disclaimer**:
   - WasteConnect India coordinates digital information and compliance records. It does not physically transport, store, or dispose of waste. Physical custody and legal compliance remain the responsibility of licensed generators, transporters, and TSDF operators.

---

## 🧪 Automated Test Suite (Section 14 Tests A through I)

The project includes an automated test runner validating all 9 mandatory test scenarios:

- **Test A**: Hospital creates a request and submits it to an eligible verified CBWTF provider.
- **Test B**: Pharmaceutical company creates a manufacturing waste request; biomedical providers are excluded and only suitable TSDF providers are matched.
- **Test C**: Provider reviews request, accepts it, and proposes a schedule.
- **Test D**: Customer confirms the schedule.
- **Test E**: Provider updates status to Collected and records actual collected weight (kg).
- **Test F**: Customer accesses updated request, weighbridge slips, and documents.
- **Test G**: Administrator verifies a pending provider and updates its status.
- **Test H**: Unauthorized organizations attempting to access another organization's consignment are denied (403 Forbidden).
- **Test I**: Unverified / pending providers are strictly excluded from eligible provider search results.

To execute the test suite:
```powershell
node server/tests/workflow.test.js
```

---

## 🚀 How to Run the Application Locally

### Prerequisites
- Node.js (v18+ or the included portable runtime in `scratch\node-v20.18.0-win-x64`)

### Option 1: One-Click Windows Launch Script
Double-click `run.bat` or run:
```cmd
run.bat
```

### Option 2: PowerShell Script
```powershell
.\start.ps1
```

### Option 3: Manual Command Line
```powershell
# Set Node in PATH if using portable installation:
$env:PATH = "C:\Users\PRASANTH\.gemini\antigravity\scratch\node-v20.18.0-win-x64;" + $env:PATH

# Start backend server (serves REST API and compiled React frontend):
node server/index.js
```

### Option 4: Development Mode with Vite HMR
```powershell
# Terminal 1: Backend API
node server/index.js

# Terminal 2: Vite Dev Server
npm run dev
```

Open your browser to:
👉 **`http://localhost:5000`** (or `http://localhost:3000` for Vite dev server)

---

## 📁 Repository Structure

```
wasteconnect-india/
├── server/
│   ├── index.js                  # Express backend & static frontend server
│   ├── db/
│   │   ├── connection.js         # SQLite database engine, Drizzle connection, table definitions
│   │   ├── schema.js             # Drizzle ORM relational schema
│   │   └── seed.js               # Demonstration seed data (hospitals, pharma, providers, admin)
│   ├── middleware/
│   │   ├── auth.js               # JWT authentication & role-based access control
│   │   └── upload.js             # Multer document upload middleware
│   ├── routes/
│   │   ├── auth.js               # Login, registration, demo-login, session endpoints
│   │   ├── categories.js         # Waste category catalogue & regulatory metadata
│   │   ├── providers.js          # Provider directory & matching endpoints
│   │   ├── requests.js           # Consignment creation, status transition workflow, history
│   │   ├── messages.js           # In-app request communication
│   │   ├── documents.js          # File upload & document vault access
│   │   ├── admin.js              # Provider verification & audit log routes
│   │   └── stats.js              # Role-specific dashboard analytics
│   ├── services/
│   │   ├── providerMatching.js   # Rule-based statutory provider matching engine
│   │   └── auditLogger.js        # Immutable regulatory audit logger
│   └── tests/
│       └── workflow.test.js      # Automated test suite (Tests A through I)
├── src/
│   ├── components/
│   │   ├── Navbar.tsx            # Header with role badge, demo switcher & notifications
│   │   ├── Sidebar.tsx           # Role-tailored platform navigation
│   │   ├── Modal.tsx             # Accessible modal dialogue
│   │   ├── Stepper.tsx           # Consignment progress timeline stepper
│   │   ├── StatusBadge.tsx       # Standardized request status pills
│   │   ├── WasteCategoryBadge.tsx# Color-coded waste stream badges
│   │   ├── CreateRequestModal.tsx# Consignment creation modal with live matching
│   │   ├── RequestDetailModal.tsx# Comprehensive consignment inspection & workflow console
│   │   ├── ProviderDirectory.tsx # SPCB provider directory & matching simulator
│   │   ├── DocumentVault.tsx     # Manifest & MSDS document repository
│   │   └── NotificationsDrawer.tsx# Side-sheet notification center
│   ├── context/
│   │   └── AuthContext.tsx       # Authentication state, session restore, 1-click demo switcher
│   ├── pages/
│   │   ├── Login.tsx             # Authentication, registration & 1-click persona cards
│   │   ├── HospitalDashboard.tsx # Hospital biomedical metrics & recent pickups
│   │   ├── PharmaDashboard.tsx   # Pharma hazardous Form 10 tracking & solvent metrics
│   │   ├── ProviderDashboard.tsx # CBWTF/TSDF operations, capacity meter & dispatch queue
│   │   ├── AdminDashboard.tsx    # CPCB regulator analytics, verification queue & audit stream
│   │   └── RequestsList.tsx      # Filterable consignments table & search
│   ├── services/
│   │   └── api.ts                # Typed frontend API client
│   ├── types/
│   │   └── index.ts              # TypeScript domain interfaces
│   ├── App.tsx                   # Main root application shell
│   ├── index.css                 # Tailwind CSS styles & custom scrollbars
│   └── main.tsx                  # Vite React entry point
├── dist/                         # Compiled production bundle
├── uploads/                      # Uploaded consignment manifests & MSDS documents
├── wasteconnect_v2.db            # Persistent relational SQLite database
├── package.json                  # Dependencies & scripts
├── run.bat                       # Windows one-click batch launcher
├── start.ps1                     # PowerShell launcher
└── README.md                     # Documentation & specification
```
