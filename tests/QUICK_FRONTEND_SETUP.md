# Quick Frontend Setup - Zoho to ClickHouse Migration

## ✅ All Services Status

### Service URLs
- **Main Backend**: `http://localhost:5009` (jarvis-main)
- **Universal Migration Service**: `http://localhost:5011` (universal_migration_service)
- **Frontend**: Open `frontend/index.html` in your browser

---

## 📋 Exact Configuration Values for Frontend UI

### Step 1: Source Configuration (Zoho CRM)

When you reach **Step 3: Source Configuration** in the Create Operation wizard, enter:

```
Refresh Token:
1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4

Client ID:
1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT

Client Secret:
d99c479d4c0db451c653d8c380bf6a4c557a73528c

API Domain:
Select from dropdown: "India (https://www.zohoapis.in)"
```

### Step 2: Destination Configuration (ClickHouse)

When you reach **Step 4: Destination Configuration**, enter:

```
Host:
74.225.251.123

Port:
8123
(Already set as default - just verify)

Database:
test6

Username:
default
(Already set as default - just verify)

Password:
root
```

### Step 3: Operation Settings

```
Operation Type:
Full Migration

Schedule Date:
(Today's date)

Schedule Time:
(Current time or a few minutes from now)

Last Sync Time:
(Leave empty - only for incremental)
```

---

## 🚀 Quick Start Checklist

### Before Starting Migration:

1. ✅ **Universal Migration Service Running**
   - Check: `http://localhost:5011/health`
   - Should return: `{"status": "healthy", ...}`

2. ✅ **Main Backend Running**
   - Check: `http://localhost:5009/health`
   - Should return: `{"status": "ok"}`

3. ✅ **Database Master Registered**
   - Go to: **Database Masters** page
   - Should see: "Universal Migration Service" with URL `http://localhost:5011`
   - If not, add it manually:
     - Name: `Universal Migration Service`
     - URL: `http://localhost:5011`

---

## 📝 Step-by-Step Frontend Flow

1. **Open Frontend**
   - Navigate to `frontend/index.html` in browser
   - Or open via local server

2. **Login/Register**
   - Create account or login

3. **Go to Operations**
   - Click "Operations" in sidebar
   - Click "Create Operation" button

4. **Wizard Steps:**
   - **Step 1**: Click "Zoho CRM" → Next
   - **Step 2**: Click "ClickHouse" → Next
   - **Step 3**: Enter Zoho credentials (see above) → Next
   - **Step 4**: Enter ClickHouse credentials (see above) → Next
   - **Step 5**: Select "Full Migration", set schedule → Next
   - **Step 6**: Review → Click "Create Operation"

5. **Execute Migration**
   - On Operation Detail page, click "Execute Now"
   - Or wait for scheduled time

6. **Monitor Progress**
   - Watch status change: Pending → Running → Completed
   - View migration results and statistics

---

## 🔍 Verification Commands

Run these in PowerShell to verify services:

```powershell
# Check Universal Migration Service
Invoke-WebRequest -Uri http://localhost:5011/health -UseBasicParsing

# Check Main Backend
Invoke-WebRequest -Uri http://localhost:5009/health -UseBasicParsing

# Check if ports are open
Get-NetTCPConnection -LocalPort 5011 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 5009 -ErrorAction SilentlyContinue
```

---

## ⚠️ Common Issues & Solutions

### Issue: "Universal Migration Service not found"
**Fix:**
1. Go to **Database Masters** page
2. Click **"Add Database Master"**
3. Enter:
   - Name: `Universal Migration Service`
   - Service URL: `http://localhost:5011`
4. Click **Save**

### Issue: Service shows "Stopped"
**Fix:**
1. Go to **Service Manager** page
2. Find "Universal Migration Service"
3. Click **"Start"** button
4. Wait for status to change to "Running"

### Issue: Connection test fails
**Fix:**
- Double-check all credentials are entered correctly
- Verify no extra spaces in fields
- Check that Universal Migration Service is running

---

## 📊 Expected Migration Results

After successful migration:
- **Status**: Completed (green badge)
- **Total Tables**: ~76 Zoho modules
- **Tables Migrated**: Most or all tables
- **ClickHouse Tables**: Created with `zoho_` prefix (e.g., `zoho_accounts`)

---

## 🎯 Summary

**All Configuration Values:**

| Category | Field | Value |
|----------|-------|-------|
| **Zoho** | Refresh Token | `1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4` |
| | Client ID | `1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT` |
| | Client Secret | `d99c479d4c0db451c653d8c380bf6a4c557a73528c` |
| | API Domain | `https://www.zohoapis.in` (India) |
| **ClickHouse** | Host | `74.225.251.123` |
| | Port | `8123` |
| | Database | `test6` |
| | Username | `default` |
| | Password | `root` |
| **Operation** | Type | `Full Migration` |
| | Schedule | Current date/time |

**Service URLs:**
- Main Backend: `http://localhost:5009`
- Universal Migration Service: `http://localhost:5011`

Everything is ready! Just follow the wizard steps and enter the values above.

