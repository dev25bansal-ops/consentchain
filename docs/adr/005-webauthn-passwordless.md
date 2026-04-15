# ADR-005: WebAuthn Passwordless Authentication

## Status
Accepted

## Date
2026-03-20

## Context
As part of our multi-factor authentication strategy, we evaluated passwordless authentication options for ConsentChain. Passwords are a known security weakness — users choose weak passwords, reuse them across services, and they are vulnerable to phishing, credential stuffing, and brute-force attacks.

**Requirements:**
- Eliminate password-based authentication entirely for dashboard users
- Support hardware security keys (YubiKey, SoloKey) for high-security environments
- Support platform authenticators (Touch ID, Face ID, Windows Hello) for consumer UX
- Maintain phishing resistance as a core security property
- Work across desktop browsers and mobile devices
- Integrate with existing JWT token infrastructure

**Alternatives considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **Magic Links (email)** | Simple UX, no passwords | Email account compromise vector, slow (email delivery), no phishing resistance |
| **TOTP (Google Authenticator)** | Widely supported, free | Not phishing-resistant, requires secondary app, lost device recovery is complex |
| **SMS OTP** | Universal phone support | SIM swap attacks, not phishing-resistant, carrier dependency, GDPR concerns |
| **WebAuthn/Passkeys** | Phishing-resistant, hardware-backed, platform-native | Requires browser support (modern browsers only), backup/recovery complexity |
| **Hardware OTP tokens** | Strong security, no network needed | Cost per token, distribution logistics, lost token replacement |

## Decision
Adopt **WebAuthn (Web Authentication API)** as our passwordless authentication standard, implemented via the `webauthn` Python library with support for both security keys and platform authenticators.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Device                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │  YubiKey │  │ Touch ID │  │ Windows Hello / PIN   │  │
│  │ (USB/NFC)│  │ (macOS)  │  │ (Windows)             │  │
│  └────┬─────┘  └────┬─────┘  └───────────┬───────────┘  │
│       │              │                     │              │
│       └──────────────┴─────────────────────┘              │
│                          │                                 │
│                   WebAuthn API                             │
│                   (navigator.credentials)                   │
└──────────────────────────┬────────────────────────────────┘
                           │
                    PublicKeyCredential
                    (attestation/assertion)
                           │
┌──────────────────────────┴────────────────────────────────┐
│                  ConsentChain API                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  /api/v1/webauthn/register/start                    │  │
│  │  /api/v1/webauthn/register/finish                   │  │
│  │  /api/v1/webauthn/authenticate/start                │  │
│  │  /api/v1/webauthn/authenticate/finish               │  │
│  │  /api/v1/webauthn/credentials/{id}  (DELETE)        │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                 │
│                   WebAuthnService                           │
│                   (verify signature)                        │
│                          │                                 │
│                   Generate JWT                              │
└─────────────────────────────────────────────────────────────┘
```

### Security Properties

- **Phishing resistant** — Cryptographic origin binding prevents credential theft
- **No shared secrets** — Private key never leaves the authenticator device
- **Hardware-backed** — Keys stored in secure element (SE) or trusted platform module (TPM)
- **Attestation support** — Server can verify the authenticator model for compliance
- **User verification** — Biometric or PIN verification at the authenticator level

### Implementation

- `api/features.py` — WebAuthn endpoints under `/api/v1/webauthn/*`
- `WebAuthnService` — Registration and authentication orchestration
- `WebAuthnUser` — User model with credential management
- `RegistrationResult` / `AuthenticationResult` — Pydantic response models
- Support for `direct` and `indirect` attestation conveyance
- Configurable `userVerification` requirement (`required`, `preferred`, `discouraged`)
- Credential exclusion during registration (prevent duplicate registrations)
- Credential deletion endpoint for account management

## Consequences

### Positive
- **Strongest consumer authentication** — Phishing-resistant, hardware-backed security
- **Better UX than passwords** — No password to remember, biometric or single-touch auth
- **Standards-based** — W3C Recommendation, supported by all major browsers and platforms
- **Passkey-ready** — WebAuthn is the foundation of the emerging passkey ecosystem
- **Complements wallet auth** — Provides a Web3-equivalent security level for Web2 users
- **Enterprise compliance** — Meets NIST SP 800-63B AAL2/AAL3 requirements

### Negative
- **Browser dependency** — Requires WebAuthn-capable browsers (excludes older browsers)
- **Recovery complexity** — Lost device means lost authenticator; requires backup credentials
- **Hardware cost** — Security keys cost $25-55 each for hardware authenticators
- **Platform fragmentation** — Different UX on macOS (Touch ID) vs Windows (Hello) vs mobile
- **Shared device limitations** — Platform authenticators are device-bound, not portable across devices
- **Attestation privacy** — Some authenticators reveal device model, raising privacy concerns

## Migration Path
For users transitioning from other auth methods:

1. **During onboarding** — Offer WebAuthn registration alongside wallet/OAuth options
2. **Post-registration** — Allow users to add WebAuthn credentials to existing accounts
3. **Credential management** — Users can register multiple authenticators for backup
4. **Fallback** — OAuth remains available as a fallback if WebAuthn authenticator is lost

## References
- [W3C Web Authentication Level 3](https://www.w3.org/TR/webauthn-3/)
- [NIST SP 800-63B — Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [Passkeys (FIDO Alliance)](https://fidoalliance.org/passkeys/)
- [webauthn Python Library](https://github.com/duo-labs/py_webauthn)
