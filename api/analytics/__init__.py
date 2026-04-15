from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    CONSENT_TOTAL = "consent_total"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    CONSENT_EXPIRED = "consent_expired"
    CONSENT_EXPIRING = "consent_expiring"
    CONSENT_BY_PURPOSE = "consent_by_purpose"
    CONSENT_BY_DATA_TYPE = "consent_by_data_type"
    DATA_ACCESS = "data_access"
    DELETION_REQUESTS = "deletion_requests"
    BREACH_INCIDENTS = "breach_incidents"
    COMPLIANCE_SCORE = "compliance_score"


@dataclass
class TimeSeriesPoint:
    timestamp: datetime
    value: float


@dataclass
class AnalyticsMetric:
    metric_type: MetricType
    current_value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"
    time_series: List[TimeSeriesPoint] = field(default_factory=list)


@dataclass
class ConsentTrend:
    period: str
    total_consents: int
    granted: int
    revoked: int
    expired: int
    grant_rate: float
    revoke_rate: float
    net_change: int


@dataclass
class ExpiryPrediction:
    consent_id: str
    principal_id: str
    purpose: str
    expires_at: datetime
    days_remaining: int
    renewal_probability: float
    suggested_action: str


@dataclass
class DashboardData:
    metrics: Dict[str, AnalyticsMetric]
    trends: List[ConsentTrend]
    expiring_consents: List[ExpiryPrediction]
    alerts: List[Dict[str, Any]]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyticsEngine:
    def __init__(self):
        self._metrics_cache: Dict[str, AnalyticsMetric] = {}

    def calculate_consent_metrics(
        self,
        consents: List[Dict[str, Any]],
        period_days: int = 30,
    ) -> Dict[str, AnalyticsMetric]:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)
        prev_period_start = period_start - timedelta(days=period_days)

        current_period = [c for c in consents if self._in_period(c, period_start, now)]
        prev_period = [c for c in consents if self._in_period(c, prev_period_start, period_start)]

        metrics: Dict[str, AnalyticsMetric] = {}

        total_current = len(current_period)
        total_prev = len(prev_period)
        metrics["total_consents"] = AnalyticsMetric(
            metric_type=MetricType.CONSENT_TOTAL,
            current_value=total_current,
            previous_value=total_prev if total_prev > 0 else None,
            change_percent=self._calc_change_pct(total_current, total_prev),
            trend=self._determine_trend(total_current, total_prev),
        )

        granted_current = len([c for c in current_period if c.get("status") == "GRANTED"])
        granted_prev = len([c for c in prev_period if c.get("status") == "GRANTED"])
        metrics["granted_consents"] = AnalyticsMetric(
            metric_type=MetricType.CONSENT_GRANTED,
            current_value=granted_current,
            previous_value=granted_prev if granted_prev > 0 else None,
            change_percent=self._calc_change_pct(granted_current, granted_prev),
            trend=self._determine_trend(granted_current, granted_prev),
        )

        revoked_current = len([c for c in current_period if c.get("status") == "REVOKED"])
        revoked_prev = len([c for c in prev_period if c.get("status") == "REVOKED"])
        metrics["revoked_consents"] = AnalyticsMetric(
            metric_type=MetricType.CONSENT_REVOKED,
            current_value=revoked_current,
            previous_value=revoked_prev if revoked_prev > 0 else None,
            change_percent=self._calc_change_pct(revoked_current, revoked_prev),
            trend=self._determine_trend(revoked_current, revoked_prev),
        )

        expired_current = len([c for c in current_period if c.get("status") == "EXPIRED"])
        metrics["expired_consents"] = AnalyticsMetric(
            metric_type=MetricType.CONSENT_EXPIRED,
            current_value=expired_current,
        )

        return metrics

    def calculate_purpose_distribution(
        self,
        consents: List[Dict[str, Any]],
    ) -> AnalyticsMetric:
        distribution: Dict[str, int] = defaultdict(int)
        for consent in consents:
            purpose = consent.get("purpose", "UNKNOWN")
            distribution[purpose] += 1

        total = len(consents)
        time_series = [
            TimeSeriesPoint(
                timestamp=datetime.now(timezone.utc), value=count / total * 100 if total > 0 else 0
            )
            for purpose, count in distribution.items()
        ]

        return AnalyticsMetric(
            metric_type=MetricType.CONSENT_BY_PURPOSE,
            current_value=total,
            time_series=time_series,
        )

    def calculate_data_type_distribution(
        self,
        consents: List[Dict[str, Any]],
    ) -> AnalyticsMetric:
        distribution: Dict[str, int] = defaultdict(int)
        for consent in consents:
            data_types = consent.get("data_types", [])
            for dt in data_types:
                distribution[dt] += 1

        total = sum(distribution.values())
        time_series = [
            TimeSeriesPoint(
                timestamp=datetime.now(timezone.utc), value=count / total * 100 if total > 0 else 0
            )
            for dt, count in distribution.items()
        ]

        return AnalyticsMetric(
            metric_type=MetricType.CONSENT_BY_DATA_TYPE,
            current_value=total,
            time_series=time_series,
        )

    def predict_expiring_consents(
        self,
        consents: List[Dict[str, Any]],
        days_ahead: int = 30,
    ) -> List[ExpiryPrediction]:
        now = datetime.now(timezone.utc)
        expiry_threshold = now + timedelta(days=days_ahead)

        predictions: List[ExpiryPrediction] = []

        for consent in consents:
            if consent.get("status") != "GRANTED":
                continue

            expires_at = consent.get("expires_at")
            if not expires_at:
                continue

            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

            if expires_at <= expiry_threshold and expires_at > now:
                days_remaining = (expires_at - now).days
                renewal_prob = self._predict_renewal_probability(consent, days_remaining)

                action = self._suggest_expiry_action(days_remaining, renewal_prob)

                predictions.append(
                    ExpiryPrediction(
                        consent_id=consent.get("consent_id", ""),
                        principal_id=consent.get("principal_id", ""),
                        purpose=consent.get("purpose", ""),
                        expires_at=expires_at,
                        days_remaining=days_remaining,
                        renewal_probability=renewal_prob,
                        suggested_action=action,
                    )
                )

        return sorted(predictions, key=lambda x: x.days_remaining)

    def _predict_renewal_probability(
        self,
        consent: Dict[str, Any],
        days_remaining: int,
    ) -> float:
        base_prob = 0.5

        purpose = consent.get("purpose", "")
        if purpose in ["SERVICE_DELIVERY", "PAYMENT_PROCESSING"]:
            base_prob += 0.2
        elif purpose == "MARKETING":
            base_prob -= 0.1

        if days_remaining <= 7:
            base_prob -= 0.1
        elif days_remaining >= 20:
            base_prob += 0.1

        history = consent.get("renewal_history", [])
        if history:
            renewals = sum(1 for h in history if h.get("renewed"))
            base_prob = (base_prob + renewals / len(history)) / 2

        return max(0.0, min(1.0, base_prob))

    def _suggest_expiry_action(
        self,
        days_remaining: int,
        renewal_prob: float,
    ) -> str:
        if days_remaining <= 7:
            if renewal_prob > 0.7:
                return "Send renewal reminder immediately"
            else:
                return "Send final notice and prepare for expiry"
        elif days_remaining <= 14:
            return "Send renewal reminder with incentive"
        elif days_remaining <= 21:
            return "Send gentle renewal reminder"
        else:
            return "Monitor for now"

    def calculate_trends(
        self,
        consents: List[Dict[str, Any]],
        periods: int = 6,
        period_days: int = 30,
    ) -> List[ConsentTrend]:
        trends: List[ConsentTrend] = []
        now = datetime.now(timezone.utc)

        for i in range(periods):
            period_end = now - timedelta(days=i * period_days)
            period_start = period_end - timedelta(days=period_days)

            period_consents = [c for c in consents if self._in_period(c, period_start, period_end)]

            granted = len([c for c in period_consents if c.get("status") == "GRANTED"])
            revoked = len([c for c in period_consents if c.get("status") == "REVOKED"])
            expired = len([c for c in period_consents if c.get("status") == "EXPIRED"])
            total = len(period_consents)

            grant_rate = (granted / total * 100) if total > 0 else 0
            revoke_rate = (revoked / total * 100) if total > 0 else 0
            net_change = granted - revoked - expired

            trends.append(
                ConsentTrend(
                    period=f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}",
                    total_consents=total,
                    granted=granted,
                    revoked=revoked,
                    expired=expired,
                    grant_rate=grant_rate,
                    revoke_rate=revoke_rate,
                    net_change=net_change,
                )
            )

        return list(reversed(trends))

    def generate_dashboard(
        self,
        consents: List[Dict[str, Any]],
        include_predictions: bool = True,
    ) -> DashboardData:
        metrics = self.calculate_consent_metrics(consents)
        metrics["by_purpose"] = self.calculate_purpose_distribution(consents)
        metrics["by_data_type"] = self.calculate_data_type_distribution(consents)

        trends = self.calculate_trends(consents)

        expiring: List[ExpiryPrediction] = []
        if include_predictions:
            expiring = self.predict_expiring_consents(consents)

        alerts = self._generate_alerts(metrics, expiring)

        return DashboardData(
            metrics=metrics,
            trends=trends,
            expiring_consents=expiring,
            alerts=alerts,
        )

    def _generate_alerts(
        self,
        metrics: Dict[str, AnalyticsMetric],
        expiring: List[ExpiryPrediction],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        revoked_metric = metrics.get("revoked_consents")
        if revoked_metric and revoked_metric.change_percent:
            if revoked_metric.change_percent > 20:
                alerts.append(
                    {
                        "type": "warning",
                        "title": "High Revocation Rate",
                        "message": f"Consent revocations increased by {revoked_metric.change_percent:.1f}%",
                        "action": "Review consent terms and user experience",
                    }
                )

        expiring_soon = [e for e in expiring if e.days_remaining <= 7]
        if expiring_soon:
            alerts.append(
                {
                    "type": "info",
                    "title": "Expiring Consents",
                    "message": f"{len(expiring_soon)} consents expiring within 7 days",
                    "action": "Send renewal reminders",
                }
            )

        low_renewal = [e for e in expiring if e.renewal_probability < 0.3]
        if low_renewal:
            alerts.append(
                {
                    "type": "warning",
                    "title": "Low Renewal Probability",
                    "message": f"{len(low_renewal)} consents have low renewal probability",
                    "action": "Engage users to understand concerns",
                }
            )

        return alerts

    def _in_period(
        self,
        consent: Dict[str, Any],
        start: datetime,
        end: datetime,
    ) -> bool:
        created_at = consent.get("created_at") or consent.get("granted_at")
        if not created_at:
            return False

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return start <= created_at <= end

    def _calc_change_pct(self, current: float, previous: float) -> Optional[float]:
        if previous == 0:
            return None
        return ((current - previous) / previous) * 100

    def _determine_trend(self, current: float, previous: float) -> str:
        if previous == 0:
            return "up" if current > 0 else "stable"
        change = ((current - previous) / previous) * 100
        if change > 5:
            return "up"
        elif change < -5:
            return "down"
        return "stable"


analytics_engine = AnalyticsEngine()
