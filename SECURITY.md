# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in ConsentChain, please report it responsibly.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please:

1. **Email**: Send details to security@consentchain.io
2. **Subject Line**: `[SECURITY] Brief description of vulnerability`
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
   - Your contact information

### What to Expect

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 72 hours
- **Status Updates**: Every 7 days until resolved
- **Resolution**: Depends on severity (see below)

### Response Timeline

| Severity | Target Resolution |
| -------- | ----------------- |
| Critical | 24-48 hours       |
| High     | 7 days            |
| Medium   | 14 days           |
| Low      | 30 days           |

### Disclosure Policy

- We follow [Coordinated Vulnerability Disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure)
- We will credit you in our security advisories (unless you prefer anonymity)
- We will not take legal action against researchers who act in good faith

## Security Features

### Authentication & Authorization

- **JWT Tokens**: Short-lived access tokens (24h) with refresh tokens (7 days)
- **API Keys**: Scoped API keys for fiduciary integrations
- **Wallet Signatures**: Algorand wallet signature verification
- **WebAuthn**: Hardware key authentication support

### Data Protection

- **Encryption at Rest**: Database field encryption for sensitive data
- **Encryption in Transit**: TLS 1.3 for all connections
- **Hashing**: SHA-256/SHA-512 for consent hashes
- **Signing**: Ed25519 for blockchain transactions

### Input Validation

- All inputs validated with Pydantic
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via output encoding
- CSRF protection for state-changing operations

### Rate Limiting

- Default: 200 requests/minute per IP
- Consent creation: 100/minute
- Batch operations: 10/minute
- Public endpoints: 10/minute

### Audit Logging

- All consent operations logged
- All authentication attempts logged
- All administrative actions logged
- Immutable audit trail on blockchain

## Security Best Practices

### For Developers

1. **Never commit secrets** to the repository
2. **Use environment variables** for sensitive configuration
3. **Rotate API keys** regularly (use `/api/v1/fiduciary/rotate-key`)
4. **Validate all inputs** on both client and server
5. **Use HTTPS** for all communications
6. **Keep dependencies updated**

### For Operators

1. **Use strong JWT secrets** (minimum 32 random bytes)
2. **Enable Redis authentication**
3. **Restrict database access** to application servers
4. **Configure CORS** for production domains only
5. **Enable rate limiting** in production
6. **Set up monitoring** for suspicious activities

### For Users

1. **Use strong passwords** for wallet accounts
2. **Enable biometric authentication** on mobile devices
3. **Review consent requests** carefully before approving
4. **Report suspicious activities** immediately
5. **Keep your wallet software updated**

## Known Security Considerations

### Blockchain Limitations

- Consensus finality: ~4.5 seconds on Algorand
- Not suitable for high-frequency real-time applications
- Transaction fees may vary based on network congestion

### Key Management

- Master mnemonic must be stored securely
- Consider using Algorand multisig for production
- Use hardware security modules (HSM) for key storage

### Data Minimization

- Only cryptographic hashes stored on blockchain
- Personal data stored in off-chain database
- Regular data purging per DPDP Section 9

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in secure vault
- [ ] HTTPS enabled with valid certificates
- [ ] Rate limiting configured
- [ ] CORS configured for production domains
- [ ] Database credentials rotated
- [ ] Redis authentication enabled
- [ ] Prometheus metrics secured
- [ ] Grafana default credentials changed
- [ ] Security headers configured
- [ ] Error messages sanitized

### Post-Deployment

- [ ] Security monitoring enabled
- [ ] Alert rules configured
- [ ] Log aggregation set up
- [ ] Incident response plan documented
- [ ] Regular security audits scheduled

## Security Headers

ConsentChain sets the following security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

## Vulnerability History

| CVE | Severity | Description                  | Fixed In |
| --- | -------- | ---------------------------- | -------- |
| N/A | N/A      | No published vulnerabilities | N/A      |

## Security Contact

- **Security Team**: security@consentchain.io
- **PGP Key**: [security.asc](https://consentchain.io/.well-known/security.asc)
- **Response Time**: 24-72 hours

---

Last Updated: April 2, 2026
