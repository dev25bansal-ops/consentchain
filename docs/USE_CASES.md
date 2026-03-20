# Use Cases and Integration Examples

## Industry-Specific Implementations

### 1. Fintech - Digital Lending Platform

#### Problem

A digital lending platform needs explicit consent from borrowers to:

- Access credit history data
- Share data with partner banks
- Use data for fraud detection analytics

#### ConsentChain Integration

```python
from sdk.client import ConsentChainClient, ConsentPurpose, DataType

# Initialize client
client = ConsentChainClient(
    api_url="https://api.consentchain.io",
    api_key="cc_fintech_api_key",
    fiduciary_id="fintech-company-uuid"
)

# When user applies for loan
def process_loan_application(user_wallet, user_email):
    # Create consent for credit check
    consent = client.create_consent(
        principal_wallet=user_wallet,
        purpose=ConsentPurpose.COMPLIANCE.value,
        data_types=[
            DataType.FINANCIAL_DATA.value,
            DataType.PERSONAL_INFO.value
        ],
        duration_days=90,  # Valid during loan processing
        metadata={
            "application_id": "loan_app_123",
            "loan_type": "personal_loan",
            "amount": 500000
        }
    )

    # Store consent_id with application
    application.consent_id = consent.consent_id

    # Before accessing credit bureau
    result = client.verify_consent(consent.consent_id)
    if result.valid:
        # Proceed with credit check
        credit_data = credit_bureau.fetch(user_email)
    else:
        raise PermissionError("Consent not valid")

    return consent
```

#### Benefits

- Immutable proof of consent for regulatory audits
- User can revoke consent at any time
- Clear audit trail for dispute resolution

---

### 2. Healthcare - Patient Data Management

#### Problem

A hospital needs patient consent to:

- Store medical records electronically
- Share data with specialists for referrals
- Use anonymized data for research

#### ConsentChain Integration

```python
# Healthcare consent creation
def create_healthcare_consent(patient_wallet, hospital_id):
    client = ConsentChainClient(
        api_url="https://api.consentchain.io",
        api_key="cc_hospital_api_key",
        fiduciary_id=hospital_id
    )

    # Primary care consent
    primary_consent = client.create_consent(
        principal_wallet=patient_wallet,
        purpose=ConsentPurpose.SERVICE_DELIVERY.value,
        data_types=[
            DataType.HEALTH_DATA.value,
            DataType.PERSONAL_INFO.value,
            DataType.CONTACT_INFO.value
        ],
        duration_days=365,
        metadata={
            "department": "general_medicine",
            "doctor_id": "dr_456",
            "treatment_type": "routine_checkup"
        }
    )

    return primary_consent

# Referral consent (additional)
def create_referral_consent(patient_wallet, specialist_type):
    referral_consent = client.create_consent(
        principal_wallet=patient_wallet,
        purpose=ConsentPurpose.THIRD_PARTY_SHARING.value,
        data_types=[
            DataType.HEALTH_DATA.value,
            DataType.SENSITIVE_DATA.value  # If applicable
        ],
        duration_days=30,  # Short term referral
        metadata={
            "referral_type": specialist_type,
            "sharing_purpose": "second_opinion"
        }
    )

    return referral_consent
```

#### Dashboard Integration for Patients

```html
<!-- Embed in patient portal -->
<div id="consentchain-widget">
  <h3>Your Medical Data Consents</h3>
  <div v-for="consent in consents">
    <div class="consent-card">
      <span class="purpose">{{ consent.purpose }}</span>
      <span class="data-types">
        Data: {{ consent.data_types.join(', ') }}
      </span>
      <button @click="revokeConsent(consent.id)">Revoke Access</button>
    </div>
  </div>
</div>
```

---

### 3. E-commerce - Marketing Personalization

#### Problem

An e-commerce platform wants to:

- Personalize product recommendations
- Send promotional emails
- Analyze shopping behavior

#### ConsentChain Integration

```python
# E-commerce consent for marketing
def request_marketing_consent(customer_wallet, email):
    client = ConsentChainClient(
        api_url="https://api.consentchain.io",
        api_key="cc_ecommerce_api_key",
        fiduciary_id="ecommerce-platform-uuid"
    )

    # Check if consent exists
    existing_consents = client.query_consents(
        principal_wallet=customer_wallet,
        status="GRANTED",
        purpose="MARKETING"
    )

    if existing_consents:
        return existing_consents[0]

    # Create new consent request
    consent = client.create_consent(
        principal_wallet=customer_wallet,
        purpose=ConsentPurpose.MARKETING.value,
        data_types=[
            DataType.PERSONAL_INFO.value,
            DataType.CONTACT_INFO.value,
            DataType.BEHAVIORAL_DATA.value
        ],
        duration_days=90,  # Quarterly renewal
        metadata={
            "channels": ["email", "push_notification"],
            "preferences": {
                "newsletter": True,
                "sale_alerts": True,
                "personalized_ads": False
            }
        }
    )

    return consent

# Before sending promotional email
def send_promotional_email(customer_id):
    customer = get_customer(customer_id)

    # Verify consent before sending
    result = client.check_consent_before_action(
        principal_id=customer.principal_id,
        purpose="MARKETING",
        data_types=["CONTACT_INFO", "BEHAVIORAL_DATA"]
    )

    if result.valid:
        send_email(customer.email, personalized_content())
    else:
        # Log consent invalidation
        log_consent_expired(customer_id)
```

