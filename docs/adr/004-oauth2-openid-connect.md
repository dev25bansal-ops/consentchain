# ADR-004: OAuth2 / OpenID Connect Authentication

## Status
Accepted

## Date
2026-03-15

## Context
ConsentChain initially supported only wallet-based authentication (Algorand cryptographic signatures) for data principals. While this aligns well with the blockchain-native architecture, it creates a significant barrier to adoption for:

1. **Non-crypto users** who don't have or want an Algorand wallet
2. **Enterprise SSO requirements** where organizations mandate SAML/OIDC-based authentication
3. **Dashboard users** (fiduciary staff) who expect familiar email/password or social login
4. **Mobile app users** who prefer biometric or social login flows

We needed an authentication strategy that bridges Web3 wallet authentication with Web2 identity providers without compromising security or the decentralized consent model.

**Alternatives considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **Custom username/password** | Full control, no external dependencies | Password security burden, no SSO, users expect social login |
| **SAML 2.0** | Enterprise standard, mature | Complex implementation, not consumer-friendly |
| **Magic Link (email)** | No passwords, simple UX | Email dependency, slower auth flow, no SSO |
| **OAuth2/OIDC** | Industry standard, SSO support, PKCE, multiple providers | External provider dependency, token management complexity |

## Decision
Adopt **OAuth 2.0 with OpenID Connect (OIDC)** as the primary Web2 authentication protocol, supporting multiple identity providers:

- **Google** — Most widely used, OIDC compliant
- **Microsoft (Azure AD/Entra ID)** — Enterprise SSO requirement
- **Auth0** — Fallback/custom identity provider option

### Architecture

```
User Browser                    ConsentChain API                 Identity Provider
     │                                │                                │
     │  1. GET /oauth/authorize/{p}   │                                │
     ├───────────────────────────────>│                                │
     │                                │   2. Authorization URL (PKCE)  │
     │                                ├───────────────────────────────>│
     │  3. Redirect to IdP            │                                │
     │<───────────────────────────────────────────────────────────────│
     │                                │                                │
     │  4. User authenticates         │                                │
     │                                │                                │
     │  5. Redirect with code         │                                │
     │                                │                                │
     │  6. GET /oauth/callback/{p}    │                                │
     ├───────────────────────────────>│                                │
     │                                │   7. Exchange code for token   │
     │                                ├───────────────────────────────>│
     │                                │   8. Access token + ID token   │
     │                                │<───────────────────────────────│
     │                                │                                │
     │                                │  9. Get user info (OIDC)       │
     │                                ├───────────────────────────────>│
     │                                │  10. User profile              │
     │                                │<───────────────────────────────│
     │                                │                                │
     │                                │  11. Find/create principal     │
     │                                │  12. Generate JWT              │
     │  13. JWT tokens + user info    │                                │
     │<───────────────────────────────│                                │
```

### Security Measures

- **PKCE (Proof Key for Code Exchange)** — Required for all authorization flows (RFC 7636)
- **State parameter** — CSRF protection on every authorization request
- **HTTP-only cookies** — Session tokens stored as `HttpOnly; Secure; SameSite=Lax`
- **JWT access tokens** — 24-hour expiry, short-lived
- **JWT refresh tokens** — 7-day expiry, stored server-side with revocation support
- **Token blacklisting** — Redis-backed JWT revocation via `/api/v1/auth/logout`
- **Account linking** — OAuth accounts can be linked to existing wallet-based principals with signature verification

### Implementation

- `api/oauth/routes.py` — Route handlers (`/api/v1/oauth/*`)
- `api.oauth.OAuthService` — Core OAuth service with provider management
- `api.database.OAuthAccountDB` — OAuth account linkage table
- PKCE code verifier/challenger generation per authorization request
- Supports `/authorize/{provider}`, `/authorize/{provider}/redirect`, `/callback/{provider}`, `/providers`, `/link`, `/unlink/{provider}`

## Consequences

### Positive
- **Lower barrier to entry** — Users can authenticate with existing Google/Microsoft accounts
- **Enterprise readiness** — Azure AD/Entra ID support enables B2B SaaS deployments
- **Account flexibility** — Users can link multiple identity providers to one principal
- **Standards-compliant** — OIDC is an IETF standard with broad ecosystem support
- **Wallet + OAuth duality** — Both Web3 and Web2 auth coexist, linked to the same principal
- **PKCE security** — No client secrets needed, safe for SPAs and mobile apps

### Negative
- **External dependency** — Outages at Google/Microsoft affect authentication availability
- **Token management complexity** — JWT lifecycle (access, refresh, blacklist) adds operational burden
- **Privacy considerations** — OAuth providers receive metadata about ConsentChain usage
- **Account linking UX** — Linking OAuth to wallet requires signature verification, adding friction
- **Provider-specific quirks** — Each OAuth provider has subtle differences in scope, token format, and error handling

## Migration Path
If we need to add additional providers:

1. Add provider enum to `OAuthProvider` in `api/oauth/__init__.py`
2. Configure environment variables (`{PROVIDER}_CLIENT_ID`, `{PROVIDER}_CLIENT_SECRET`)
3. Define scopes in `init_oauth_from_env()`
4. Test authorization callback flow
5. Update `/api/v1/oauth/providers` endpoint (automatic)

## References
- [RFC 6749 — The OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636 — PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OWASP OAuth 2.0 Security Best Practices](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/)
