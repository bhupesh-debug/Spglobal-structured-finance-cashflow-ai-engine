"""Unit tests for S&P Global Ratings Structured Finance Waterfall Engine."""

import pytest
from src.core_engine import DebtTranche, StructuredFinanceWaterfallEngine


@pytest.fixture
def sample_deal():
    # Capital structure: $100M total
    # Class A: $70M (AAA), Class B: $15M (A), Class C: $10M (BBB), Equity: $5M
    t_a = DebtTranche("Class A", 70000000.0, 70000000.0, 0.055, "AAA")
    t_b = DebtTranche("Class B", 15000000.0, 15000000.0, 0.070, "A")
    t_c = DebtTranche("Class C", 10000000.0, 10000000.0, 0.095, "BBB")
    t_eq = DebtTranche("Equity", 5000000.0, 5000000.0, 0.0, "EQUITY")
    engine = StructuredFinanceWaterfallEngine([t_a, t_b, t_c, t_eq], senior_fee_rate=0.005, senior_oc_trigger=1.18)
    return engine


def test_oc_ratio_calculation(sample_deal):
    # Collateral: $100M vs Class A $70M = 1.4286
    oc = sample_deal.compute_oc_ratio(100000000.0, target_tranche_index=0)
    assert round(oc, 4) == 1.4286
    assert oc > sample_deal.senior_oc_trigger


def test_sequential_principal_paydown(sample_deal):
    # Normal month: $2M principal collected
    res = sample_deal.run_monthly_waterfall(
        collateral_balance=100000000.0,
        gross_interest_collected=800000.0,
        principal_collected=2000000.0,
        net_credit_losses=0.0
    )
    # Class A should receive all $2M principal
    assert sample_deal.tranches[0].current_balance == 68000000.0
    assert sample_deal.tranches[0].cumulative_principal == 2000000.0
    # Junior notes receive $0 principal in sequential pay
    assert sample_deal.tranches[1].current_balance == 15000000.0
    assert sample_deal.tranches[2].current_balance == 10000000.0


def test_bottom_up_loss_absorption(sample_deal):
    # Credit loss of $3M: should hit Equity ($5M) first
    sample_deal.run_monthly_waterfall(
        collateral_balance=100000000.0,
        gross_interest_collected=600000.0,
        principal_collected=1000000.0,
        net_credit_losses=3000000.0
    )
    equity = sample_deal.tranches[3]
    assert equity.current_balance == 2000000.0
    assert equity.cumulative_loss == 3000000.0
    # Senior tranches unaffected
    assert sample_deal.tranches[0].cumulative_loss == 0.0
    assert sample_deal.tranches[1].cumulative_loss == 0.0


def test_oc_trigger_cash_diversion(sample_deal):
    # Stressed collateral: $75M vs Class A $70M = 1.0714 (< 1.18 trigger)
    res = sample_deal.run_monthly_waterfall(
        collateral_balance=75000000.0,
        gross_interest_collected=700000.0,
        principal_collected=1000000.0,
        net_credit_losses=0.0
    )
    assert res["oc_tripped"] is True
    # Equity receives zero cash when OC trips
    assert res["equity_distribution"] == 0.0