---

### 4. Banking - Open Banking API

#### Problem

A bank implementing open banking needs to:

- Allow third-party apps to access account data
- Provide clear consent mechanism for users
- Generate compliance reports for RBI

#### ConsentChain Integration

```python
# Open Banking consent creation
def create_open_banking_consent(
    customer_wallet,
    third_party_app,
    data_permissions,
    duration_days
):
    client = ConsentChainClient(
        api_url="https://api.consentchain.io",
        api_key="cc_bank_api_key",
        fiduciary_id="bank-uuid"
    )

    consent = client.create_consent(
        principal_wallet=customer_wallet,
        purpose=ConsentPurpose.THIRD_PARTY_SHARING.value,
        data_types=data_permissions,
        duration_days=duration_days,
        metadata={
            "third_party": third_party_app,
            "api_version": "OB_2.0",
            "permissions": [
                "ReadAccountsBasic",
                "ReadAccountsDetail",
                "ReadTransactionsBasic"
            ],
            "purpose_text": f"Allow {third_party_app} to view your account information"
        }
    )

    return consent

# API Gateway middleware
def verify_open_banking_access(request):
    consent_id = request.headers.get("X-Consent-ID")

    result = client.verify_consent(consent_id)

    if not result.valid:
        raise HTTPException(
            status_code=403,
            detail="Consent invalid or revoked"
        )

    # Check if requested data is within consent scope
    requested_data = get_requested_data_type(request)
    if requested_data not in result.data_types:
        raise HTTPException(
            status_code=403,
            detail="Data type not covered by consent"
        )

    return result
```

---

## Integration Patterns

### 1. Web Application Integration (Django/Flask)

```python
# Django middleware
from django.http import JsonResponse
from sdk.client import ConsentChainClient

class ConsentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.client = ConsentChainClient(
            api_url=settings.CONSENTCHAIN_API_URL,
            api_key=settings.CONSENTCHAIN_API_KEY,
            fiduciary_id=settings.FIDUCIARY_ID
        )

    def __call__(self, request):
        # Skip public paths
        if request.path in settings.PUBLIC_PATHS:
            return self.get_response(request)

        # Get user's consent
        user = request.user
        if user.is_authenticated:
            result = self.client.check_consent_before_action(
                principal_id=str(user.principal_id),
                purpose="SERVICE_DELIVERY",
                data_types=["PERSONAL_INFO"]
            )

            if not result.valid:
                return JsonResponse({
                    "error": "Consent required",
                    "redirect": "/consent/request"
                }, status=403)

        return self.get_response(request)
```

### 2. Mobile App Integration (React Native)

```typescript
// ConsentChain SDK wrapper for React Native
import { NativeModules } from "react-native";

const { ConsentChainModule } = NativeModules;

class ConsentService {
  async createConsent(
    walletAddress: string,
    purpose: string,
    dataTypes: string[],
    durationDays: number,
  ): Promise<string> {
    const consentId = await ConsentChainModule.createConsent({
      walletAddress,
      purpose,
      dataTypes,
      durationDays,
    });
    return consentId;
  }

  async verifyConsent(consentId: string): Promise<boolean> {
    const isValid = await ConsentChainModule.verifyConsent(consentId);
    return isValid;
  }

  async revokeConsent(consentId: string, reason?: string): Promise<void> {
    await ConsentChainModule.revokeConsent(consentId, reason);
  }
}

export default new ConsentService();
```

### 3. API Gateway Integration (Kong/Express Gateway)

```yaml
# Kong plugin configuration
plugins:
  - name: consentchain-auth
    config:
      api_url: https://api.consentchain.io
      api_key: cc_gateway_api_key
      fiduciary_id: gateway-fiduciary-uuid
      required_scopes:
        - purpose: SERVICE_DELIVERY
          data_types:
            - PERSONAL_INFO
      cache_ttl: 60
```

### 4. Webhook Integration for Real-time Updates

