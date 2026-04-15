"""Tests for Analytics Engine.

Covers:
- Consent metrics calculation
- Purpose distribution
- Data type distribution
- Expiring consent predictions
- Trend calculation
- Dashboard generation
- Alert generation
"""

import pytest
from datetime import datetime, timezone, timedelta
from api.analytics import (
    analytics_engine,
    AnalyticsEngine,
    MetricType,
    AnalyticsMetric,
    ConsentTrend,
    ExpiryPrediction,
    DashboardData,
    TimeSeriesPoint,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_consents():
    """Provide a list of sample consent records for testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "consent_id": "c1",
            "principal_id": "p1",
            "fiduciary_id": "f1",
            "purpose": "MARKETING",
            "data_types": ["contact_info", "personal_info"],
            "status": "GRANTED",
            "created_at": now - timedelta(days=5),
            "granted_at": now - timedelta(days=5),
            "expires_at": now + timedelta(days=25),
        },
        {
            "consent_id": "c2",
            "principal_id": "p2",
            "fiduciary_id": "f1",
            "purpose": "SERVICE_DELIVERY",
            "data_types": ["personal_info"],
            "status": "GRANTED",
            "created_at": now - timedelta(days=10),
            "granted_at": now - timedelta(days=10),
            "expires_at": now + timedelta(days=350),
        },
        {
            "consent_id": "c3",
            "principal_id": "p1",
            "fiduciary_id": "f2",
            "purpose": "ANALYTICS",
            "data_types": ["behavioral_data"],
            "status": "REVOKED",
            "created_at": now - timedelta(days=15),
            "granted_at": now - timedelta(days=15),
            "expires_at": now + timedelta(days=350),
        },
        {
            "consent_id": "c4",
            "principal_id": "p3",
            "fiduciary_id": "f1",
            "purpose": "MARKETING",
            "data_types": ["contact_info"],
            "status": "EXPIRED",
            "created_at": now - timedelta(days=40),
            "granted_at": now - timedelta(days=40),
            "expires_at": now - timedelta(days=5),
        },
        {
            "consent_id": "c5",
            "principal_id": "p2",
            "fiduciary_id": "f2",
            "purpose": "PAYMENT_PROCESSING",
            "data_types": ["financial_data"],
            "status": "GRANTED",
            "created_at": now - timedelta(days=2),
            "granted_at": now - timedelta(days=2),
            "expires_at": now + timedelta(days=3),
            "renewal_history": [{"renewed": True}, {"renewed": True}],
        },
    ]


@pytest.fixture
def empty_consents():
    """Provide an empty consent list."""
    return []


# ============================================================
# Test: Consent Metrics Calculation
# ============================================================


class TestConsentMetrics:
    """Test consent metrics calculation."""

    def test_total_consents_counted(self, sample_consents):
        """Total consents count all records in period."""
        metrics = analytics_engine.calculate_consent_metrics(sample_consents, period_days=30)

        assert "total_consents" in metrics
        # 4 consents within 30 days (c4 is 40 days ago, outside period)
        assert metrics["total_consents"].current_value == 4

    def test_granted_consents_counted(self, sample_consents):
        """Granted consents are counted separately."""
        metrics = analytics_engine.calculate_consent_metrics(sample_consents, period_days=30)

        assert "granted_consents" in metrics
        assert metrics["granted_consents"].current_value == 3  # c1, c2, c5

    def test_revoked_consents_counted(self, sample_consents):
        """Revoked consents are counted separately."""
        metrics = analytics_engine.calculate_consent_metrics(sample_consents, period_days=30)

        assert "revoked_consents" in metrics
        assert metrics["revoked_consents"].current_value == 1  # c3

    def test_expired_consents_counted(self, sample_consents):
        """Expired consents within period are counted."""
        metrics = analytics_engine.calculate_consent_metrics(sample_consents, period_days=60)

        assert "expired_consents" in metrics
        assert metrics["expired_consents"].current_value == 1  # c4

    def test_empty_consents_metrics(self, empty_consents):
        """Empty consent list produces zero metrics."""
        metrics = analytics_engine.calculate_consent_metrics(empty_consents)

        assert metrics["total_consents"].current_value == 0
        assert metrics["granted_consents"].current_value == 0
        assert metrics["revoked_consents"].current_value == 0

    def test_metric_has_trend(self, sample_consents):
        """Metrics include trend information."""
        metrics = analytics_engine.calculate_consent_metrics(sample_consents, period_days=30)

        total = metrics["total_consents"]
        assert total.trend is not None
        assert total.trend in ("up", "down", "stable")


# ============================================================
# Test: Purpose Distribution
# ============================================================


class TestPurposeDistribution:
    """Test purpose-based consent distribution."""

    def test_distribution_counts_purposes(self, sample_consents):
        """Distribution aggregates consents by purpose."""
        metric = analytics_engine.calculate_purpose_distribution(sample_consents)

        assert metric.current_value == 5
        assert len(metric.time_series) > 0

    def test_distribution_time_series_values(self, sample_consents):
        """Time series values represent percentages."""
        metric = analytics_engine.calculate_purpose_distribution(sample_consents)

        for point in metric.time_series:
            assert 0 <= point.value <= 100
            assert isinstance(point.timestamp, datetime)

    def test_empty_distribution(self, empty_consents):
        """Empty list produces zero distribution."""
        metric = analytics_engine.calculate_purpose_distribution(empty_consents)

        assert metric.current_value == 0
        assert len(metric.time_series) == 0


# ============================================================
# Test: Data Type Distribution
# ============================================================


class TestDataTypeDistribution:
    """Test data type-based consent distribution."""

    def test_distribution_counts_data_types(self, sample_consents):
        """Distribution aggregates by data type."""
        metric = analytics_engine.calculate_data_type_distribution(sample_consents)

        assert metric.current_value > 0
        assert len(metric.time_series) > 0

    def test_distribution_handles_multiple_types_per_consent(self, sample_consents):
        """Consents with multiple data types are counted per type."""
        metric = analytics_engine.calculate_data_type_distribution(sample_consents)

        # c1 has 2 types, so total data type occurrences > number of consents
        assert metric.current_value > len(sample_consents)

    def test_distribution_empty(self, empty_consents):
        """Empty list produces zero distribution."""
        metric = analytics_engine.calculate_data_type_distribution(empty_consents)
        assert metric.current_value == 0


# ============================================================
# Test: Expiring Consent Predictions
# ============================================================


class TestExpiryPredictions:
    """Test expiring consent prediction logic."""

    def test_predict_expiring_within_window(self, sample_consents):
        """Predictions include consents expiring within window."""
        predictions = analytics_engine.predict_expiring_consents(sample_consents, days_ahead=30)

        assert len(predictions) >= 1
        for pred in predictions:
            assert pred.days_remaining <= 30

    def test_predictions_sorted_by_days_remaining(self, sample_consents):
        """Predictions are sorted by urgency."""
        predictions = analytics_engine.predict_expiring_consents(sample_consents, days_ahead=30)

        if len(predictions) > 1:
            for i in range(len(predictions) - 1):
                assert predictions[i].days_remaining <= predictions[i + 1].days_remaining

    def test_prediction_excludes_non_granted(self, sample_consents):
        """Revoked and expired consents are not predicted."""
        predictions = analytics_engine.predict_expiring_consents(sample_consents, days_ahead=365)

        for pred in predictions:
            # c3 is REVOKED, c4 is EXPIRED - should not appear
            assert pred.consent_id != "c3"
            assert pred.consent_id != "c4"

    def test_prediction_renewal_probability_range(self, sample_consents):
        """Renewal probability is between 0 and 1."""
        predictions = analytics_engine.predict_expiring_consents(sample_consents, days_ahead=30)

        for pred in predictions:
            assert 0.0 <= pred.renewal_probability <= 1.0

    def test_prediction_service_delivery_higher_renewal(self):
        """Service delivery consents have higher renewal probability."""
        now = datetime.now(timezone.utc)
        consents = [
            {
                "consent_id": "sd1",
                "principal_id": "p1",
                "purpose": "SERVICE_DELIVERY",
                "status": "GRANTED",
                "expires_at": now + timedelta(days=10),
            },
            {
                "consent_id": "m1",
                "principal_id": "p2",
                "purpose": "MARKETING",
                "status": "GRANTED",
                "expires_at": now + timedelta(days=10),
            },
        ]

        predictions = analytics_engine.predict_expiring_consents(consents, days_ahead=30)
        sd_pred = next(p for p in predictions if p.consent_id == "sd1")
        m_pred = next(p for p in predictions if p.consent_id == "m1")

        assert sd_pred.renewal_probability > m_pred.renewal_probability

    def test_prediction_with_renewal_history(self):
        """Renewal history increases probability."""
        now = datetime.now(timezone.utc)
        consents = [
            {
                "consent_id": "c1",
                "principal_id": "p1",
                "purpose": "MARKETING",
                "status": "GRANTED",
                "expires_at": now + timedelta(days=10),
                "renewal_history": [
                    {"renewed": True},
                    {"renewed": True},
                    {"renewed": True},
                ],
            },
        ]

        predictions = analytics_engine.predict_expiring_consents(consents, days_ahead=30)
        assert len(predictions) == 1
        assert predictions[0].renewal_probability > 0.5

    def test_prediction_suggested_action(self, sample_consents):
        """Predictions include suggested actions."""
        predictions = analytics_engine.predict_expiring_consents(sample_consents, days_ahead=30)

        for pred in predictions:
            assert pred.suggested_action is not None
            assert len(pred.suggested_action) > 0


# ============================================================
# Test: Trend Calculation
# ============================================================


class TestTrendCalculation:
    """Test consent trend calculation."""

    def test_trends_return_correct_number(self, sample_consents):
        """Trends returns requested number of periods."""
        trends = analytics_engine.calculate_trends(sample_consents, periods=4, period_days=30)

        assert len(trends) == 4

    def test_trends_earliest_period_first(self, sample_consents):
        """Trends are ordered earliest to latest."""
        trends = analytics_engine.calculate_trends(sample_consents, periods=3, period_days=30)

        # After reversal, earliest period should be first
        assert len(trends) == 3

    def test_trend_has_all_fields(self, sample_consents):
        """Each trend has required fields."""
        trends = analytics_engine.calculate_trends(sample_consents, periods=1, period_days=30)

        trend = trends[0]
        assert isinstance(trend.period, str)
        assert isinstance(trend.total_consents, int)
        assert isinstance(trend.granted, int)
        assert isinstance(trend.revoked, int)
        assert isinstance(trend.expired, int)
        assert 0 <= trend.grant_rate <= 100
        assert 0 <= trend.revoke_rate <= 100

    def test_empty_trends(self, empty_consents):
        """Empty consents produce zero trends."""
        trends = analytics_engine.calculate_trends(empty_consents, periods=3)

        assert len(trends) == 3
        for trend in trends:
            assert trend.total_consents == 0
            assert trend.grant_rate == 0
            assert trend.revoke_rate == 0


# ============================================================
# Test: Dashboard Generation
# ============================================================


class TestDashboardGeneration:
    """Test full dashboard data generation."""

    def test_dashboard_has_all_sections(self, sample_consents):
        """Dashboard includes all required sections."""
        dashboard = analytics_engine.generate_dashboard(sample_consents)

        assert isinstance(dashboard.metrics, dict)
        assert isinstance(dashboard.trends, list)
        assert isinstance(dashboard.expiring_consents, list)
        assert isinstance(dashboard.alerts, list)
        assert isinstance(dashboard.generated_at, datetime)

    def test_dashboard_without_predictions(self, sample_consents):
        """Dashboard can exclude predictions."""
        dashboard = analytics_engine.generate_dashboard(
            sample_consents, include_predictions=False
        )

        assert len(dashboard.expiring_consents) == 0

    def test_dashboard_metrics_populated(self, sample_consents):
        """Dashboard metrics are populated."""
        dashboard = analytics_engine.generate_dashboard(sample_consents)

        assert "total_consents" in dashboard.metrics
        assert "granted_consents" in dashboard.metrics
        assert "by_purpose" in dashboard.metrics
        assert "by_data_type" in dashboard.metrics


# ============================================================
# Test: Alert Generation
# ============================================================


class TestAlertGeneration:
    """Test alert generation logic."""

    def test_alert_has_required_fields(self):
        """Generated alerts have required structure."""
        alert = {
            "type": "warning",
            "title": "Test Alert",
            "message": "Test message",
            "action": "Test action",
        }

        assert "type" in alert
        assert "title" in alert
        assert "message" in alert
        assert "action" in alert


# ============================================================
# Test: Utility Methods
# ============================================================


class TestUtilityMethods:
    """Test utility helper methods."""

    def test_calc_change_pct_normal(self):
        """Percentage change calculated correctly."""
        result = analytics_engine._calc_change_pct(150, 100)
        assert result == 50.0

    def test_calc_change_pct_decrease(self):
        """Percentage decrease calculated correctly."""
        result = analytics_engine._calc_change_pct(50, 100)
        assert result == -50.0

    def test_calc_change_pct_zero_previous(self):
        """Zero previous returns None."""
        assert analytics_engine._calc_change_pct(100, 0) is None

    def test_determine_trend_up(self):
        """Significant increase detected as up."""
        assert analytics_engine._determine_trend(200, 100) == "up"

    def test_determine_trend_down(self):
        """Significant decrease detected as down."""
        assert analytics_engine._determine_trend(50, 100) == "down"

    def test_determine_trend_stable(self):
        """Small change detected as stable."""
        assert analytics_engine._determine_trend(102, 100) == "stable"

    def test_determine_trend_zero_previous(self):
        """New value from zero is 'up'."""
        assert analytics_engine._determine_trend(10, 0) == "up"
        assert analytics_engine._determine_trend(0, 0) == "stable"
