# 🔄 Africa's Talking → BRIQ SMS Gateway Migration

> **Project:** Smart ID Card Distribution Kiosk  
> **Task:** Replace Africa's Talking SDK with BRIQ Solutions REST API  
> **Scope:** SMS gateway only (Email/SMTP remains untouched)  
> **Estimated Total Time:** ~4 hours  
> **Impact:** Phase 3 (Authentication & SMS) stabilization

---

## Overall Migration Progress

```text
Configuration Update          [░░░░░░░░░░░░░░░░░░░░]   0%
SMS Client Refactor           [░░░░░░░░░░░░░░░░░░░░]   0%
Auth Module Updates           [░░░░░░░░░░░░░░░░░░░░]   0%
Dependencies & Testing        [░░░░░░░░░░░░░░░░░░░░]   0%
```

---

## Migration Overview

**Current State:**

- ✅ Email delivery working (SMTP via Gmail)
- ❌ SMS delivery failing (Africa's Talking blocked/non-responsive)
- ✅ All function names are generic (no SDK branding in signatures)

**Target State:**

- ✅ Email delivery unchanged (SMTP via Gmail)
- ✅ SMS delivery working (BRIQ Solutions REST API)
- ✅ Function names unchanged (internal SMS implementation swapped)
- ✅ No breaking changes to auth.py or test_auth.py

**Key Principle:** Replace only SMS implementation. Email and function architecture remain untouched.

---

---

## Task 1 — Configuration Update

> **Estimated Time:** ~0.5 hours  
> **Goal:** Remove Africa's Talking credentials, add BRIQ credentials to config files.  
> **Deliverable:** Updated config.py and config.example.py with BRIQ settings.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 1.1 — Update [kiosk_brain/config.py](kiosk_brain/config.py)

**Changes:**

- [ ] **1.1.1** Remove `AFRICA_TALKING_API_KEY` constant _(5 min)_
- [ ] **1.1.2** Remove `AFRICA_TALKING_USERNAME` constant _(5 min)_
- [ ] **1.1.3** Add `BRIQ_API_KEY = "your-briq-api-key"` _(2 min)_
- [ ] **1.1.4** Add `BRIQ_API_ENDPOINT = "https://api.briq.io/api/send-sms"` (confirm actual endpoint) _(3 min)_
- [ ] **1.1.5** Add `BRIQ_SENDER_ID = "CARD-KIOSK"` (or appropriate sender name) _(2 min)_
- [ ] **1.1.6** Verify all SMTP settings remain unchanged: `SMTP_EMAIL`, `APP_PASSWORD` _(3 min)_

**Verification:**

- [ ] Python can import config without syntax errors: `python3 -c "from config import BRIQ_API_KEY, BRIQ_API_ENDPOINT, BRIQ_SENDER_ID; print('OK')"`
- [ ] Confirm old Africa's Talking constants are gone: `python3 -c "from config import AFRICA_TALKING_API_KEY"` should raise `ImportError`

#### Subtotal: ~0.25 hrs

---

### Task 1.2 — Update [kiosk_brain/config.example.py](kiosk_brain/config.example.py)

**Changes:**

- [ ] **1.2.1** Remove Africa's Talking section and setup instructions _(5 min)_
- [ ] **1.2.2** Add BRIQ setup instructions section:

  ```python
  # BRIQ Solutions SMS Gateway Configuration
  # 1. Sign up for BRIQ account at https://briq.io
  # 2. Retrieve API key from dashboard
  # 3. Set BRIQ_API_KEY and BRIQ_API_ENDPOINT below
  ```

  _(5 min)_

- [ ] **1.2.3** Add example BRIQ constants (with placeholder values) _(5 min)_
- [ ] **1.2.4** Keep all SMTP configuration as-is with no changes _(2 min)_

**Verification:**

- [ ] File is syntactically valid Python: `python3 -m py_compile config.example.py`
- [ ] Docstring/comments are clear for new developers

#### Subtotal: ~0.25 hrs

---

**Phase 1 Summary:** Configuration files updated. BRIQ credentials externalized. SMTP untouched.

---

---

## Task 2 — Refactor SMS Client Module

> **Estimated Time:** ~1.5 hours  
> **Goal:** Replace Africa's Talking SDK calls with BRIQ REST API calls. Email logic remains 100% untouched.  
> **Deliverable:** [kiosk_brain/modules/sms_client.py](kiosk_brain/modules/sms_client.py) with BRIQ integration.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 2.1 — Update Imports (Lines 1–10)

**Current:**

```python
from config import (
    AFRICA_TALKING_API_KEY,
    AFRICA_TALKING_USERNAME,
    SMTP_EMAIL,
    APP_PASSWORD,
)
from email.mime.text import MIMEText
import africastalking
import smtplib
import sqlite3
```

**Changes:**

- [ ] **2.1.1** Remove `AFRICA_TALKING_API_KEY` from config import _(2 min)_
- [ ] **2.1.2** Remove `AFRICA_TALKING_USERNAME` from config import _(2 min)_
- [ ] **2.1.3** Add `BRIQ_API_KEY`, `BRIQ_API_ENDPOINT`, `BRIQ_SENDER_ID` to config import _(3 min)_
- [ ] **2.1.4** Delete `import africastalking` line _(1 min)_
- [ ] **2.1.5** Add `import requests` (already in requirements.txt) _(1 min)_
- [ ] **2.1.6** Verify email imports remain: `from email.mime.text import MIMEText`, `import smtplib`, `import sqlite3` _(1 min)_

**Verification:**

- [ ] No syntax errors: `python3 -m py_compile modules/sms_client.py`
- [ ] Imports resolve: `python3 -c "from modules.sms_client import *; print('OK')"`

#### Subtotal: ~0.25 hrs

---

### Task 2.2 — Refactor `send_credentials()` Function — SMS Block (Lines 43–74)

> **Critical:** Only modify SMS section. Email block (lines 75–113) is completely untouched.

**Current Africa's Talking Block:**

```python
africastalking.initialize(AFRICA_TALKING_USERNAME, AFRICA_TALKING_API_KEY)
sms = africastalking.SMS
response = sms.send(sms_message, [phone_number])

# Handle Africa's Talking SMS response
sms_sent = False
sms_error = None
try:
    if "SMSMessageData" in response:
        sms_data = response["SMSMessageData"]
        # ... complex response parsing (15+ lines)
except Exception as e:
    sms_sent = False
    sms_error = f"SMS error: {str(e)}"
```

**Changes:**

- [ ] **2.2.1** Delete lines 43–44: `africastalking.initialize(...)` and `sms = africastalking.SMS` _(2 min)_
- [ ] **2.2.2** Replace lines 45: `response = sms.send(...)` with BRIQ HTTP POST:

  ```python
  headers = {"Authorization": f"Bearer {BRIQ_API_KEY}"}
  payload = {"phone": phone_number, "message": sms_message}
  try:
      response = requests.post(BRIQ_API_ENDPOINT, json=payload, headers=headers)
      response_data = response.json()
  except requests.exceptions.RequestException as e:
      response_data = {"success": False, "message": str(e)}
  ```

  _(5 min)_

- [ ] **2.2.3** Delete lines 47–74 (old Africa's Talking response parsing, ~28 lines) _(2 min)_
- [ ] **2.2.4** Replace with simplified BRIQ response parsing:

  ```python
  sms_sent = False
  sms_error = None
  try:
      if response_data.get("success") and response_data.get("status_code") == 200:
          sms_sent = True
      else:
          sms_error = response_data.get("message", "Unknown error")
  except Exception as e:
      sms_sent = False
      sms_error = f"SMS error: {str(e)}"
  ```

  _(5 min)_

- [ ] **2.2.5** **DO NOT TOUCH** lines 75–113 (email block) _(0 min)_

**Result:**

- Lines 1–42: Function header, database query, message template construction — **UNCHANGED**
- Lines 43–74: SMS block — **REPLACED** (Africa's Talking → BRIQ)
- Lines 75–113: Email block — **UNTOUCHED** (SMTP logic identical)
- Lines 114–121: Return statement — **UNCHANGED**

**Verification:**

- [ ] No syntax errors: `python3 -m py_compile modules/sms_client.py`
- [ ] Function signature unchanged: `send_credentials(reg_num, otp, temp_pin=None, db_path="data/kiosk.db")`
- [ ] Return dict structure unchanged: `{"success", "sms_sent", "email_sent", "sms_error", "email_error"}`
- [ ] Email block still has all original SMTP code

#### Subtotal: ~0.75 hrs

---

### Task 2.3 — Code Review

- [ ] **2.3.1** Verify SMS block uses BRIQ credentials from config _(2 min)_
- [ ] **2.3.2** Verify email block is 100% unchanged from original _(2 min)_
- [ ] **2.3.3** Verify message templates (OTP + temp PIN) are unchanged _(2 min)_
- [ ] **2.3.4** Verify error handling covers network failures _(2 min)_
- [ ] **2.3.5** Verify return dict keys remain the same _(1 min)_

**Verification:**

- [ ] Full module imports without errors: `python3 -c "import modules.sms_client; print('OK')"`

#### Subtotal: ~0.25 hrs

---

**Phase 2 Summary:** SMS implementation replaced. Email untouched. Function interface preserved.

---

---

## Task 3 — Update Dependencies

> **Estimated Time:** ~0.25 hours  
> **Goal:** Remove Africa's Talking from requirements, verify requests is pinned.  
> **Deliverable:** Updated [kiosk_brain/requirements.txt](kiosk_brain/requirements.txt).

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 3.1 — Update [kiosk_brain/requirements.txt](kiosk_brain/requirements.txt)

**Current:**

```
africastalking==2.0.2
bcrypt==5.0.0
...
requests==2.33.0
...
```

**Changes:**

- [ ] **3.1.1** Delete line: `africastalking==2.0.2` _(2 min)_
- [ ] **3.1.2** Verify `requests>=2.33.0` is present (no change needed, already there) _(2 min)_
- [ ] **3.1.3** Verify no other SMS-related packages are listed _(2 min)_

**Verification:**

- [ ] File is valid pip format: `pip install -r requirements.txt --dry-run` (check for syntax errors)
- [ ] No Africa's Talking in final file: `grep -v "africastalking" requirements.txt | grep -i "africa"` should return nothing

#### Subtotal: ~0.25 hrs

---

**Phase 3 Summary:** Dependencies cleaned up. No new package additions needed.

---

---

## Task 4 — Update Auth Module (Minimal)

> **Estimated Time:** ~0.5 hours  
> **Goal:** Update [kiosk_brain/modules/auth.py](kiosk_brain/modules/auth.py) to handle SMS-only response format.  
> **Deliverable:** Updated retry logic that works with BRIQ SMS delivery.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 4.1 — Verify Function Signature Compatibility

- [ ] **4.1.1** Confirm `send_credentials(reg_number, otp, temp_pin, db_path)` signature is unchanged _(2 min)_
- [ ] **4.1.2** Confirm return dict still has keys: `{"success", "sms_sent", "email_sent", "sms_error", "email_error"}` _(2 min)_
- [ ] **4.1.3** Confirm no changes needed to `dispatch_credentials_with_logging()` function _(2 min)_
- [ ] **4.1.4** Confirm no changes needed to `retry_send_credentials()` function _(2 min)_

**Verification:**

- [ ] Tests import auth without errors: `python3 -c "from modules.auth import *; print('OK')"`

#### Subtotal: ~0.25 hrs

---

### Task 4.2 — Review Retry Logic (No Code Changes Expected)

- [ ] **4.2.1** Verify `dispatch_credentials_with_logging()` checks `if result["sms_sent"] or result["email_sent"]` — this logic works for BRIQ _(3 min)_
- [ ] **4.2.2** Verify `retry_send_credentials()` re-calls `send_credentials()` with same interface — still works _(2 min)_
- [ ] **4.2.3** Verify 10-minute rate limit and 24-hour OTP expiry are unchanged _(2 min)_

**Verification:**

- [ ] Module compiles: `python3 -m py_compile modules/auth.py`

#### Subtotal: ~0.25 hrs

---

**Phase 4 Summary:** Auth module compatibility verified. No changes required (function signatures preserved).

---

---

## Task 5 — Testing and Verification

> **Estimated Time:** ~1 hour  
> **Goal:** Ensure SMS delivery works via BRIQ without breaking email or auth logic.  
> **Deliverable:** Green test results confirming both SMS and email delivery.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 5.1 — Unit/Integration Test Compatibility

- [ ] **5.1.1** Run existing auth tests without modifications:

  ```bash
  python3 -m unittest tests.test_auth.Test361ReturningStudent -v
  ```

  _(5 min)_

- [ ] **5.1.2** Expected: Test passes, SMS now sent via BRIQ instead of Africa's Talking _(0 min)_
- [ ] **5.1.3** Run second auth test:

  ```bash
  python3 -m unittest tests.test_auth.Test362FirstYearStudent -v
  ```

  _(5 min)_

- [ ] **5.1.4** Expected: Test passes, temp PIN delivered via BRIQ SMS _(0 min)_

**Note:** No test code changes — tests call `send_credentials()` with same signature and check same return dict.

#### Subtotal: ~0.25 hrs

---

### Task 5.2 — Manual Verification

**Setup:**

- [ ] **5.2.1** Ensure BRIQ credentials are set in config.py _(2 min)_
- [ ] **5.2.2** Ensure both students in test*auth.py have valid BRIQ phone numbers configured *(2 min)\_

**Smoke Test:**

- [ ] **5.2.3** Run in Python shell:

  ```python
  from modules.sms_client import send_credentials
  result = send_credentials("2022-04-09050", "123456", temp_pin=None)
  print(result)
  ```

  _(5 min)_

- [ ] **5.2.4** Expected: `result["success"] == True` and `result["sms_sent"] == True` _(0 min)_
- [ ] **5.2.5** Check phone receives OTP text message from BRIQ _(5 min)_

**Email Verification:**

- [ ] **5.2.6** Check email address receives credential email from Gmail SMTP _(5 min)_
- [ ] **5.2.7** Expected: Email subject is "SMARTCARD OTP KIOSK" with OTP and temp PIN (if applicable) _(0 min)_

#### Subtotal: ~0.5 hrs

---

### Task 5.3 — Error Handling Test

- [ ] **5.3.1** Test with invalid phone number:

  ```python
  result = send_credentials("2022-04-09050", "123456", phone_override="invalid")
  ```

  _(5 min)_

- [ ] **5.3.2** Expected: `result["success"] == False`, `result["sms_error"]` contains error message _(0 min)_
- [ ] **5.3.3** Test with unreachable BRIQ endpoint (simulate by changing BRIQ_API_ENDPOINT):

  ```python
  # Temporarily change config.BRIQ_API_ENDPOINT = "http://invalid.example.com"
  result = send_credentials("2022-04-09050", "123456")
  ```

  _(5 min)_

- [ ] **5.3.4** Expected: Network error caught gracefully, return dict populated with error, no crash _(0 min)_

#### Subtotal: ~0.25 hrs

---

### Task 5.4 — Regression Check

- [ ] **5.4.1** Verify no Africa's Talking code remains in sms*client.py: `grep -i "africastalking" modules/sms_client.py` should return nothing *(2 min)\_
- [ ] **5.4.2** Verify email block in sms*client.py is unchanged from Phase 3 original *(3 min)\_
- [ ] **5.4.3** Verify all tests pass without modification to test code _(3 min)_

#### Subtotal: ~0.25 hrs

---

**Phase 5 Summary:** All tests pass. SMS delivered via BRIQ. Email delivered via SMTP. No regressions detected.

---

---

## Task 6 — Documentation Update (Optional, Recommended)

> **Estimated Time:** ~0.5 hours  
> **Goal:** Update project documentation to reflect SMS gateway change.  
> **Deliverable:** Updated README and code comments.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

### Task 6.1 — Update Code Commentary

- [ ] **6.1.1** Update comments in sms*client.py to mention BRIQ instead of Africa's Talking *(3 min)\_
- [ ] **6.1.2** Update comments in config.py to mention BRIQ setup _(2 min)_
- [ ] **6.1.3** Leave all email-related comments untouched _(0 min)_

#### Subtotal: ~0.1 hrs

---

### Task 6.2 — Update BUILD.md

- [ ] **6.2.1** Update BUILD.md Phase 3, Task 3.2.5 status:  
       Change: `⚠️ SMS blocked: Messages charged but not delivered — investigating carrier/account issue.`  
       To: `✅ SMS verified working via BRIQ Solutions.`  
       _(3 min)_

#### Subtotal: ~0.1 hrs

---

**Phase 6 Summary:** Documentation updated to reflect BRIQ migration. Maintenance notes added for future reference.

---

---

## Rollback Plan (If Needed)

> In case BRIQ integration fails catastrophically, here's how to restore:

- [ ] **R1.1** Git revert commit: `git revert <commit-hash-of-briq-changes>`
- [ ] **R1.2** Reinstall Africa's Talking: `pip install africastalking==2.0.2`
- [ ] **R1.3** Restore config.py from commit: `git checkout HEAD~1 config.py`
- [ ] **R1.4** Revert sms_client.py: `git checkout HEAD~1 modules/sms_client.py`
- [ ] **R1.5** Run tests to confirm reversion: `python3 -m unittest tests.test_auth -v`

**Time to Rollback:** ~5 minutes (git operations only, no code changes needed)

---

---

## Summary

| Phase     | Task                     | Time         | Status         |
| --------- | ------------------------ | ------------ | -------------- |
| 1         | Configuration Update     | 0.5 hrs      | ⏳ Not Started |
| 2         | SMS Client Refactor      | 1.5 hrs      | ⏳ Not Started |
| 3         | Dependencies Update      | 0.25 hrs     | ⏳ Not Started |
| 4         | Auth Module Check        | 0.5 hrs      | ⏳ Not Started |
| 5         | Testing & Verification   | 1 hr         | ⏳ Not Started |
| 6         | Documentation (Optional) | 0.5 hrs      | ⏳ Not Started |
| **Total** | **All Phases**           | **~4 hours** | **0%**         |

---

## Execution Checklist

Before starting, confirm:

- [ ] BRIQ API key and endpoint obtained
- [ ] BRIQ documentation reviewed for authentication method (Bearer token ✅)
- [ ] BRIQ response format confirmed (`{"success": bool, "message": string, "status_code": int}` ✅)
- [ ] Test phone numbers valid and SMS-enabled
- [ ] Email account working (should not change)
- [ ] Git repository clean (ready for commits)

---

## Decision Log

| Decision                                      | Rationale                                                                   | Status       |
| --------------------------------------------- | --------------------------------------------------------------------------- | ------------ |
| SMS-only delivery (no email fallback removal) | Email working fine, no reason to remove. Keep both channels.                | ✅ Confirmed |
| Generic function names                        | Function signature remains identical; only internals change.                | ✅ Confirmed |
| No test code modifications                    | Tests call same interface, hit real API (BRIQ instead of Africa's Talking). | ✅ Confirmed |
| Email SMTP untouched                          | Python built-in SMTP; zero risk; already working.                           | ✅ Confirmed |
| Rollback via Git                              | No database migrations, no breaking changes; simple revert.                 | ✅ Confirmed |

---
