# 🌾 RationSmart – Intelligent PDS Distribution & Beneficiary Transparency Platform

**Base Project:** Digital Ration Shop Sales Recording and PDS Grain Allocation Tracking Portal  
**Academic Target:** S7 CSE Mini Project & Hackathon Prototype  
**Tech Stack:** Python (Flask), MySQL / SQLite, HTML5, CSS3, Bootstrap 5, Vanilla JavaScript, Chart.js

---

## 📌 1. Project Overview

**RationSmart** is an intelligent, transparent Public Distribution System (PDS) portal designed to eliminate foodgrain diversion, streamline Fair Price Shop (FPS) inventory, calculate accurate monthly household entitlements under the National Food Security Act (NFSA), prevent over-distribution, and provide complete public transparency to citizens.

### 🌟 Key Modules & Features
1. **Admin Analytics Dashboard:**
   - Central overview with key metrics: Total Fair Price Shops, enrolled cardholders, monthly distributed grains (kg/L), and low-stock alert counters.
   - Interactive **Chart.js** visualizations for monthly commodity distribution trends and cardholder demographics.
2. **Fair Price Shop (FPS) Management:**
   - Shop registration, dealer assignment, license number verification, ward mapping, and active status tracking.
3. **Beneficiary & Ration Card Registry:**
   - Classification across NFSA categories:
     - 🟡 **AAY (Antyodaya Anna Yojana)**: Poorest households (Flat 35 kg grain quota).
     - 🌸 **PHH (Priority Household)**: 5 kg grains per member (3kg Rice + 2kg Wheat per head).
     - ⚪ **NPHH (Non-Priority Household)**: Subsidized allocation.
     - 🟢 **AY (Annapurna Yojana)**: 10 kg 100% free foodgrains for indigent senior citizens.
4. **PDS Grain Allocation Tracking:**
   - Dispatches from District Central Godown to Fair Price Shops with automatic shop stock replenishment upon receipt.
5. **Real-time Stock Health & Depletion Monitor:**
   - Real-time stock balance tracking per shop and commodity.
   - **Low-Stock Warnings** (< 150 kg or custom threshold).
   - **Depletion Forecast**: Estimates remaining days until stockout based on assigned cardholders and daily consumption rate.
6. **Dealer Point of Sale (POS) Terminal:**
   - Rapid card search by Card Number, Mobile, or Aadhaar.
   - Real-time entitlement and remaining monthly quota calculation.
   - Dynamic cart calculation, simulated biometric/Aadhaar OTP authentication.
   - Real-time inventory deduction and instant generation of printable digital **e-Ration receipts**.
7. **Citizen Transparency & Purchase History:**
   - Public portal where any citizen can look up their ration card to check live entitlement balance, view live inventory at their assigned FPS shop, download verified digital bill receipts, and submit grievances.
8. **Rule-Based Anomaly & Vigilance Radar:**
   - Automated detection for:
     - 🚨 **Over-Quota Distribution Attempts**
     - 🚨 **Rapid Duplicate Transactions** (< 24 hours for same card)
     - 🚨 **Off-Hours Sales** (outside 07:00 AM - 08:00 PM)
     - 🚨 **Stock Inconsistencies / Deficit Sales**
9. **Citizen Grievance Redressal Center:**
   - Lodging complaints and official resolution tracking with status updates.
10. **Reports & Exports:**
    - Monthly commodity outflow summaries and Fair Price Shop performance registers with one-click print/export.

---

## 📂 2. Project File Structure

