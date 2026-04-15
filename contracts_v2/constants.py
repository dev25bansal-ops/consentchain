from consentchain_types.enums import ConsentStatus, ConsentPurpose, DataType, EventType


CONSENT_STATUS_MAP = {
    ConsentStatus.PENDING: 0,
    ConsentStatus.GRANTED: 1,
    ConsentStatus.REVOKED: 2,
    ConsentStatus.EXPIRED: 3,
    ConsentStatus.MODIFIED: 4,
}

STATUS_TO_CONSENT = {v: k for k, v in CONSENT_STATUS_MAP.items()}


EVENT_TYPE_MAP = {
    EventType.CONSENT_GRANTED: 1,
    EventType.CONSENT_REVOKED: 2,
    EventType.CONSENT_MODIFIED: 3,
    EventType.CONSENT_EXPIRY: 4,
    EventType.DATA_ACCESS: 5,
    EventType.DATA_DELETION: 6,
}

EVENT_TYPE_TO_STR = {v: k for k, v in EVENT_TYPE_MAP.items()}
