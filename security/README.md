# ConsentChain Security Tools

This directory contains automated security testing and hardening tools for the ConsentChain API.

## Files

| File | Purpose | Usage |
|------|---------|-------|
| `penetration_test.py` | Automated penetration testing suite | `python penetration_test.py` |
| `security-checklist.md` | Comprehensive security checklist | Review manually |
| `hardening.sh` | Automated security hardening checks | `bash hardening.sh` |

## Quick Start

### 1. Run Penetration Tests

```bash
# Start the API server first
cd D:\consentchain
python -m uvicorn api.main:app --reload --port 8000

# In another terminal, run penetration tests
cd security
python penetration_test.py
```

**Environment Variables:**
- `CONSENTCHAIN_BASE_URL` - API base URL (default: `http://localhost:8000`)

**Example:**
```bash
CONSENTCHAIN_BASE_URL=http://localhost:8000 python penetration_test.py
```

### 2. Run Security Hardening Checks

```bash
# On Linux/macOS
bash hardening.sh

# On Windows (Git Bash)
bash security/hardening.sh

# On Windows (WSL)
wsl bash security/hardening.sh
```

### 3. Review Security Checklist

Open `security-checklist.md` and review each section. Check off items as they are verified or implemented.

## Test Coverage

### Penetration Tests (`penetration_test.py`)

| Category | Tests | Description |
|----------|-------|-------------|
| 🔐 Authentication | 6 | JWT, API key, token revocation |
| 🔒 Authorization | 4 | Access control, ownership verification |
| 💉 Injection | 7 | SQL injection, XSS, path traversal |
| 🌐 SSRF | 4 | Webhook URL validation, internal network access |
| ⏱️ Rate Limiting | 2 | Brute force protection, general rate limits |
| 📏 Request Size | 2 | Large payload rejection |
| 🛡️ CSRF | 3 | Token validation, session protection |
| 🔍 Info Disclosure | 5 | Stack traces, server headers, metrics exposure |
| 🔑 Cryptography | 4 | Algorithm review, key storage |
| 🎫 Session | 4 | Token expiry, blacklist, randomness |
| 🌐 CORS | 3 | Origin validation, preflight handling |
| 🛡️ Security Headers | 5 | CSP, HSTS, X-Frame-Options, etc. |

**Total: 50 security tests**

### Hardening Checks (`hardening.sh`)

| Category | Checks | Description |
|----------|--------|-------------|
| Dependencies | 3 | Vulnerability scanning, version pinning |
| File Permissions | 6 | .env permissions, git tracking, key files |
| Environment Variables | 4 | Hardcoded secrets, git history |
| CORS | 4 | Wildcard origins, localhost, credentials |
| Rate Limiting | 6 | Middleware, limits, Redis backend |
| Security Headers | 3 | Header presence and configuration |
| Database | 3 | Parameterized queries, connection strings |
| Logging | 3 | Sentry, audit logging, structured logs |
| CSRF | 3 | Middleware, global application, exemptions |

**Total: 35 hardening checks**

## Output

### Penetration Test Report

Results are saved to `security/pentest-report.json`:

```json
{
  "passed": 45,
  "failed": 5,
  "tests": [
    {"name": "Test name", "status": "PASS"},
    {"name": "Another test", "status": "FAIL", "error": "Details"}
  ],
  "warnings": ["CRITICAL: Test name"]
}
```

### Hardening Summary

```
🔒 ConsentChain Security Hardening Script
==========================================
Date: 2026-04-12 22:57:00
Project: D:\consentchain

Passed: 28
Failed: 2
Warnings: 5
Total:  35

❌ Security hardening required - 2 issue(s) found
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Security Audit
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests pip-audit
      
      - name: Run hardening checks
        run: bash security/hardening.sh
      
      - name: Run dependency audit
        run: pip-audit --format json > security/dependency-report.json
      
      - name: Upload security report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: security/
```

## Recommendations

1. **Run penetration tests** before every production deployment
2. **Run hardening checks** weekly or on every PR
3. **Review security checklist** monthly
4. **Update dependencies** regularly and re-run audits
5. **Rotate secrets** quarterly or after any security incident

## Contributing

When adding new security tests:
1. Follow the existing test pattern in `penetration_test.py`
2. Add corresponding checklist items to `security-checklist.md`
3. Add hardening checks to `hardening.sh` if applicable
4. Mark critical tests with `critical=True`

---

*Last Updated: 2026-04-12*  
*Next Review: 2026-05-12*
