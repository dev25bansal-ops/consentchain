"""User-friendly error messages for ConsentChain API."""

ERROR_MESSAGES = {
    "CONSENT_NOT_FOUND": "The consent record you requested could not be found. It may have been deleted or the ID is incorrect.",
    "CONSENT_REVOKED": "This consent has already been revoked and cannot be modified.",
    "CONSENT_EXPIRED": "This consent has expired and is no longer valid.",
    "CONSENT_ALREADY_GRANTED": "A consent record with these details already exists.",
    "INVALID_SIGNATURE": "The digital signature verification failed. Please ensure you are signing with the correct wallet.",
    "SIGNATURE_REQUIRED": "A valid digital signature is required for this operation.",
    "FIDUCIARY_NOT_FOUND": "The specified data fiduciary could not be found. Please verify the fiduciary ID.",
    "FIDUCIARY_INACTIVE": "This fiduciary account is not active. Please contact support.",
    "PRINCIPAL_NOT_FOUND": "The data principal could not be found. Please verify your wallet address is registered.",
    "INVALID_API_KEY": "The API key provided is invalid or has been revoked. Please check your credentials.",
    "API_KEY_EXPIRED": "Your API key has expired. Please generate a new one from your dashboard.",
    "TOKEN_EXPIRED": "Your session has expired. Please log in again to continue.",
    "INVALID_TOKEN": "The authentication token is invalid. Please log in again.",
    "REFRESH_TOKEN_EXPIRED": "Your refresh token has expired. Please log in again.",
    "RATE_LIMIT_EXCEEDED": "Too many requests. Please wait a moment before trying again.",
    "BLOCKCHAIN_ERROR": "A blockchain transaction error occurred. Please try again later.",
    "IPFS_ERROR": "Failed to store data on IPFS. Please try again later.",
    "DATABASE_ERROR": "A database error occurred. Please try again later.",
    "VALIDATION_ERROR": "The request contains invalid data. Please check your input and try again.",
    "COMPLIANCE_VIOLATION": {
        "SENSITIVE_DATA_MARKETING": "Sensitive personal data cannot be used for marketing purposes. Please select different data types or purpose.",
        "INVALID_DURATION": "The consent duration exceeds the maximum allowed period for this purpose.",
        "MISSING_PURPOSE": "A valid purpose is required for consent.",
        "MISSING_DATA_TYPES": "At least one data type must be specified for consent.",
    },
    "GRIEVANCE_NOT_FOUND": "The grievance could not be found. Please verify the grievance ID.",
    "GRIEVANCE_ALREADY_RESOLVED": "This grievance has already been resolved.",
    "GUARDIAN_NOT_FOUND": "The nominated representative could not be found.",
    "GUARDIAN_NOT_VERIFIED": "The nominated representative has not been verified yet.",
    "GUARDIAN_EXPIRED": "The nominated representative's authorization has expired.",
    "DELETION_REQUEST_NOT_FOUND": "The deletion request could not be found.",
    "DELETION_ALREADY_COMPLETED": "This data has already been deleted.",
    "DELETION_IN_PROGRESS": "Data deletion is currently in progress. You will be notified when complete.",
    "VERIFICATION_CODE_INVALID": "The verification code is invalid or has expired.",
    "WEBHOOK_DELIVERY_FAILED": "Failed to deliver webhook notification. The system will retry automatically.",
    "TEMPLATE_NOT_FOUND": "The consent template could not be found.",
    "TEMPLATE_INACTIVE": "This template is no longer active.",
}

COMPLIANCE_ERROR_MESSAGES = {
    "sensitive_data_marketing": "Sensitive personal data (health, biometric, financial) cannot be used for marketing. Please select appropriate data types.",
    "health_data_third_party": "Health data cannot be shared with third parties without explicit consent.",
    "biometric_data_sharing": "Biometric data sharing requires additional verification.",
    "financial_data_analytics": "Financial data cannot be used for analytics without explicit consent.",
    "duration_exceeded": "The consent duration exceeds the maximum allowed period. Maximum is 365 days.",
    "minor_consent": "Consent for minors must be provided by a nominated representative.",
    "guardian_required": "A nominated representative is required for this operation.",
}


def get_error_message(error_code: str, context: dict = None) -> str:
    """Get a user-friendly error message."""
    message = ERROR_MESSAGES.get(error_code, f"An error occurred: {error_code}")

    if isinstance(message, dict) and context:
        sub_key = context.get("sub_type")
        if sub_key and sub_key in message:
            return message[sub_key]
        return message.get("default", "An error occurred.")

    return message


def format_validation_error(field: str, value: any, reason: str) -> str:
    """Format a validation error with context."""
    return f"Invalid value for '{field}': {reason}. Received: {value}"
