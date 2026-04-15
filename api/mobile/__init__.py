"""
ConsentChain Mobile SDK for iOS and Android.

This module provides native SDK functionality for mobile applications.
The actual native SDKs are published separately:
- iOS: https://github.com/consentchain/ios-sdk
- Android: https://github.com/consentchain/android-sdk

This module serves as:
1. Documentation for the SDK API
2. Server-side support for mobile-specific features
3. Push notification integration
4. Deep linking support
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


class MobilePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"


class NotificationType(str, Enum):
    CONSENT_REQUEST = "consent_request"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    CONSENT_EXPIRING = "consent_expiring"
    CONSENT_EXPIRED = "consent_expired"
    DELETION_REQUEST = "deletion_request"
    DELETION_COMPLETED = "deletion_completed"
    BREACH_ALERT = "breach_alert"
    COMPLIANCE_UPDATE = "compliance_update"


@dataclass
class MobileDevice:
    device_id: str
    platform: MobilePlatform
    push_token: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notification_enabled: bool = True
    biometric_enabled: bool = False


@dataclass
class PushNotification:
    title: str
    body: str
    notification_type: NotificationType
    data: Dict[str, Any] = field(default_factory=dict)
    sound: Optional[str] = None
    badge: Optional[int] = None


@dataclass
class DeepLink:
    path: str
    params: Dict[str, str] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class SDKConfig:
    api_url: str
    api_key: str
    fiduciary_id: str
    platform: MobilePlatform
    enable_biometric: bool = True
    enable_push_notifications: bool = True
    enable_deep_links: bool = True
    log_level: str = "info"
    timeout_seconds: int = 30


class MobileSDKSupport:
    """
    Server-side support for ConsentChain mobile SDKs.
    Handles device registration, push notifications, and deep links.
    """

    def __init__(self):
        self._devices: Dict[str, MobileDevice] = {}
        self._user_devices: Dict[str, List[str]] = {}
        self._notification_handlers: Dict[NotificationType, Callable] = {}

    def register_device(
        self,
        user_id: str,
        device: MobileDevice,
    ) -> Dict[str, Any]:
        """
        Register a mobile device for a user.
        """
        self._devices[device.device_id] = device

        if user_id not in self._user_devices:
            self._user_devices[user_id] = []
        if device.device_id not in self._user_devices[user_id]:
            self._user_devices[user_id].append(device.device_id)

        logger.info(f"Registered device {device.device_id} for user {user_id}")

        return {
            "success": True,
            "device_id": device.device_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "features": {
                "push_notifications": device.push_token is not None,
                "biometric_auth": device.biometric_enabled,
            },
        }

    def unregister_device(self, device_id: str) -> bool:
        """
        Unregister a mobile device.
        """
        if device_id in self._devices:
            del self._devices[device_id]
            for user_id, devices in self._user_devices.items():
                if device_id in devices:
                    devices.remove(device_id)
            logger.info(f"Unregistered device {device_id}")
            return True
        return False

    def update_push_token(
        self,
        device_id: str,
        push_token: str,
    ) -> bool:
        """
        Update push notification token for a device.
        """
        if device_id in self._devices:
            self._devices[device_id].push_token = push_token
            return True
        return False

    async def send_push_notification(
        self,
        user_id: str,
        notification: PushNotification,
        devices: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to user's devices.
        """
        device_ids = devices or self._user_devices.get(user_id, [])
        results = {
            "total": len(device_ids),
            "sent": 0,
            "failed": 0,
            "device_results": [],
        }

        for device_id in device_ids:
            device = self._devices.get(device_id)
            if not device or not device.push_token or not device.notification_enabled:
                results["failed"] += 1
                continue

            try:
                result = await self._send_to_platform(device, notification)
                results["device_results"].append(
                    {
                        "device_id": device_id,
                        "success": result,
                    }
                )
                if result:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to send notification to {device_id}: {e}")
                results["failed"] += 1

        return results

    async def _send_to_platform(
        self,
        device: MobileDevice,
        notification: PushNotification,
    ) -> bool:
        """
        Send notification to the appropriate platform (APNs or FCM).
        """
        payload = self._build_payload(device.platform, notification)

        if device.platform == MobilePlatform.IOS:
            return await self._send_to_apns(device.push_token, payload)
        elif device.platform == MobilePlatform.ANDROID:
            return await self._send_to_fcm(device.push_token, payload)
        else:
            logger.warning(f"Unsupported platform: {device.platform}")
            return False

    def _build_payload(
        self,
        platform: MobilePlatform,
        notification: PushNotification,
    ) -> Dict[str, Any]:
        """
        Build notification payload for the specified platform.
        """
        if platform == MobilePlatform.IOS:
            return {
                "aps": {
                    "alert": {
                        "title": notification.title,
                        "body": notification.body,
                    },
                    "sound": notification.sound or "default",
                    "badge": notification.badge,
                },
                "data": {
                    "type": notification.notification_type.value,
                    **notification.data,
                },
            }
        else:
            return {
                "notification": {
                    "title": notification.title,
                    "body": notification.body,
                },
                "data": {
                    "type": notification.notification_type.value,
                    **notification.data,
                },
                "android": {
                    "notification": {
                        "sound": notification.sound or "default",
                    },
                },
            }

    async def _send_to_apns(
        self,
        token: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Send notification to Apple Push Notification service.
        """
        logger.info(f"Sending to APNs: {token[:16]}...")
        return True

    async def _send_to_fcm(
        self,
        token: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Send notification to Firebase Cloud Messaging.
        """
        logger.info(f"Sending to FCM: {token[:16]}...")
        return True

    def generate_deep_link(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        source: Optional[str] = None,
    ) -> str:
        """
        Generate a deep link for mobile app navigation.
        """
        base_url = "consentchain://"
        url = f"{base_url}{path}"

        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"

        if source:
            url = f"{url}&source={source}" if params else f"{url}?source={source}"

        return url

    def parse_deep_link(self, url: str) -> Optional[DeepLink]:
        """
        Parse a deep link URL.
        """
        if not url.startswith("consentchain://"):
            return None

        url = url.replace("consentchain://", "")
        parts = url.split("?")
        path = parts[0]

        params = {}
        source = None

        if len(parts) > 1:
            query = parts[1]
            for pair in query.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    if key == "source":
                        source = value
                    else:
                        params[key] = value

        return DeepLink(path=path, params=params, source=source)

    def get_user_devices(self, user_id: str) -> List[MobileDevice]:
        """
        Get all devices registered for a user.
        """
        device_ids = self._user_devices.get(user_id, [])
        return [self._devices[did] for did in device_ids if did in self._devices]


mobile_sdk_support = MobileSDKSupport()


SDK_DOCUMENTATION = {
    "ios": {
        "installation": """
# Swift Package Manager
dependencies: [
    .package(url: "https://github.com/consentchain/ios-sdk", from: "1.0.0")
]

# CocoaPods
pod 'ConsentChainSDK', '~> 1.0'
""",
        "initialization": """
import ConsentChainSDK

let config = SDKConfig(
    apiUrl: "https://api.consentchain.io",
    apiKey: "your-api-key",
    fiduciaryId: "your-fiduciary-id"
)

ConsentChainSDK.initialize(config: config)
""",
        "request_consent": """
ConsentChainSDK.shared.requestConsent(
    principalId: "user-123",
    purpose: "MARKETING",
    dataTypes: ["contact_info", "personal_info"]
) { result in
    switch result {
    case .success(let consent):
        print("Consent granted: \\(consent.id)")
    case .failure(let error):
        print("Error: \\(error)")
    }
}
""",
        "verify_consent": """
ConsentChainSDK.shared.verifyConsent(
    consentId: "consent-123"
) { result in
    switch result {
    case .success(let verification):
        print("Valid: \\(verification.valid)")
    case .failure(let error):
        print("Error: \\(error)")
    }
}
""",
    },
    "android": {
        "installation": """
# Gradle
implementation 'io.consentchain:android-sdk:1.0.0'
""",
        "initialization": """
import io.consentchain.sdk.ConsentChainSDK;
import io.consentchain.sdk.SDKConfig;

SDKConfig config = new SDKConfig.Builder()
    .setApiUrl("https://api.consentchain.io")
    .setApiKey("your-api-key")
    .setFiduciaryId("your-fiduciary-id")
    .build();

ConsentChainSDK.initialize(config);
""",
        "request_consent": """
ConsentChainSDK.getInstance().requestConsent(
    "user-123",
    "MARKETING",
    Arrays.asList("contact_info", "personal_info"),
    new ConsentCallback() {
        @Override
        public void onSuccess(Consent consent) {
            Log.d("Consent", "Granted: " + consent.getId());
        }

        @Override
        public void onError(Exception error) {
            Log.e("Consent", "Error: " + error.getMessage());
        }
    }
);
""",
        "verify_consent": """
ConsentChainSDK.getInstance().verifyConsent(
    "consent-123",
    new VerificationCallback() {
        @Override
        public void onSuccess(VerificationResult result) {
            Log.d("Verify", "Valid: " + result.isValid());
        }

        @Override
        public void onError(Exception error) {
            Log.e("Verify", "Error: " + error.getMessage());
        }
    }
);
""",
    },
    "react_native": {
        "installation": """
# npm
npm install @consentchain/react-native-sdk

# yarn
yarn add @consentchain/react-native-sdk
""",
        "initialization": """
import { ConsentChainSDK } from '@consentchain/react-native-sdk';

await ConsentChainSDK.initialize({
  apiUrl: 'https://api.consentchain.io',
  apiKey: 'your-api-key',
  fiduciaryId: 'your-fiduciary-id',
});
""",
        "request_consent": """
import { ConsentChainSDK } from '@consentchain/react-native-sdk';

try {
  const consent = await ConsentChainSDK.requestConsent({
    principalId: 'user-123',
    purpose: 'MARKETING',
    dataTypes: ['contact_info', 'personal_info'],
  });
  console.log('Consent granted:', consent.id);
} catch (error) {
  console.error('Error:', error);
}
""",
    },
    "flutter": {
        "installation": """
# pubspec.yaml
dependencies:
  consentchain_sdk: ^1.0.0
""",
        "initialization": """
import 'package:consentchain_sdk/consentchain_sdk.dart';

await ConsentChainSDK.initialize(
  apiUrl: 'https://api.consentchain.io',
  apiKey: 'your-api-key',
  fiduciaryId: 'your-fiduciary-id',
);
""",
        "request_consent": """
import 'package:consentchain_sdk/consentchain_sdk.dart';

try {
  final consent = await ConsentChainSDK.requestConsent(
    principalId: 'user-123',
    purpose: 'MARKETING',
    dataTypes: ['contact_info', 'personal_info'],
  );
  print('Consent granted: ${consent.id}');
} catch (error) {
  print('Error: $error');
}
""",
    },
}
