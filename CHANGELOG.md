# Changelog

All notable changes to ConsentChain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-10

### Added

#### Authentication & Security

- OAuth2/OIDC integration with Google, Microsoft, and Auth0 providers
- WebAuthn/passkey authentication support (FIDO2 compliant)
- Enhanced JWT token rotation and refresh mechanisms
- Token blacklist management for secure logout
- CSRF protection with Redis storage
- API key rotation for fiduciaries with immediate invalidation
- Request ID middleware for distributed tracing
- Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)

#### Mobile SDK

- iOS SDK with Swift native implementation
- Android SDK with Kotlin native implementation
- React Native bridge for cross-platform support
- Flutter plugin for multi-platform deployment
- Mobile-specific API endpoints (`/api/v1/mobile/*`)
- Push notification integration
- Biometric authentication for mobile apps

#### Billing & Subscriptions

- Stripe integration for subscription management
- Multi-tier pricing plans (Free, Pro, Enterprise)
- Usage-based billing with metered billing
- Invoice generation and payment history
- Webhook handling for Stripe events
- Proration handling for plan changes
- Trial period management

#### Multi-Tenant SaaS

- Tenant isolation with schema-level separation
- Per-tenant configuration and branding
- Tenant-aware routing and middleware
- Tenant provisioning and lifecycle management
- Cross-tenant audit logging
- Tenant-specific rate limiting

#### Data Portability & Compliance

- Data export in multiple formats (JSON, CSV, XML, PDF)
- Consent renewal workflow with user initiation
- Breach notification system with 72-hour SLA tracking
- Automated compliance score calculation
- DPDP Act Section 8 breach notification automation
- Regulator audit portal with integrity verification
- IPFS evidence storage for tamper-proof records

#### API Enhancements

- Batch consent creation with per-item error handling
- Consent expiry notifications and auto-querying
- Detailed health check with component latency metrics
- Prometheus metrics endpoint for all core entities
- Grievance SLA compliance checking
- Guardian authorization for vulnerable users
- Data deletion orchestrator with certificate generation
- Public endpoints for user-facing consent management

#### Developer Experience

- Comprehensive OpenAPI documentation with tags
- Request size limiting middleware (10MB max)
- Global exception handling with structured responses
- Enhanced error responses with context
- API versioning support (`/api/v1/*`)
- OpenAPI JSON endpoint (`/api/v1/openapi.json`)

#### Infrastructure & DevOps

- Docker Compose with production configuration
- Nginx reverse proxy configuration
- Kubernetes deployment manifests (k8s/)
- GitHub Actions CI/CD pipeline
- Pre-commit hooks with linting and formatting
- Multi-stage Docker build optimization
- Health check and readiness probes

#### Monitoring & Observability

- OpenTelemetry distributed tracing
- Prometheus metrics collection
- Grafana dashboard configurations
- Slow query logging (>1 second threshold)
- Connection pool tuning with pre-ping
- Request timing middleware
- Component-level health monitoring

#### Testing

- 159+ unit and integration tests (95%+ coverage)
- Playwright E2E test framework setup
- Pytest fixtures for common test patterns
- Async test support with pytest-asyncio
- Test markers for slow and integration tests

### Changed

- Upgraded from FastAPI 0.104 to 0.109
- Enhanced SQLAlchemy async session management
- Improved Redis caching with aiocache integration
- Refined rate limiting with slowapi
- Updated smart contract deployment scripts
- Enhanced TypeScript SDK with full type coverage

### Fixed

- 103 issues identified and resolved across implementation rounds
- Database connection pool exhaustion under load
- Race conditions in consent state transitions
- Memory leaks in WebSocket connections
- Incorrect pagination calculations
- Missing CSRF token validation on sensitive endpoints
- Token expiry edge cases in refresh flow

### Security

- Added Sentry error tracking integration
- Enhanced input validation with Pydantic v2
- Secret scanning in pre-commit hooks
- Dependency vulnerability auditing
- OWASP Top 10 compliance review
- Ed25519 cryptographic signing for all transactions

