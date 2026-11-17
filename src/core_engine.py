"""
S&P Global Ratings Structured Finance Cash-Flow Waterfall Core Engine
Project Codename: Waterfall-Net
Author: Bhupesh Chandra Dimri
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class DebtTranche:
    name: str
    original_balance: float
    current_balance: float
    coupon_rate: float
    rating_tier: str  # 'AAA', 'AA', 'A', 'BBB', 'EQUITY'
    cumulative_loss: float = 0.0
    cumulative_interest: float = 0.0
    cumulative_principal: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.current_balance > 0.0


class StructuredFinanceWaterfallEngine:
    """Multi-tranche ABS & CLO priority-of-payments cash-flow waterfall simulator."""

    def __init__(
        self,
        tranches: List[DebtTranche],
        senior_fee_rate: float = 0.005,
        senior_oc_trigger: float = 1.18,
        mezzanine_oc_trigger: float = 1.08
    ):
        self.tranches = tranches
        self.senior_fee_rate = senior_fee_rate
        self.senior_oc_trigger = senior_oc_trigger
        self.mezzanine_oc_trigger = mezzanine_oc_trigger

    def compute_oc_ratio(self, collateral_balance: float, target_tranche_index: int = 0) -> float:
        """Computes Overcollateralization Ratio for tranches up to target_tranche_index."""
        debt_pool = sum(t.current_balance for t in self.tranches[: target_tranche_index + 1])
        if debt_pool <= 0:
            return 999.0
        return collateral_balance / debt_pool

    def run_monthly_waterfall(
        self,
        collateral_balance: float,
        gross_interest_collected: float,
        principal_collected: float,
        net_credit_losses: float
    ) -> Dict[str, any]:
        """Executes a single monthly payment waterfall cycle."""
        # 1. Deduct Senior Administrative & Servicing Fees
        servicing_fee = collateral_balance * (self.senior_fee_rate / 12.0)
        available_interest = max(0.0, gross_interest_collected - servicing_fee)

        # 2. Check Overcollateralization (OC) Trigger
        senior_oc = self.compute_oc_ratio(collateral_balance, target_tranche_index=0)
        oc_tripped = senior_oc < self.senior_oc_trigger

        # 3. Pay Tranche Interest Sequentially (Class A -> B -> C)
        for t in self.tranches:
            if t.rating_tier == "EQUITY":
                continue
            interest_due = t.current_balance * (t.coupon_rate / 12.0)
            interest_paid = min(available_interest, interest_due)
            t.cumulative_interest += interest_paid
            available_interest -= interest_paid

        # 4. Allocate Available Principal (Sequential Paydown)
        available_principal = principal_collected
        if oc_tripped:
            # Divert remaining excess interest to accelerate senior principal paydown
            available_principal += available_interest
            available_interest = 0.0

        for t in self.tranches:
            if t.rating_tier == "EQUITY":
                continue
            if available_principal <= 0:
                break
            paydown = min(available_principal, t.current_balance)
            t.current_balance -= paydown
            t.cumulative_principal += paydown
            available_principal -= paydown

        # 5. Allocate Residual Interest to Equity (if OC not tripped)
        equity_distribution = 0.0
        if not oc_tripped:
            equity_distribution = available_interest
            equity_tranche = next((t for t in self.tranches if t.rating_tier == "EQUITY"), None)
            if equity_tranche:
                equity_tranche.cumulative_interest += equity_distribution

        # 6. Allocate Net Credit Losses (Bottom-Up: Equity -> Class C -> Class B -> Class A)
        unabsorbed_loss = net_credit_losses
        for t in reversed(self.tranches):
            if unabsorbed_loss <= 0:
                break
            loss_applied = min(unabsorbed_loss, t.current_balance)
            t.current_balance -= loss_applied
            t.cumulative_loss += loss_applied
            unabsorbed_loss -= loss_applied

        post_collateral = max(0.0, collateral_balance - principal_collected - net_credit_losses)

        return {
            "servicing_fee": round(servicing_fee, 2),
            "senior_oc_ratio": round(senior_oc, 4),
            "oc_tripped": oc_tripped,
            "post_collateral_balance": round(post_collateral, 2),
            "equity_distribution": round(equity_distribution, 2),
            "unabsorbed_loss": round(unabsorbed_loss, 2),
            "tranche_status": [
                {
                    "name": t.name,
                    "tier": t.rating_tier,
                    "remaining_balance": round(t.current_balance, 2),
                    "principal_paid": round(t.cumulative_principal, 2),
                    "interest_paid": round(t.cumulative_interest, 2),
                    "allocated_loss": round(t.cumulative_loss, 2)
                }
                for t in self.tranches
            ]
        }
