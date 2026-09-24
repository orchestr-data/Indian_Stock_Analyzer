"""Tests for banking, NBFC, and insurance sector calculations."""

import pytest
from src.calculations.banking import (
    net_interest_margin,
    gnpa_ratio,
    nnpa_ratio,
    provision_coverage_ratio,
    casa_ratio,
    credit_cost,
    cost_to_income_ratio,
)
from src.calculations.nbfc import aum_growth, spread
from src.calculations.insurance import vnb_margin, combined_ratio, solvency_ratio_check


# ===========================================================================
# Banking — Net Interest Margin
# ===========================================================================

class TestNetInterestMargin:
    def test_basic(self):
        r = net_interest_margin(5000, 100000)
        assert r.value == pytest.approx(5.0)

    def test_zero_assets(self):
        r = net_interest_margin(5000, 0)
        assert r.value is None

    def test_none_nii(self):
        r = net_interest_margin(None, 100000)
        assert r.value is None

    def test_none_assets(self):
        r = net_interest_margin(5000, None)
        assert r.value is None

    def test_rounding(self):
        r = net_interest_margin(3333, 100000)
        assert r.value == pytest.approx(3.33, rel=0.01)

    def test_label(self):
        r = net_interest_margin(4000, 80000)
        assert r.label == "NIM"
        assert r.unit == "%"


# ===========================================================================
# Banking — GNPA ratio
# ===========================================================================

class TestGnpaRatio:
    def test_basic(self):
        r = gnpa_ratio(gross_npa=1200, gross_advances=100000)
        assert r.value == pytest.approx(1.2)

    def test_zero_advances(self):
        r = gnpa_ratio(gross_npa=1200, gross_advances=0)
        assert r.value is None

    def test_zero_npa(self):
        r = gnpa_ratio(gross_npa=0, gross_advances=100000)
        assert r.value == pytest.approx(0.0)

    def test_none_npa(self):
        r = gnpa_ratio(gross_npa=None, gross_advances=100000)
        assert r.value is None

    def test_none_advances(self):
        r = gnpa_ratio(gross_npa=1200, gross_advances=None)
        assert r.value is None

    def test_high_npa_note(self):
        r = gnpa_ratio(gross_npa=8000, gross_advances=100000)
        assert r.value == pytest.approx(8.0)
        assert r.note is not None  # should flag high NPA


# ===========================================================================
# Banking — NNPA ratio
# ===========================================================================

class TestNnpaRatio:
    def test_basic(self):
        r = nnpa_ratio(net_npa=400, net_advances=100000)
        assert r.value == pytest.approx(0.4)

    def test_zero_advances(self):
        r = nnpa_ratio(net_npa=400, net_advances=0)
        assert r.value is None

    def test_nnpa_less_than_gnpa_typical(self):
        gnpa = gnpa_ratio(1200, 100000)
        nnpa = nnpa_ratio(400, 100000)
        assert nnpa.value is not None
        assert gnpa.value is not None
        assert nnpa.value < gnpa.value


# ===========================================================================
# Banking — Provision Coverage Ratio
# ===========================================================================

class TestProvisionCoverageRatio:
    def test_basic(self):
        r = provision_coverage_ratio(provisions=900, gross_npa=1200)
        assert r.value == pytest.approx(75.0)

    def test_full_coverage(self):
        r = provision_coverage_ratio(provisions=1200, gross_npa=1200)
        assert r.value == pytest.approx(100.0)

    def test_zero_npa(self):
        r = provision_coverage_ratio(provisions=900, gross_npa=0)
        assert r.value is None

    def test_none_provisions(self):
        r = provision_coverage_ratio(provisions=None, gross_npa=1200)
        assert r.value is None

    def test_low_coverage_note(self):
        # Below 60% PCR should produce a note
        r = provision_coverage_ratio(provisions=600, gross_npa=1200)
        assert r.value == pytest.approx(50.0)
        assert r.note is not None


# ===========================================================================
# Banking — CASA Ratio
# ===========================================================================

class TestCasaRatio:
    def test_basic(self):
        r = casa_ratio(casa_deposits=45000, total_deposits=100000)
        assert r.value == pytest.approx(45.0)

    def test_zero_deposits(self):
        r = casa_ratio(casa_deposits=45000, total_deposits=0)
        assert r.value is None

    def test_none_casa(self):
        r = casa_ratio(casa_deposits=None, total_deposits=100000)
        assert r.value is None

    def test_high_casa(self):
        r = casa_ratio(casa_deposits=70000, total_deposits=100000)
        assert r.value == pytest.approx(70.0)
        assert r.label == "CASA Ratio"

    def test_full_casa(self):
        r = casa_ratio(casa_deposits=100000, total_deposits=100000)
        assert r.value == pytest.approx(100.0)


# ===========================================================================
# Banking — Credit Cost
# ===========================================================================

class TestCreditCost:
    def test_basic(self):
        r = credit_cost(provisions=600, avg_advances=100000)
        assert r.value == pytest.approx(0.6)

    def test_zero_advances(self):
        r = credit_cost(provisions=600, avg_advances=0)
        assert r.value is None

    def test_none_provisions(self):
        r = credit_cost(provisions=None, avg_advances=100000)
        assert r.value is None

    def test_low_credit_cost(self):
        r = credit_cost(provisions=100, avg_advances=100000)
        assert r.value == pytest.approx(0.1)


