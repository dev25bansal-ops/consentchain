# ADR-003: Multi-Tenant SaaS Architecture

## Status
Accepted

## Date
2025-02-01

## Context
ConsentChain needed to support multiple enterprises (Data Fiduciaries) who each manage consent for their own users (Data Principals). Each enterprise requires:
- Complete data isolation from other tenants
- Independent API keys and authentication
- Separate compliance reporting
- Custom branding and configuration (future requirement)
- Pay-per-use billing (Stripe integration)

**Alternatives considered:**
1. **Single-tenant deployment per enterprise** - Most isolation but expensive to operate
2. **Database-per-tenant** - Good isolation but complex migrations and backups
3. **Shared database, shared schema (row-level isolation)** - Cost-effective, requires careful coding
4. **Hybrid approach** - Shared for small tenants, dedicated for enterprise

## Decision
Implemented **multi-tenant SaaS with row-level isolation** using:

1. **Shared database, shared schema** - All tenants in same tables
2. **`fiduciary_id` foreign key** on all tenant-scoped tables
3. **Tenant isolation middleware** - Automatically filters queries by authenticated tenant
4. **Context propagation** via `ContextVar` - Tenant context available throughout request lifecycle
5. **Stripe integration** - Tiered billing (Free, Starter, Pro, Enterprise)
6. **Tenant management API** - CRUD operations for tenant administration

## Implementation

### Database Schema
```sql
-- All tenant-scoped tables include fiduciary_id
consent_records (id, fiduciary_id, principal_id, ...)
audit_logs (id, fiduciary_id, action, ...)
grievances (id, fiduciary_id, status, ...)
webhook_subscriptions (id, fiduciary_id, callback_url, ...)
```

### Tenant Isolation Middleware
```python
# Automatically adds fiduciary_id filter to all queries
async def tenant_filtered_query(query, model, fiduciary_id):
    return query.where(model.fiduciary_id == fiduciary_id)
```

### Context Propagation
```python
tenant_context: ContextVar[TenantContext] = ContextVar("tenant_context")
# Set in middleware, available throughout request lifecycle
```

## Consequences

### Positive
- **Cost-effective** - Single deployment serves all tenants
- **Easy onboarding** - New tenants require no infrastructure changes
- **Simplified operations** - One database to backup, monitor, scale
- **Consistent updates** - All tenants get features simultaneously
- **Economies of scale** - Infrastructure costs shared across tenants
- **Stripe integration** - Automated billing, dunning, invoicing

### Negative
- **Requires careful coding** - One missing filter = data leak between tenants
- **Noisy neighbor problem** - One tenant's heavy usage affects others
- **Compliance complexity** - Some regulations require data residency (can't share DB)
- **Limited customization** - Can't easily offer tenant-specific features
- **Migration complexity** - Moving a tenant to dedicated deployment is difficult

### Security Risks
- **Tenant data leakage** if `fiduciary_id` filter is missing on any query
- **Privilege escalation** if tenant can access another tenant's resources
- **Billing manipulation** if usage records are incorrectly attributed

### Mitigations
1. **Mandatory tenant filtering** - All queries use `tenant_filtered_query()`
2. **Comprehensive testing** - Test suite includes tenant isolation tests
3. **Audit logging** - All cross-tenant access attempts logged
4. **Regular security audits** - Penetration testing includes tenant isolation checks
5. **API key scoping** - Each tenant has unique API keys, cannot impersonate others

## Scaling Strategy
- **Up to 1,000 tenants** - Current architecture sufficient
- **1,000-10,000 tenants** - Add read replicas, shard by fiduciary_id
- **10,000+ tenants** - Consider database-per-tenant for largest tenants

## Future Enhancements
1. **Custom domains** - Tenant-specific subdomains (tenant.consentchain.io)
2. **Tenant-specific rate limits** - Higher limits for paid tiers
3. **White-label branding** - Custom logos, colors, email templates
4. **Data residency** - Regional deployments for GDPR/compliance requirements
5. **Dedicated instances** - Option for enterprise tenants to get isolated deployment

## References
- [Multi-Tenant Data Architecture (Microsoft)](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/)
- [SaaS Multi-Tenancy Patterns (AWS)](https://aws.amazon.com/blogs/apn/multi-tenancy-saas/)
- [Stripe Billing Documentation](https://stripe.com/docs/billing)
