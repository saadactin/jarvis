# Frontend UI Migration Configuration Guide

## Complete Configuration for Zoho to ClickHouse Migration

### Prerequisites Check

Before starting, ensure these services are running:

1. **Main Backend (jarvis-main)**: `http://localhost:5009`
2. **Universal Migration Service**: `http://localhost:5011`
3. **Frontend**: Open in your browser

---

## Step-by-Step Frontend Configuration

### Step 1: Access the Frontend

1. Open your browser and navigate to the frontend (usually `file:///` path or local server)
2. Login or Register if you haven't already

### Step 2: Verify Services (Optional)

1. Go to **Service Manager** page from sidebar

2. Check that "Universal Migration Service" shows status: **Running** (green badge)

3. If not running, click **"Start"** button

### Step 3: Create Migration Operation

Navigate to **Operations** → **Create Operation**

#### Step 1: Select Source
- **Click on:** `Zoho CRM` ☁️
- Click **Next**

#### Step 2: Select Destination
- **Click on:** `ClickHouse` 📊
- Click **Next**

#### Step 3: Source Configuration (Zoho)

Enter the following values:

```
Refresh Token: 1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4

Client ID: 1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT

Client Secret: d99c479d4c0db451c653d8c380bf6a4c557a73528c

API Domain: Select "India (https://www.zohoapis.in)" from dropdown
```

**Note:** The API Domain dropdown should show:
- US (https://www.zohoapis.com)
- **India (https://www.zohoapis.in)** ← Select this one
- Europe (https://www.zohoapis.eu)
- Australia (https://www.zohoapis.com.au)
- Japan (https://www.zohoapis.jp)

Click **Next**

#### Step 4: Destination Configuration (ClickHouse)

Enter the following values:

```
Host: 74.225.251.123

Port: 8123

Database: test6

Username: default

Password: root
```

**Note:** Port 8123 is already set as default - just verify it's correct.

Click **Next**

#### Step 5: Schedule & Type

```
Operation Type: Select "Full Migration"

Schedule Date: (Select today's date)

Schedule Time: (Select current time or a few minutes from now)

Last Sync Time: (Leave empty - only for incremental migrations)
```

Click **Next**

#### Step 6: Review

1. Review all your settings
2. Verify:
   - Source: Zoho CRM
   - Destination: ClickHouse
   - All credentials are correct
3. Click **"Create Operation"**

### Step 4: Execute the Migration

After creating the operation:

1. You'll be redirected to the **Operation Detail** page
2. Click **"Execute Now"** button (or wait for scheduled time)
3. The operation status will change to **"Running"**
4. Monitor progress on the same page

### Step 5: Monitor Progress

The Operation Detail page will show:
- **Status**: Running → Completed/Failed
- **Progress**: Real-time updates
- **Migration Results**: 
  - Total tables found
  - Tables migrated successfully
  - Tables failed (if any)
  - Records migrated

---

## Quick Reference: All Configuration Values

### Zoho Source Configuration
| Field | Value |
|-------|-------|
| Refresh Token | `1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4` |
| Client ID | `1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT` |
| Client Secret | `d99c479d4c0db451c653d8c380bf6a4c557a73528c` |
| API Domain | `https://www.zohoapis.in` (India) |

### ClickHouse Destination Configuration
| Field | Value |
|-------|-------|
| Host | `74.225.251.123` |
| Port | `8123` |
| Database | `test6` |
| Username | `default` |
| Password | `root` |

### Operation Settings
| Field | Value |
|-------|-------|
| Operation Type | `Full Migration` |
| Schedule | Current date/time (or future) |
| Last Sync Time | (Leave empty) |

---

## Troubleshooting

### Issue: "Universal Migration Service not found"
**Solution:** 
1. Go to **Database Masters** page
2. Click **"Add Database Master"**
3. Enter:
   - Name: `Universal Migration Service`
   - Service URL: `http://localhost:5011`
4. Click **Save**

### Issue: Service not running
**Solution:**
1. Go to **Service Manager** page
2. Find "Universal Migration Service"
3. Click **"Start"** button
4. Wait for status to change to "Running"

### Issue: Connection test fails
**Solution:**
- Verify all credentials are correct
- Check that Universal Migration Service is running on port 5011
- Check network connectivity to ClickHouse (74.225.251.123:8123)

---

## Expected Results

After migration completes, you should see:
- **Status**: Completed (green badge)
- **Total Tables**: ~76 (all Zoho modules)
- **Tables Migrated**: Most or all tables
- **Records Migrated**: Varies based on your Zoho data

Tables will be created in ClickHouse with prefix `zoho_` (e.g., `zoho_accounts`, `zoho_contacts`)

---

## Service URLs Reference

- **Main Backend**: `http://localhost:5009`
- **Universal Migration Service**: `http://localhost:5011`
- **Frontend**: Your local file path or server

---

## Next Steps After Migration

1. **Verify Data**: Check ClickHouse database `test6` for tables with `zoho_` prefix
2. **View Results**: Check the Operation Detail page for detailed migration results
3. **Retry Failed Tables**: If any tables failed, you can retry them individually
4. **Schedule Incremental**: Set up incremental migrations for regular syncs