```text
digital-ration-portal/
├── app.py                     # Main Flask application with all routes, APIs, and auth
├── config.py                  # App configuration, MySQL/SQLite connection strings
├── models.py                  # SQLAlchemy database schema (10 tables with relationships)
├── rules.py                   # Entitlement engine, stock depletion, & anomaly detector
├── seed_data.py               # Auto-seeder with realistic PDS demo data
├── database.sql               # Full raw MySQL database schema and SQL seed insert statements
├── test_app.py                # Automated unittest suite verifying all modules and business logic
├── run.py                     # Easy application startup launcher
├── requirements.txt           # Python library dependencies
├── .env                       # Environment configuration file
├── .env.example               # Template environment configuration file
├── static/
│   ├── css/
│   │   └── style.css          # Government portal styling, responsive cards, print CSS
│   └── js/
│       └── main.js            # POS calculator, quota validation, and Chart.js integration
└── templates/
    ├── base.html              # Master layout with topbar, navbar, flash alerts, footer
    ├── index.html             # Landing page with hero search, counters, norms, shop directory
    ├── auth/
    │   └── login.html         # Official login portal with 1-click demo autofill
    ├── citizen/
    │   └── portal.html        # Citizen transparency hub, quota meters, stock, grievances
    ├── dealer/
    │   ├── pos.html           # Dealer POS sales counter & cart
    │   ├── stock.html         # Shop stock inventory & depletion forecast
    │   └── sales_history.html # Dealer sales register
    ├── admin/
    │   ├── dashboard.html     # Admin analytics dashboard with Chart.js
    │   ├── shops.html         # Fair Price Shops CRUD
    │   ├── beneficiaries.html # Beneficiary ration card directory & filters
    │   ├── allocations.html   # Central Godown grain dispatches
    │   ├── stock.html         # District-wide stock health monitor
    │   ├── anomalies.html     # Rule-based vigilance & anomaly logs
    │   ├── grievances.html    # Grievance redressal center
    │   └── reports.html       # Monthly reports & shop performance
    └── reports/
        └── receipt.html       # Official printable e-Ration digital cash memo
```

---

## ⚙️ 3. Installation & Setup

### Step 1: Open in VS Code Terminal
Ensure Python 3.8+ is installed on your system.

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

---

## 🗄️ 4. Database Setup

### Option A: Out-of-the-Box SQLite (Zero Setup - Recommended for Instant Demo)
The application is pre-configured to run seamlessly with SQLite. On first startup, it automatically creates `rationsmart.db` and populates realistic demo shops, beneficiaries, stock, and transactions.

### Option B: Connecting to MySQL (XAMPP / MySQL Server / MariaDB)
1. Start your MySQL Server (e.g. via XAMPP Control Panel or MySQL Workbench).
2. Open MySQL prompt or phpMyAdmin and create the database:
   ```sql
   CREATE DATABASE rationsmart_db CHARACTER SET utf8mb4;
   ```
3. Import the provided SQL script:
   - In phpMyAdmin: Click `rationsmart_db` -> **Import** -> Select `database.sql` -> Click **Go**.
   - Or via MySQL CLI:
     ```bash
     mysql -u root -p rationsmart_db < database.sql
     ```
4. Update your `.env` file:
   ```env
   DB_TYPE=mysql
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=rationsmart_db
   ```

---

## 🚀 5. How to Run the Application

Execute the startup file:
```bash
python run.py
```
*(Or alternatively: `python app.py`)*

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 6. Demo Login Credentials

| Role | Username / Card Number | Password | Access / Function |
| :--- | :--- | :--- | :--- |
| **Admin (DFSO)** | `admin` | `admin123` | Full district dashboard, shop management, allocations, vigilance radar, reports |
| **Vigilance Inspector** | `inspector1` | `inspector123` | Anomaly investigation, stock health audit, shop surveillance |
| **Shop Dealer 1** | `dealer1` | `dealer123` | Fair Price Shop #101 POS billing counter, stock receipts, local offline sync |
| **Shop Dealer 2** | `dealer2` | `dealer123` | Fair Price Shop #102 POS counter (Ward 15) |
| **Citizen (AAY Card)** | `RC-AAY-1001` *(or `citizen1`)* | `citizen123` *(or `pass`)* | Munna Lal (AAY - 35 kg grain quota portal, e-receipts, grievance tracking) |
| **Citizen (PHH Card)** | `RC-PHH-2001` *(or `citizen2`)* | `citizen123` *(or `pass`)* | Suresh Babu (PHH - 5 kg/member scaling, entitlement meter) |
| **Citizen (AY Card)** | `RC-AY-4001` *(or `citizen3`)* | `citizen123` *(or `pass`)* | Ramachandra Rao (Annapurna Senior Citizen - 100% free grains) |

