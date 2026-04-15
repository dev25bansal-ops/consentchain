#!/usr/bin/env bash
###############################################################################
# ConsentChain Security Hardening Script
#
# Purpose: Automated security hardening checks and recommendations
# Usage:   bash security/hardening.sh
#
# This script:
#   1. Checks for outdated dependencies
#   2. Verifies file permissions
#   3. Checks environment variable exposure
#   4. Validates CORS configuration
#   5. Reviews rate limiting settings
#   6. Scans for hardcoded secrets
#   7. Checks for common misconfigurations
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

###############################################################################
# Helper functions
###############################################################################
pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN++))
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

###############################################################################
# 1. Dependency Security Checks
###############################################################################
check_dependencies() {
    section "1. Dependency Security Checks"

    # Check if pip-audit is available
    if command -v pip-audit &>/dev/null; then
        info "Running pip-audit..."
        cd "$PROJECT_ROOT"
        if pip-audit --require-hashes 2>/dev/null || pip-audit 2>/dev/null; then
            pass "No known vulnerabilities in Python dependencies"
        else
            fail "Vulnerabilities found in Python dependencies"
            info "Run: pip-audit > security/dependency-report.txt"
        fi
    else
        warn "pip-audit not installed. Install with: pip install pip-audit"
    fi

    # Check for pinned versions in requirements
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        unpinned=$(grep -v '==' "$PROJECT_ROOT/requirements.txt" | grep -v '^#' | grep -v '^$' || true)
        if [ -z "$unpinned" ]; then
            pass "All dependencies are pinned to specific versions"
        else
            warn "Some dependencies are not pinned:"
            echo "$unpinned" | head -5
        fi
    else
        warn "requirements.txt not found"
    fi

    # Check for setup.py or pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ] || [ -f "$PROJECT_ROOT/setup.py" ]; then
        pass "Project configuration file found"
    else
        warn "No pyproject.toml or setup.py found"
    fi
}

###############################################################################
# 2. File Permission Checks
###############################################################################
check_permissions() {
    section "2. File Permission Checks"

    # Check .env file permissions
    if [ -f "$PROJECT_ROOT/.env" ]; then
        perms=$(stat -c "%a" "$PROJECT_ROOT/.env" 2>/dev/null || stat -f "%Lp" "$PROJECT_ROOT/.env" 2>/dev/null || echo "unknown")
        if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
            pass ".env file has restrictive permissions ($perms)"
        else
            fail ".env file permissions too open ($perms). Should be 600 or 400"
            info "Run: chmod 600 .env"
        fi
    else
        warn ".env file not found (may be using environment variables)"
    fi

    # Check .env.example exists
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        pass ".env.example file exists"
    else
        warn ".env.example not found"
    fi

    # Check for committed .env in git
    if git -C "$PROJECT_ROOT" ls-files --error-unmatch .env &>/dev/null 2>&1; then
        fail ".env file is tracked by git! Remove immediately"
        info "Run: git rm --cached .env && echo '.env' >> .gitignore"
    else
        pass ".env file is not tracked by git"
    fi

    # Check for private keys in repository
    key_files=$(find "$PROJECT_ROOT" -name "*.pem" -o -name "*.key" -o -name "id_rsa" 2>/dev/null | grep -v node_modules | grep -v .git || true)
    if [ -n "$key_files" ]; then
        fail "Private key files found in repository:"
        echo "$key_files"
    else
        pass "No private key files found in repository"
    fi

    # Check for world-readable sensitive files
    world_readable=$(find "$PROJECT_ROOT" -name "*.env*" -perm -o+r 2>/dev/null | grep -v node_modules | grep -v .git || true)
    if [ -n "$world_readable" ]; then
        fail "World-readable sensitive files found:"
        echo "$world_readable"
    else
        pass "No world-readable sensitive files"
    fi
}

###############################################################################
# 3. Environment Variable Exposure
###############################################################################
check_env_vars() {
    section "3. Environment Variable Exposure"

    # Check for hardcoded secrets in source code
    info "Scanning for hardcoded secrets..."

    # Check for common secret patterns
    secret_patterns=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "API_KEY\s*=\s*['\"][^'\"]+['\"]"
        "JWT_SECRET\s*=\s*['\"][^'\"]+['\"]"
        "DATABASE_URL\s*=\s*['\"][^'\"]*:[^'\"]*@['\"]"
        "mnemonic\s*=\s*['\"][^'\"]+['\"]"
        "PRIVATE_KEY\s*=\s*['\"][^'\"]+['\"]"
    )

    found_secrets=false
    for pattern in "${secret_patterns[@]}"; do
        matches=$(grep -rn --include="*.py" -E "$pattern" "$PROJECT_ROOT/api" "$PROJECT_ROOT/core" "$PROJECT_ROOT/contracts" 2>/dev/null | grep -v "__pycache__" | grep -v ".pyc" | grep -v "os.getenv" | grep -v "TESTING" || true)
        if [ -n "$matches" ]; then
            # Filter out placeholder values and comments
            real_secrets=$(echo "$matches" | grep -v "your_" | grep -v "placeholder" | grep -v "#" || true)
            if [ -n "$real_secrets" ]; then
                fail "Potential hardcoded secret found:"
                echo "$real_secrets" | head -3
                found_secrets=true
            fi
        fi
    done

    if [ "$found_secrets" = false ]; then
        pass "No hardcoded secrets detected in source code"
    fi

    # Check .env.example for placeholder values
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        real_values=$(grep -v "^#" "$PROJECT_ROOT/.env.example" | grep -v "your_" | grep -v "placeholder" | grep "=" | grep -v "^$" || true)
        if [ -n "$real_values" ]; then
            warn ".env.example contains real-looking values:"
            echo "$real_values" | head -3
        else
            pass ".env.example uses placeholder values"
        fi
    fi

    # Check for .env in git history
    if git -C "$PROJECT_ROOT" log --all --full-history -- .env &>/dev/null 2>&1; then
        warn ".env may have been committed in git history"
        info "Consider using: git filter-branch or BFG Repo-Cleaner"
    fi
}

