"""
S&P Global Ratings Structured Finance Waterfall Streamlit Workbench
Project Codename: Waterfall-Net
Author: Bhupesh Chandra Dimri
"""

import streamlit as st
import pandas as pd
from src.core_engine import DebtTranche, StructuredFinanceWaterfallEngine

st.set_page_config(page_title="S&P Structured Finance Waterfall Workbench", layout="wide")
st.title("S&P Global Ratings — Structured Finance Cash-Flow Waterfall Engine")
st.markdown("**Collateral Surveillance, Tranche Subordination & Priority of Payments Simulator (Waterfall-Net)**")

t_a = DebtTranche("Class A Notes", 75000000.0, 75000000.0, 0.0525, "AAA")
t_b = DebtTranche("Class B Notes", 12000000.0, 12000000.0, 0.0680, "AA")
t_c = DebtTranche("Class C Notes", 8000000.0, 8000000.0, 0.0890, "BBB")
t_eq = DebtTranche("Equity Residual", 5000000.0, 5000000.0, 0.0, "EQUITY")

engine = StructuredFinanceWaterfallEngine([t_a, t_b, t_c, t_eq], senior_fee_rate=0.005, senior_oc_trigger=1.18)

col1, col2, col3 = st.columns(3)
col1.metric("Original Deal Size", "$100,000,000")
col2.metric("Senior Subordination", "25.0%")
col3.metric("Senior OC Trigger", "1.18x")

st.subheader("Monthly Waterfall Simulation Parameters")
c1, c2, c3 = st.columns(3)
with c1:
    collateral = st.number_input("Performing Collateral ($)", value=98000000.0, step=1000000.0)
with c2:
    principal_in = st.number_input("Principal Collected ($)", value=2500000.0, step=250000.0)
with c3:
    losses_in = st.number_input("Net Credit Losses ($)", value=500000.0, step=100000.0)

if st.button("Execute Monthly Cash-Flow Waterfall"):
    res = engine.run_monthly_waterfall(
        collateral_balance=collateral,
        gross_interest_collected=750000.0,
        principal_collected=principal_in,
        net_credit_losses=losses_in
    )
    st.write(f"**Senior OC Ratio:** {res['senior_oc_ratio']:.4f} (Trigger: {'TRIPPED' if res['oc_tripped'] else 'PASSED'})")
    st.write(f"• Servicing Fee: ${res['servicing_fee']:,.2f} | Equity Distribution: ${res['equity_distribution']:,.2f}")
    st.dataframe(pd.DataFrame(res["tranche_status"]), use_container_width=True)