---

## 🧪 7. How to Test & Demonstrate Each Module

### 1. Citizen Transparency Test:
1. Open the homepage (`http://127.0.0.1:5000`).
2. In the citizen search bar, enter sample card **`RC-AAY-1001`** or **`RC-PHH-2001`**.
3. Observe:
   - Beneficiary details and card type badge.
   - Monthly entitlement progress bars (Entitled vs Claimed vs Remaining).
   - Live stock availability at their assigned Fair Price Shop.
   - Complete purchase history with **"e-Receipt"** buttons.
   - Lodge a grievance and get an instant tracking ID.

### 2. Dealer POS Sales Distribution Test:
1. Click **Official Login** -> Choose **Shop Dealer 1** (or login with `dealer1` / `dealer123`).
2. Search beneficiary card **`RC-AAY-1002`** (Devaki Ammal).
3. The system shows remaining entitlement (20kg Rice, 15kg Wheat).
4. Enter quantities (e.g. 10 kg Rice, 5 kg Wheat), select Biometric Aadhaar Authentication, and click **Record Distribution**.
5. The system generates an official **e-Ration Digital Receipt** and instantly decrements the shop's live inventory.
6. Try entering 30 kg Rice to test **Policy Protection**: the POS will block the over-quota entry and flag it on the anomaly radar!

### 3. Admin Analytics & Stock Health Test:
1. Login as **Admin** (`admin` / `admin123`).
2. Go to **Dashboard** to view Chart.js distribution analytics, KPI counters, and live anomaly feed.
3. Go to **Stock Health** to see all shops, safety thresholds, and **Depletion Forecasts** (estimated days left before stockout).
4. Go to **Allocations** to dispatch grain consignments from the Central Godown to any Fair Price Shop.
5. Go to **Anomalies** to review rule-triggered flags with severity levels and enter official investigation notes.
6. Go to **Reports** to view printable monthly commodity summaries and shop performance tables.

### 4. Running Automated Unit Tests:
Run the complete automated test suite across all modules:
```bash
python -m unittest discover -s . -p "test_*.py"
```
Or execute individual verification suites:
```bash
python -m unittest test_app.py test_login_redesign.py test_customer_quota_table_ui.py test_production_login_render_fix.py
python verify_pwa_offline_system.py
python verify_qr_complaint_system.py
```
All unit tests covering authentication, database bootstrap, PWA offline sync idempotency, responsive table layout, QR complaint tracking, and NFSA entitlement calculations will execute and verify with `OK`.

---

## 🎓 College Review & Viva Tips (Honest Architectural Grounds)
- **Why Flask & SQLite/PostgreSQL?** Clean, standard Python backend that provides ACID transaction guarantees (`db.session.rollback()` on stock shortages or policy violations) without excessive microservice bloat.
- **How does Offline PWA Mode work?** Built using browser-native Service Worker (`/sw.js`) and client-side IndexedDB (`RationSmartPWA`). When offline, the dealer terminal queues transactions with unique UUID client sale keys (`clientSaleId`). Upon reconnection, an idempotent bulk-sync endpoint (`/api/sales/bulk-sync`) commits valid sales and deduplicates already-processed bills.
- **How is forecasting implemented?** Uses deterministic historical consumption rate analytics (`estimate_stock_depletion` and `calculate_demand_forecast` in `rules.py`), calculating average daily outflows from completed ledger items to predict days until safety stock thresholds are reached. It is an algorithmic moving-average formula, not a black-box AI model.
- **How are remaining quotas tracked?** Calculated dynamically on-demand from completed transaction records in the active calendar month period (`month_period = 'YYYY-MM'`), eliminating multi-counter desynchronization.
- **What are the security boundaries?** Centralized append-only audit logging (`audit_service.py`) with sensitive credential redaction (`[REDACTED]`), formula-injection escaping for CSV exports, role-based decorators (`@role_required`), and shop-boundary enforcement ensuring dealers can only access cards assigned to their registered Fair Price Shop.