### Documentation

- Comprehensive API reference (`docs/API_REFERENCE.md`)
- Architecture guide (`docs/ARCHITECTURE.md`)
- Deployment guide (`docs/DEPLOYMENT.md`)
- DPDP compliance guide (`docs/DPDP_COMPLIANCE.md`)
- Use cases documentation (`docs/USE_CASES.md`)
- Quick start guide (`QUICKSTART.md`)
- Security guide (`SECURITY.md`)
- Contribution guidelines (`CONTRIBUTING.md`)
- Project index (`PROJECT_INDEX.md`)

### Smart Contracts

- Consent Registry (App ID: 757755252)
- Audit Trail (App ID: 757755253)
- ARC-4 compliant contract interfaces

### SDKs

- Python SDK (`sdk/client.py`)
- TypeScript SDK (`sdk-ts/`)
- Async SDK (`sdk-async/`)

### Removed

- Deprecated v0.5.0 legacy endpoints
- Unused synchronous database connections

## [1.0.0] - 2024-03-25

### Added

#### Core Features

- Consent lifecycle management (create, revoke, modify, verify)
- Algorand blockchain integration with ARC4 smart contracts
- Merkle tree-based audit trails
- DPDP Act Section 9 compliance (30-day deletion deadline)
- DPDP Act Section 13 compliance (grievance redressal)
- DPDP Act Section 8 compliance (breach notification)
- Guardian support for minors and persons with disabilities
- Data portability (JSON/PDF export)

#### Security

- JWT authentication with refresh tokens
- API key authentication for fiduciaries
- Algorand wallet signature verification
- CSRF protection with Redis storage
- Rate limiting (200 requests/minute default)
- Ed25519 cryptographic signing

#### API Endpoints

- Health and monitoring endpoints
- Consent CRUD operations
- Fiduciary registration and management
- Audit trail querying
- Compliance reporting
- Webhook subscriptions
- Data deletion requests

#### Advanced Features

- WebSocket real-time updates
- Multi-language consent templates (Hindi, Tamil, Bengali, English)
- AI compliance assistant with DPDP analysis
- Analytics dashboard with trends and predictions
- WebAuthn/passkey authentication
- Mobile SDK support (iOS, Android, React Native, Flutter)

#### Architecture

- Circuit breaker pattern for external services
- Redis caching layer with local fallback
- Graceful shutdown handling
- Event-driven architecture
- OpenTelemetry distributed tracing

#### Infrastructure

- Docker Compose deployment
- PostgreSQL database
- Redis cache
- Prometheus metrics
- Grafana dashboards
- GitHub Actions CI/CD

### Smart Contracts

- Consent Registry (App ID: 757755252)
- Audit Trail (App ID: 757755253)

### SDKs

- Python SDK (`sdk/client.py`)
- TypeScript SDK (`sdk-ts/`)
- Async SDK (`sdk-async/`)

### Documentation

- API Reference (`docs/API_REFERENCE.md`)
- Architecture Guide (`docs/ARCHITECTURE.md`)
- Deployment Guide (`docs/DEPLOYMENT.md`)
- DPDP Compliance Guide (`docs/DPDP_COMPLIANCE.md`)
- Use Cases (`docs/USE_CASES.md`)

### Tests

- 159 unit and integration tests
- 95%+ code coverage on core modules

## [0.9.0] - 2024-03-20

### Added

- Initial beta release
- Basic consent management
- Algorand testnet deployment
- React dashboard
- REST API

## [0.5.0] - 2024-03-15

### Added

- Project initialization
- Core database models
- Basic smart contracts (PyTeal)
- Development environment setup

---

## Release Schedule

### [1.2.0] - Planned Q3 2026

- AI compliance chatbot
- Consent prediction model
- Advanced analytics dashboard
- Mobile SDK native app store releases
- Enterprise SSO (SAML, LDAP)

### [2.0.0] - Planned Q4 2026

- Zero-knowledge proofs
- Cross-chain support
- Decentralized identity (DID)
- Compliance marketplace
- White-label solution