```python
# Webhook handler for consent events
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/webhooks/consentchain")
async def handle_consent_event(request: Request):
    payload = await request.json()
    event_type = payload.get("event_type")
    consent_id = payload.get("consent_id")

    if event_type == "consent.granted":
        # Update user record
        await update_user_consent_status(
            consent_id,
            status="granted"
        )
        # Enable features that require consent
        await enable_personalized_features(consent_id)

    elif event_type == "consent.revoked":
        # Immediately stop processing
        await disable_data_processing(consent_id)
        # Schedule data deletion
        await schedule_data_deletion(
            consent_id,
            deadline_days=30  # DPDP requirement
        )
        # Notify downstream systems
        await notify_third_parties(consent_id)

    return {"status": "processed"}

# Register webhook with ConsentChain
def register_webhook():
    response = requests.post(
        f"{API_URL}/api/v1/webhooks/subscribe",
        json={
            "callback_url": "https://your-domain.com/webhooks/consentchain",
            "events": [
                "consent.granted",
                "consent.revoked",
                "consent.expired"
            ],
            "fiduciary_id": FIDUCIARY_ID,
            "secret": WEBHOOK_SECRET
        },
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    return response.json()
```

---

## Sample Workflow: New User Onboarding

```python
# Complete user onboarding with consent
def onboard_new_user(user_data):
    """
    Full workflow for onboarding a new user with explicit consent
    """

    # Step 1: Create user account
    user = create_user_account(user_data)

    # Step 2: Generate Algorand wallet (or use existing)
    if not user.wallet_address:
        wallet = generate_algorand_wallet()
        user.wallet_address = wallet.address
        user.wallet_mnemonic = wallet.mnemonic  # Store securely!
        save_user(user)

    # Step 3: Display consent request
    consent_request = {
        "principal_wallet": user.wallet_address,
        "fiduciary_id": FIDUCIARY_ID,
        "purpose": "SERVICE_DELIVERY",
        "data_types": [
            "PERSONAL_INFO",
            "CONTACT_INFO",
            "BEHAVIORAL_DATA"
        ],
        "duration_days": 365,
        "description": """
            We need your consent to:
            - Process your personal information for account management
            - Send you service-related notifications
            - Personalize your experience based on usage patterns

            You can revoke this consent at any time from your dashboard.
        """
    }

    # Step 4: User signs consent request
    signature = request_user_signature(
        user.wallet_address,
        consent_request
    )

    # Step 5: Create consent on-chain
    consent = client.create_consent(
        principal_wallet=user.wallet_address,
        purpose=consent_request["purpose"],
        data_types=consent_request["data_types"],
        duration_days=consent_request["duration_days"],
        signature=signature
    )

    # Step 6: Store consent reference
    user.consent_id = consent.consent_id
    user.on_chain_tx_id = consent.on_chain_tx_id
    save_user(user)

    # Step 7: Enable services
    enable_user_services(user.id)

    # Step 8: Log audit event
    log_audit_event(
        action="USER_ONBOARDED",
        principal_id=user.id,
        consent_id=consent.consent_id
    )

    return {
        "user_id": user.id,
        "consent_id": str(consent.consent_id),
        "tx_id": consent.on_chain_tx_id,
        "expires_at": consent.expires_at
    }
```

---

## Best Practices

### 1. Consent Collection UI

```
✓ DO:
- Use clear, plain language
- Separate consent for each purpose
- Show what data will be collected
- Display consent duration
- Provide easy revocation mechanism

✗ DON'T:
- Use pre-checked boxes
- Bundle multiple purposes together
- Hide consent in terms of service
- Make revocation difficult
- Collect more data than stated
```

### 2. Data Handling

```python
# Always verify consent before data access
def access_user_data(user_id, data_type):
    consent = get_active_consent(user_id, data_type)

    if not consent:
        raise ConsentRequiredError(
            f"No consent for {data_type}. Request consent first."
        )

    if consent.expires_at < datetime.utcnow():
        raise ConsentExpiredError(
            "Consent expired. Please renew."
        )

    # Verify on-chain
    result = client.verify_consent(consent.consent_id)
    if not result.valid:
        raise ConsentInvalidError(
            f"Consent invalid: {result.reason}"
        )

    # Log access
    log_data_access(user_id, data_type, consent.consent_id)

    # Return data
    return get_data(user_id, data_type)
```

### 3. Graceful Degradation

```python
# Handle consent revocation gracefully
def handle_revoked_consent(user_id):
    # Immediately stop processing
    stop_data_processing(user_id)

    # Notify user
    send_notification(
        user_id,
        "Your consent has been recorded. "
        "Data deletion will complete within 30 days."
    )

    # Schedule deletion
    schedule_deletion(user_id, delay_days=30)

    # Offer alternative service
    offer_basic_service(user_id)
```

---

## Support

For integration support:

- Technical Docs: https://docs.consentchain.io
- SDK Reference: https://github.com/your-org/consentchain-sdk
- Sample Apps: https://github.com/your-org/consentchain-examples
- Developer Discord: https://discord.gg/consentchain