# ===========================================================================
# Banking — Cost to Income
# ===========================================================================

class TestCostToIncomeRatio:
    def test_basic(self):
        r = cost_to_income_ratio(operating_expenses=4000, net_income=10000)
        assert r.value == pytest.approx(40.0)

    def test_zero_income(self):
        r = cost_to_income_ratio(operating_expenses=4000, net_income=0)
        assert r.value is None

    def test_none_expenses(self):
        r = cost_to_income_ratio(operating_expenses=None, net_income=10000)
        assert r.value is None

    def test_high_ci_note(self):
        # Above 60% C/I should produce a note
        r = cost_to_income_ratio(operating_expenses=7000, net_income=10000)
        assert r.value == pytest.approx(70.0)
        assert r.note is not None

    def test_label(self):
        r = cost_to_income_ratio(operating_expenses=4000, net_income=10000)
        assert r.label == "Cost-to-Income"
        assert r.unit == "%"


# ===========================================================================
# NBFC — AUM Growth
# ===========================================================================

class TestAumGrowth:
    def test_basic(self):
        r = aum_growth(aum_current=12000, aum_previous=10000)
        assert r.value == pytest.approx(20.0)

    def test_zero_previous(self):
        r = aum_growth(aum_current=12000, aum_previous=0)
        assert r.value is None

    def test_none_aum(self):
        r = aum_growth(aum_current=None, aum_previous=10000)
        assert r.value is None

    def test_decline(self):
        r = aum_growth(aum_current=9000, aum_previous=10000)
        assert r.value == pytest.approx(-10.0)

    def test_label(self):
        r = aum_growth(aum_current=12000, aum_previous=10000)
        assert r.label == "AUM Growth"


# ===========================================================================
# NBFC — Spread
# ===========================================================================

class TestSpread:
    def test_basic(self):
        r = spread(yield_on_advances=12.5, cost_of_borrowings=8.0)
        assert r.value == pytest.approx(4.5)

    def test_negative_spread(self):
        r = spread(yield_on_advances=7.0, cost_of_borrowings=8.0)
        assert r.value == pytest.approx(-1.0)

    def test_none_yield(self):
        r = spread(yield_on_advances=None, cost_of_borrowings=8.0)
        assert r.value is None

    def test_zero_spread(self):
        r = spread(yield_on_advances=8.0, cost_of_borrowings=8.0)
        assert r.value == pytest.approx(0.0)


# ===========================================================================
# Insurance — VNB Margin
# ===========================================================================

class TestVnbMargin:
    def test_basic(self):
        r = vnb_margin(vnb=2000, ape=10000)
        assert r.value == pytest.approx(20.0)

    def test_zero_ape(self):
        r = vnb_margin(vnb=2000, ape=0)
        assert r.value is None

    def test_none_vnb(self):
        r = vnb_margin(vnb=None, ape=10000)
        assert r.value is None

    def test_high_margin(self):
        r = vnb_margin(vnb=3000, ape=10000)
        assert r.value == pytest.approx(30.0)

    def test_label(self):
        r = vnb_margin(vnb=2000, ape=10000)
        assert r.label == "VNB Margin"
        assert r.unit == "%"


# ===========================================================================
# Insurance — Combined Ratio
# ===========================================================================

class TestCombinedRatio:
    def test_basic(self):
        r = combined_ratio(claims_ratio=65.0, expense_ratio=25.0)
        assert r.value == pytest.approx(90.0)

    def test_underwriting_loss(self):
        r = combined_ratio(claims_ratio=75.0, expense_ratio=30.0)
        assert r.value == pytest.approx(105.0)
        assert r.note is not None  # above 100% should have a note

    def test_breakeven(self):
        r = combined_ratio(claims_ratio=70.0, expense_ratio=30.0)
        assert r.value == pytest.approx(100.0)

    def test_none_claims(self):
        r = combined_ratio(claims_ratio=None, expense_ratio=25.0)
        assert r.value is None

    def test_none_expense(self):
        r = combined_ratio(claims_ratio=65.0, expense_ratio=None)
        assert r.value is None

    def test_label(self):
        r = combined_ratio(claims_ratio=65.0, expense_ratio=25.0)
        assert r.label == "Combined Ratio"
        assert r.unit == "%"


# ===========================================================================
# Insurance — Solvency Ratio
# ===========================================================================

class TestSolvencyRatioCheck:
    def test_adequate(self):
        r = solvency_ratio_check(solvency_ratio=200.0)
        assert r.value == pytest.approx(200.0)
        assert r.note is None

    def test_below_minimum(self):
        r = solvency_ratio_check(solvency_ratio=140.0)
        assert r.value == pytest.approx(140.0)
        assert r.note is not None
        assert "150" in r.note

    def test_at_minimum(self):
        r = solvency_ratio_check(solvency_ratio=150.0)
        assert r.value == pytest.approx(150.0)
        assert r.note is None

    def test_none_ratio(self):
        r = solvency_ratio_check(solvency_ratio=None)
        assert r.value is None

    def test_label(self):
        r = solvency_ratio_check(solvency_ratio=180.0)
        assert r.label == "Solvency Ratio"
        assert r.unit == "%"
