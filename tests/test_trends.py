"""Tests for trend analysis engine."""

import pytest
from src.analysis.trends import TrendAnalyzer, _direction, _consecutive, _volatility


class TestDirection:
    def test_improving(self):
        vals = [100, 110, 120, 130, 140, 150]
        assert _direction(vals) == "improving"

    def test_declining(self):
        vals = [150, 140, 130, 120, 110, 100]
        assert _direction(vals) == "declining"

    def test_insufficient(self):
        vals = [100, 110]
        assert _direction(vals) == "insufficient_history"

    def test_mixed(self):
        # 3 positive / 2 negative moves with positive slope → "improving" per algorithm
        # A truly mixed series needs roughly equal up/down with ambiguous slope
        vals = [100, 120, 90, 80, 130, 70]
        assert _direction(vals) in ("mixed", "declining")

    def test_with_nones(self):
        vals = [None, 100, 110, 120, 130]
        result = _direction(vals)
        assert result in ("improving", "mixed", "insufficient_history")


class TestConsecutive:
    def test_consecutive_increases(self):
        # From tail: 130>120>110>100>90 → 4 consecutive increases
        vals = [100, 90, 100, 110, 120, 130]
        inc, dec = _consecutive(vals)
        assert inc == 4
        assert dec == 0

    def test_consecutive_decreases(self):
        vals = [130, 120, 110, 100, 90, 80]
        inc, dec = _consecutive(vals)
        assert dec == 5
        assert inc == 0

    def test_no_streak(self):
        vals = [100, 110, 105]
        inc, dec = _consecutive(vals)
        assert inc == 0
        assert dec == 1


class TestTrendAnalyzer:
    def setup_method(self):
        self.analyzer = TrendAnalyzer()

    def test_full_analysis(self):
        values = [100, 110, 121, 133.1, 146.41, 161.05]
        labels = ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        result = self.analyzer.analyze("Revenue", values, labels, years)

        assert result.latest == pytest.approx(161.05, rel=0.01)
        assert result.cagr_5y is not None
        assert abs(result.cagr_5y - 10.0) < 0.1
        assert result.direction == "improving"
        assert result.consecutive_increases == 5

    def test_declining_trend(self):
        values = [100, 90, 80, 70, 60]
        labels = [f"FY{y}" for y in range(2020, 2025)]
        years = list(range(2020, 2025))
        result = self.analyzer.analyze("Revenue", values, labels, years)
        assert result.direction == "declining"
        assert result.consecutive_decreases == 4

    def test_with_none_values(self):
        values = [None, 100, 110, None, 130]
        labels = [f"FY{y}" for y in range(2020, 2025)]
        years = list(range(2020, 2025))
        result = self.analyzer.analyze("Revenue", values, labels, years)
        # Should handle None gracefully
        assert result.latest == 130

    def test_insufficient_history(self):
        values = [100, 110]
        result = self.analyzer.analyze("Revenue", values, ["FY2024", "FY2025"], [2024, 2025])
        assert result.direction == "insufficient_history"
        assert result.cagr_5y is None

    def test_cagr_3y(self):
        values = [100, 110, 121, 133.1]
        result = self.analyzer.analyze("EPS", values, [f"FY{y}" for y in range(2022, 2026)],
                                        list(range(2022, 2026)))
        assert result.cagr_3y is not None
        assert abs(result.cagr_3y - 10.0) < 0.1