###############################################################################
# 4. CORS Configuration Review
###############################################################################
check_cors() {
    section "4. CORS Configuration Review"

    # Check CORS origins in code
    cors_origins=$(grep -n "CORS_ORIGINS\|allow_origins" "$PROJECT_ROOT/api/main.py" 2>/dev/null || true)
    if [ -n "$cors_origins" ]; then
        info "CORS configuration found:"
        echo "$cors_origins"

        # Check for wildcard
        if echo "$cors_origins" | grep -q '"\*"'; then
            fail "CORS allows all origins (wildcard *)"
            info "Restrict to specific domains in production"
        else
            pass "CORS does not use wildcard origin"
        fi

        # Check for localhost in production
        if echo "$cors_origins" | grep -q "localhost"; then
            warn "CORS includes localhost origins"
            info "Remove localhost origins in production deployment"
        else
            pass "No localhost origins in CORS"
        fi
    else
        warn "CORS configuration not found in main.py"
    fi

    # Check allow_credentials
    if grep -q "allow_credentials=True" "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
        warn "CORS allow_credentials is True"
        info "Ensure origins are restricted when credentials are allowed"
    fi

    # Check allow_methods
    if grep -q 'allow_methods=\["\*"\]' "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
        warn "CORS allows all HTTP methods"
        info "Restrict to required methods (GET, POST, PUT, DELETE)"
    else
        pass "CORS methods are not wildcard"
    fi
}

###############################################################################
# 5. Rate Limiting Review
###############################################################################
check_rate_limiting() {
    section "5. Rate Limiting Review"

    # Check if rate limiting is configured
    if [ -f "$PROJECT_ROOT/api/middleware/rate_limiting.py" ]; then
        pass "Rate limiting middleware exists"
    else
        fail "Rate limiting middleware not found"
    fi

    # Check default limits
    default_limit=$(grep -n "default_limits" "$PROJECT_ROOT/api/middleware/rate_limiting.py" 2>/dev/null || true)
    if [ -n "$default_limit" ]; then
        info "Default rate limits: $default_limit"

        # Check if limits are reasonable
        if echo "$default_limit" | grep -q "200/minute"; then
            pass "Default rate limit is reasonable (200/minute)"
        elif echo "$default_limit" | grep -q "1000/minute"; then
            warn "Default rate limit may be too high (1000/minute)"
        fi
    fi

    # Check endpoint-specific limits
    endpoint_limits=$(grep -n "limiter.limit" "$PROJECT_ROOT/api/routes/"*.py 2>/dev/null | wc -l || echo "0")
    if [ "$endpoint_limits" -gt 0 ]; then
        pass "$endpoint_limits endpoints have rate limiting"
    else
        warn "No endpoint-specific rate limits found"
    fi

    # Check authentication endpoint limits
    auth_limit=$(grep -n "limiter.limit" "$PROJECT_ROOT/api/main.py" 2>/dev/null | grep -i "login\|auth" || true)
    if [ -n "$auth_limit" ]; then
        info "Authentication endpoint rate limits: $auth_limit"
        if echo "$auth_limit" | grep -q "10/minute"; then
            pass "Login endpoint has strict rate limiting (10/minute)"
        fi
    else
        warn "No rate limiting found on authentication endpoints"
    fi

    # Check Redis backend for rate limiting
    if grep -q "redis" "$PROJECT_ROOT/api/middleware/rate_limiting.py" 2>/dev/null; then
        pass "Rate limiting uses Redis backend (distributed)"
    else
        warn "Rate limiting may use in-memory backend (not distributed)"
    fi
}

