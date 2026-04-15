# ADR-006: Stripe Billing Integration

## Status
Accepted

## Date
2026-04-01

## Context
ConsentChain operates as a multi-tenant SaaS platform serving data fiduciaries, regulators, and enterprise clients. We needed a billing system to support:

1. **Tiered subscription plans** — Free, Starter, Professional, Enterprise
2. **Monthly and annual billing cycles** — With annual discount incentives
3. **Automated invoicing and payment collection** — Without building payment infrastructure
4. **Usage-based billing readiness** — Future capability to charge per consent operation
5. **Self-service billing portal** — Users manage subscriptions, payment methods, and invoices
6. **Multi-currency support** — For international EU deployments (GDPR compliance markets)
7. **PCI DSS compliance** — Without taking on the burden of storing payment card data

**Alternatives considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **Custom payment integration** | Full control, no vendor lock-in, lower fees at scale | PCI DSS compliance burden, fraud prevention, 3D Secure implementation |
| **Paddle** | Merchant of Record handles taxes globally | Higher fees (5% + 50¢), less customization, slower payout |
| **Lemon Squeezy** | Merchant of Record, modern API | Newer platform, less mature ecosystem, limited enterprise features |
| **Chargebee + Stripe** | Robust subscription management, analytics | Additional cost, complexity of two-vendor integration |
| **Stripe Billing** | Industry standard, excellent developer experience, hosted checkout | Vendor lock-in, fees at scale (2.9% + 30¢), webhook management |

## Decision
Adopt **Stripe Billing** as our payment processing and subscription management platform, integrated via Stripe's Checkout Sessions and Customer Portal.

### Architecture

```
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  ConsentChain    │     │   Stripe API      │     │  Stripe Checkout │
│  Dashboard       │     │                   │     │  (Hosted)        │
│                  │     │  • Customers      │     │                  │
│  ┌────────────┐  │     │  • Subscriptions  │     │  ┌────────────┐  │
│  │ Plan Select ├──┼────>│  • Products       ├────>│  │ Payment    │  │
│  │ & Checkout │  │     │  • Prices         │     │  │ Form       │  │
│  └────────────┘  │     │  • Invoices       │     │  └────────────┘  │
│                  │     │  • PaymentMethods │     │                  │
│  ┌────────────┐  │     └─────────┬─────────┘     └──────────────────┘
│  │ Billing     │  │               │
│  │ Portal     │  │     ┌─────────┴─────────┐
│  └────────────┘  │     │  Stripe Webhooks  │
│                  │     │                   │
│  ┌────────────┐  │     │  • checkout.session │
│  │ Invoice     │  │<────┤    .completed     │
│  │ History    │  │     │  • customer.        │
│  └────────────┘  │     │    subscription.*   │
└──────────────────┘     │  • invoice.paid     │
                         │  • invoice.         │
                         │    payment_failed   │
                         └─────────┬─────────┘
                                   │
                         ┌─────────┴─────────┐
                         │  ConsentChain API │
                         │  /api/v1/billing  │
                         │  /webhook         │
                         └───────────────────┘
```

### Pricing Tiers

| Plan | Monthly | Annual | API Rate Limit | Consent Records | Audit Retention |
|---|---|---|---|---|---|
| **Free** | $0 | $0 | 100/min | 1,000 | 30 days |
| **Starter** | $29 | $290 (save 17%) | 500/min | 50,000 | 1 year |
| **Professional** | $99 | $990 (save 17%) | 2,000/min | 500,000 | 3 years |
| **Enterprise** | Custom | Custom | Unlimited | Unlimited | 7+ years |

### Implementation

- `api/billing/__init__.py` — Stripe webhook handling and subscription management
- `/api/v1/billing/webhook` — Stripe event processing with signature verification
- `/api/v1/billing/{tenant_id}/checkout` — Create Stripe Checkout Session
- `/api/v1/billing/{tenant_id}/portal` — Create Stripe Customer Portal Session
- `/api/v1/billing/{tenant_id}/status` — Get current billing status
- `/api/v1/billing/{tenant_id}/invoices` — List invoice history
- `STRIPE_WEBHOOK_SECRET` — Environment variable for webhook signature verification
- `STRIPE_API_KEY` — Stripe secret key for API calls
- `BillingEventDB` — Database model for tracking billing events and Stripe events

### Webhook Events Handled

| Event | Action |
|---|---|
| `checkout.session.completed` | Activate tenant subscription |
| `customer.subscription.created` | Record subscription, activate tenant |
| `customer.subscription.updated` | Update tenant status (active/past_due/cancelled) |
| `customer.subscription.deleted` | Cancel tenant subscription, downgrade to Free |
| `invoice.paid` | Record payment, ensure active status |
| `invoice.payment_failed` | Flag tenant after 3+ failed attempts |
| `customer.created` | Link Stripe customer to tenant |

## Consequences

### Positive
- **Rapid time-to-market** — Hosted checkout and portal reduce development to days
- **PCI DSS compliance offloaded** — Stripe handles all card data, we never touch PAN
- **Automatic tax calculation** — Stripe Tax handles VAT, GST, sales tax by jurisdiction
- **Dunning management** — Automatic retry logic for failed payments
- **Rich analytics** — Stripe Dashboard provides MRR, churn, LTV metrics out of the box
- **Global payments** — 135+ currencies, local payment methods (SEPA, iDEAL, etc.)
- **Idempotent webhooks** — Event deduplication via `stripe_event_id` tracking

### Negative
- **Vendor lock-in** — Migration to another provider requires rebuilding checkout and portal flows
- **Webhook reliability dependency** — Missed webhooks can cause billing state inconsistencies
- **Fee structure** — 2.9% + 30¢ per transaction adds up at scale
- **Test complexity** — Stripe test mode doesn't perfectly replicate production behavior
- **European data transfer** — Stripe is a US company; SCCs required for GDPR compliance
- **Webhook signature verification** — Must be implemented correctly to prevent forged events

## Migration Path
If we need to migrate away from Stripe in the future:

1. Abstract payment provider interface (currently `api/billing/__init__.py` is Stripe-specific)
2. Build provider adapter for replacement (Paddle, etc.)
3. Export customer and subscription data from Stripe API
4. Implement data migration for existing subscriptions
5. Run dual-billing during transition period
6. Redirect checkout flows to new provider

## References
- [Stripe Billing Documentation](https://stripe.com/docs/billing)
- [Stripe Webhook Security](https://stripe.com/docs/webhooks/signatures)
- [Stripe Checkout Integration](https://stripe.com/docs/payments/checkout)
- [PCI DSS Compliance](https://www.pcisecuritystandards.org/)
- [GDPR and US Data Transfers (SCCs)](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en)
