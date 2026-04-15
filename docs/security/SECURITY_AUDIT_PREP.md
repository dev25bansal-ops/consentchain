# ConsentChain Security Audit Preparation

## Document Control

| Version | Date       | Author        | Changes         |
| ------- | ---------- | ------------- | --------------- |
| 1.0     | 2024-03-20 | Security Team | Initial version |

---

## 1. Executive Summary

This document outlines the security controls, policies, and procedures implemented by ConsentChain to achieve SOC 2 Type I compliance and meet the security requirements of the Digital Personal Data Protection Act, 2023.

---

## 2. System Description

### 2.1 Architecture Overview

ConsentChain is a blockchain-based consent management platform built on Algorand, consisting of:

- **API Layer**: FastAPI-based REST API
- **Blockchain Layer**: Algorand smart contracts (ARC-4)
- **Database Layer**: PostgreSQL with encrypted storage
- **Cache Layer**: Redis for session management
- **IPFS Layer**: Decentralized evidence storage

---

## 3. Security Controls

### 3.1 Access Control (CC6.1 - CC6.3)

#### Authentication

- Multi-factor authentication (MFA) required for all admin users
- Wallet-based authentication for data principals
- API key rotation every 90 days
- Session timeout: 30 minutes of inactivity

#### Authorization

- Role-Based Access Control (RBAC) with 5 roles
- Tenant isolation enforced at middleware level
- Principle of least privilege applied

### 3.2 Encryption (CC6.6 - CC6.7)

- AES-256 encryption for database fields
- TLS 1.3 for data in transit
- Ed25519 signatures for blockchain transactions

### 3.3 Network Security (CC6.6)

- VPC with private subnets
- Web Application Firewall (WAF)
- Rate limiting: 100 req/min per API key

### 3.4 Logging and Monitoring (CC7.1 - CC7.3)

- All security-relevant events are logged
- Log retention: 90 days operational, 7 years compliance
- Real-time alerting for security events

---

## 4. Compliance Mapping

### 4.1 DPDP Act Requirements

| Section | Requirement                | Implementation                  |
| ------- | -------------------------- | ------------------------------- |
| S.4     | Consent before processing  | Blockchain consent records      |
| S.6     | Data Fiduciary obligations | Audit trail, retention policies |
| S.7     | Consent management         | Granular consent system         |
| S.8     | Data breach notification   | Incident response procedures    |
| S.9     | Right to erasure           | Deletion orchestration          |
| S.13    | Grievance redressal        | Grievance management system     |
| S.14    | Guardian provisions        | Nominated representative flow   |

### 4.2 SOC 2 Trust Services Criteria

| Criteria                        | Status   | Evidence                |
| ------------------------------- | -------- | ----------------------- |
| CC6.1 - Logical Access          | Complete | RBAC, MFA documentation |
| CC6.2 - Access Authorization    | Complete | Policy, access reviews  |
| CC6.3 - Access Removal          | Complete | HR process, automation  |
| CC6.6 - Transmission Protection | Complete | TLS 1.3 configuration   |
| CC6.7 - Data Protection         | Complete | Encryption policy       |
| CC7.1 - System Monitoring       | Complete | SIEM dashboards         |
| CC7.2 - Anomaly Detection       | Complete | Alert rules             |
| CC8.1 - Change Management       | Complete | CAB process             |

---

## 5. Incident Response

### 5.1 Incident Classification

| Severity      | Description                    | Response Time |
| ------------- | ------------------------------ | ------------- |
| P1 - Critical | Data breach, system compromise | 15 minutes    |
| P2 - High     | Security vulnerability exploit | 1 hour        |
| P3 - Medium   | Suspicious activity            | 4 hours       |
| P4 - Low      | Minor security event           | 24 hours      |

### 5.2 Data Breach Notification (DPDP Section 8)

- Data principals: Within 72 hours of breach
- Data Protection Authority: Within 72 hours
- Documentation of all breaches maintained

---

## 6. Security Certifications Roadmap

| Milestone                     | Target Date | Status      |
| ----------------------------- | ----------- | ----------- |
| Security policy documentation | Q1 2024     | Complete    |
| Penetration testing           | Q2 2024     | In Progress |
| SOC 2 Type I audit            | Q3 2024     | Scheduled   |
| SOC 2 Type II audit           | Q4 2024     | Planned     |
| ISO 27001 certification       | Q2 2025     | Planned     |

---

## 7. Contact Information

- Security Team: security@consentchain.io
- Data Protection Officer: dpo@consentchain.io
- Incident Response: incident@consentchain.io