###############################################################################
# 6. Security Headers Check
###############################################################################
check_security_headers() {
    section "6. Security Headers Check"

    # Check for security headers middleware
    headers_files=$(find "$PROJECT_ROOT/api" -name "*header*" -o -name "*security*" 2>/dev/null | grep -v __pycache__ || true)
    if [ -n "$headers_files" ]; then
        pass "Security headers configuration found"
    else
        warn "No dedicated security headers middleware found"
        info "Consider adding: X-Content-Type-Options, X-Frame-Options, CSP, HSTS"
    fi

    # Check main.py for header configuration
    if grep -q "X-Content-Type-Options\|X-Frame-Options\|Content-Security-Policy" "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
        pass "Security headers configured in main.py"
    else
        warn "Security headers not explicitly configured"
    fi
}

###############################################################################
# 7. Database Security
###############################################################################
check_database() {
    section "7. Database Security"

    # Check for parameterized queries
    raw_queries=$(grep -rn "execute\s*(" "$PROJECT_ROOT/api/" --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -v "session.execute" || true)
    if [ -n "$raw_queries" ]; then
        warn "Potential raw SQL queries found:"
        echo "$raw_queries" | head -3
        info "Ensure all queries use parameterized statements"
    else
        pass "No raw SQL queries found (using ORM)"
    fi

    # Check for connection string in code
    if grep -rn "postgresql://\|mysql://\|sqlite:///" "$PROJECT_ROOT/api/" --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -v "os.getenv" | grep -v "DATABASE_URL" | grep -v "#"; then
        fail "Database connection string found in source code"
    else
        pass "No hardcoded database connection strings"
    fi

    # Check for pool configuration
    if grep -q "pool_size\|pool_pre_ping" "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
        pass "Database connection pooling configured"
    else
        warn "Database connection pooling not explicitly configured"
    fi
}

###############################################################################
# 8. Logging & Monitoring
###############################################################################
check_logging() {
    section "8. Logging & Monitoring"

    # Check for Sentry integration
    if grep -q "sentry_sdk" "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
        pass "Sentry integration configured"
    else
        warn "Sentry integration not found"
    fi

    # Check for structured logging
    if grep -q "json_logs\|structlog" "$PROJECT_ROOT/api/" -r --include="*.py" 2>/dev/null; then
        pass "Structured logging configured"
    else
        warn "Structured logging not detected"
    fi

    # Check for audit logging
    if [ -f "$PROJECT_ROOT/api/routes/audit.py" ]; then
        pass "Audit logging routes exist"
    else
        warn "No dedicated audit logging routes found"
    fi
}

###############################################################################
# 9. CSRF Protection
###############################################################################
check_csrf() {
    section "9. CSRF Protection"

    if [ -f "$PROJECT_ROOT/api/middleware/csrf.py" ]; then
        pass "CSRF protection middleware exists"

        # Check if CSRF is applied globally
        if grep -q "app.middleware.*csrf" "$PROJECT_ROOT/api/main.py" 2>/dev/null; then
            pass "CSRF protection is applied globally"
        else
            warn "CSRF protection may not be applied globally"
        fi

        # Check for exempt paths
        exempt_paths=$(grep -n "exempt_paths" "$PROJECT_ROOT/api/middleware/csrf.py" 2>/dev/null || true)
        if [ -n "$exempt_paths" ]; then
            info "CSRF exempt paths configured:"
            echo "$exempt_paths"
        fi
    else
        fail "CSRF protection middleware not found"
    fi
}

###############################################################################
# 10. Summary
###############################################################################
print_summary() {
    section "Security Hardening Summary"

    total=$((PASS + FAIL + WARN))
    echo -e "${GREEN}Passed: $PASS${NC}"
    echo -e "${RED}Failed: $FAIL${NC}"
    echo -e "${YELLOW}Warnings: $WARN${NC}"
    echo -e "Total:  $total"
    echo ""

    if [ "$FAIL" -gt 0 ]; then
        echo -e "${RED}❌ Security hardening required - $FAIL issue(s) found${NC}"
        echo ""
        echo "Recommended immediate actions:"
        echo "  1. Fix all FAIL items before deploying to production"
        echo "  2. Review WARN items and address as appropriate"
        echo "  3. Run penetration tests: python security/penetration_test.py"
        echo "  4. Review security checklist: security/security-checklist.md"
        exit 1
    elif [ "$WARN" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARN warning(s) - review recommended${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Review WARN items and address security improvements"
        echo "  2. Run penetration tests: python security/penetration_test.py"
        echo "  3. Review security checklist: security/security-checklist.md"
    else
        echo -e "${GREEN}✅ All security hardening checks passed${NC}"
        echo ""
        echo "Recommended next steps:"
        echo "  1. Run penetration tests: python security/penetration_test.py"
        echo "  2. Review security checklist: security/security-checklist.md"
        echo "  3. Schedule regular security audits"
    fi
}

###############################################################################
# Main
###############################################################################
main() {
    echo "🔒 ConsentChain Security Hardening Script"
    echo "=========================================="
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Project: $PROJECT_ROOT"
    echo ""

    check_dependencies
    check_permissions
    check_env_vars
    check_cors
    check_rate_limiting
    check_security_headers
    check_database
    check_logging
    check_csrf

    print_summary
}

main "$@"
