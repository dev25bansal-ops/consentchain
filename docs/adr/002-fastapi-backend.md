# ADR-002: Use FastAPI for Backend Framework

## Status
Accepted

## Date
2025-01-15

## Context
We needed a modern Python web framework for building the REST API that manages consent records, handles authentication, and interfaces with the Algorand blockchain.

**Requirements:**
- Native async/await support for blockchain operations
- Automatic API documentation (OpenAPI/Swagger)
- Strong data validation (Pydantic integration)
- High performance (comparable to Node.js frameworks)
- Type safety for large codebase maintainability
- Active community and regular security updates
- Dependency injection for testability

**Alternatives considered:**
- Flask: Mature but no native async, requires extensions for everything
- Django: Heavy, ORM doesn't match our blockchain-first architecture
- Sanic: Fast but smaller ecosystem, less mature
- Starlette: Low-level, would need to build too much from scratch
- aiohttp: Good for async but lacks data validation and auto-docs

## Decision
Chose **FastAPI** (with Uvicorn ASGI server) because:

1. **Async/await support** out of the box - Critical for non-blocking blockchain calls
2. **Automatic OpenAPI documentation** - Reduces documentation burden, always up-to-date
3. **Pydantic integration** - Strong validation on all request/response schemas
4. **Dependency injection system** - Makes testing easier, enforces separation of concerns
5. **High performance** - Benchmarks show performance comparable to Node.js/Go
6. **Type hints** - Full type safety with mypy support
7. **Modern Python** - Designed for Python 3.7+, uses latest features

## Implementation
- **Uvicorn** as ASGI server (async, production-ready)
- **Pydantic v2** for data validation and serialization
- **SQLAlchemy 2.0** async ORM for database operations
- **SlowAPI** for rate limiting (Redis-backed)
- **Custom middleware** for CSRF, request ID, timing, tenant isolation

## Architecture
```
Request → Middleware Stack → Route Handler → Service Layer → Database/Blockchain
           - CORS           - Auth          - Business Logic  - PostgreSQL
           - Request ID     - Validation    - Compliance      - Algorand
           - Timing         - Rate Limit    - Audit           - Redis
           - CSRF           - Tenant        - Notifications   - IPFS
```

## Consequences

### Positive
- **Automatic API documentation** via Swagger UI and ReDoc - always accurate
- **Type safety** with Pydantic models - catches errors at development time
- **Modern async patterns** - Non-blocking I/O throughout
- **Easy testing** - Dependency injection makes mocking straightforward
- **Developer experience** - Auto-completion, type checking, validation
- **Performance** - Handles 1000+ req/s on modest hardware

### Negative
- **Steeper learning curve** than Flask - team needed training on async patterns
- **Smaller ecosystem** than Django - fewer ready-made packages
- **Rapid evolution** - Breaking changes between major versions (Pydantic v1→v2 migration)
- **Async complexity** - Need to be careful about blocking calls in async context
- **Young framework** - Less battle-tested than Django/Flask for edge cases

## Key Decisions Enabled by FastAPI
- **Dependency injection** for database sessions, Redis clients, auth
- **Path operation functions** with type-hinted parameters
- **Automatic request validation** via Pydantic models
- **Background tasks** for async blockchain processing
- **Lifespan context manager** for startup/shutdown logic

## Migration Considerations
If we ever need to migrate away from FastAPI:
1. Pydantic models are framework-agnostic - can be reused
2. Service layer is framework-agnostic - can be reused
3. Only route handlers and middleware would need rewriting
4. SQLAlchemy ORM layer is unchanged
5. Estimated migration effort: 2-3 weeks for experienced team

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI Benchmarks](https://www.techempower.com/benchmarks/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
