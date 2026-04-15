# ADR-001: Use Algorand Blockchain for Consent Records

## Status
Accepted

## Date
2025-01-15

## Context
We needed a blockchain platform for immutable consent record audit trails. The DPDP Act 2023 requires demonstrable compliance with consent management, and we needed a tamper-proof ledger to prove consent was granted, modified, or revoked at specific points in time.

**Requirements:**
- Low transaction costs (< $0.001 per consent operation)
- Fast finality (< 5 seconds for user experience)
- Smart contract support for consent lifecycle logic
- Environmental sustainability (corporate ESG requirements)
- Developer-friendly tooling with Python support
- Regulatory compliance story for DPDP Act

**Alternatives considered:**
- Ethereum (L1): Too expensive ($5-50+ per transaction), slow finality
- Polygon: Good costs but centralization concerns
- Hyperledger Fabric: Complex infrastructure, not public/auditable
- Solana: Fast but history of network instability

## Decision
Chose **Algorand** as our blockchain platform because:

1. **Pure Proof-of-Stake consensus** - Energy efficient, aligns with ESG goals
2. **Low transaction fees** (~$0.001) - Makes consent operations economically viable at scale
3. **Fast block times** (~3.5 seconds) - Good user experience for consent verification
4. **PyTeal/algopy** - Python-based smart contract development matches our backend stack
5. **Immediate finality** - No fork risk, consent records are immutable once confirmed
6. **Built-in governance** - Good compliance story for regulators
7. **Arc-4 contracts** - Modern Python-native contract development with algopy

## Implementation
- **PyTeal v1** for initial contract deployment (legacy)
- **algopy ARC-4** v2 contracts for current deployment
- **ConsentRegistry**: Manages consent lifecycle (grant, revoke, modify, expire)
- **AuditTrail**: Merkle-root anchored audit trail with event chaining
- **Box storage model** for efficient on-chain data storage

## Consequences

### Positive
- **Low operational costs** - Can process millions of consents affordably
- **Fast user experience** - 3-5 second confirmation times
- **Python-friendly development** - Same language as backend
- **Good compliance story** - Immutable, auditable, regulator-friendly
- **ESG alignment** - Carbon-neutral blockchain operations

### Negative
- **Smaller developer ecosystem** than Ethereum - harder to find experienced developers
- **Less mature tooling** - Fewer libraries, examples, and community resources
- **Network dependency** - Relies on Algorand node availability (mitigated with multiple endpoints)
- **Vendor lock-in** - Migration to another blockchain would require significant rework
- **Learning curve** - Team needed to learn blockchain development concepts

## Migration Path
If we need to support multiple blockchains in the future:
1. Abstract blockchain interface layer (already partially implemented in `contracts/client.py`)
2. Implement adapters for other chains (Ethereum, Polygon)
3. Deploy parallel contracts on additional chains
4. Maintain Algorand as primary, others as secondary/backup

## References
- [Algorand Developer Documentation](https://developer.algorand.org/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/)
- [ARC-4 Contract Specification](https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0004.md)
- [DPDP Act 2023](https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf)
