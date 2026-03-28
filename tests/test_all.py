"""
Comprehensive test suite for the analysis engine.

Tests every module with:
  - Hand-computed expected values (verified on paper)
  - Edge cases (zero values, missing columns, single rows, NaN)
  - Boundary conditions (exactly 12 months for YoY, empty DataFrames)
  - Cross-verification (bridge sums, P+V+M decomposition, CCC formula)
  - Real data from test files
"""

import math
import pandas as pd
import sys

PASS = 0
FAIL = 0
TOTAL = 0


def check(name, condition, detail=""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


def approx(a, b, tol=0.01):
    """Check two floats are approximately equal."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < tol


def approx_pct(a, b, tol=0.1):
    """Check two percentages are approximately equal."""
    return approx(a, b, tol)


# ═══════════════════════════════════════════════════════════════════════════
#  UTILS
# ═══════════════════════════════════════════════════════════════════════════

def test_utils():
    print("\n── UTILS ──")
    from analysis.utils import (
        safe_div, safe_pct, days_in_period, get_prior_year_period,
        favorability, get_value, has_column,
    )
    from analysis.types import Favorability

    # safe_div
    check("safe_div(10,5)=2", safe_div(10, 5) == 2.0)
    check("safe_div(10,0)=None", safe_div(10, 0) is None)
    check("safe_div(0,0)=None", safe_div(0, 0) is None)
    check("safe_div(10,None)=None", safe_div(10, None) is None)
    check("safe_div(None,5)", safe_div(None, 5) is None)
    check("safe_div(nan,5)=None", safe_div(float('nan'), 5) is None)
    check("safe_div(5,nan)=None", safe_div(5, float('nan')) is None)
    check("safe_div(inf,5)=None", safe_div(float('inf'), 5) is None)
    check("safe_div(5,inf)=None", safe_div(5, float('inf')) is None)
    check("safe_div(-10,5)=-2", safe_div(-10, 5) == -2.0)
    check("safe_div(10,-5)=-2", safe_div(10, -5) == -2.0)
    check("safe_div(0,5)=0", safe_div(0, 5) == 0.0)

    # safe_pct
    check("safe_pct(1,4)=25", safe_pct(1, 4) == 25.0)
    check("safe_pct(0,100)=0", safe_pct(0, 100) == 0.0)
    check("safe_pct(10,0)=None", safe_pct(10, 0) is None)

    # days_in_period
    check("days 2026-01=31", days_in_period("2026-01") == 31)
    check("days 2026-02=28", days_in_period("2026-02") == 28)
    check("days 2024-02=29 (leap)", days_in_period("2024-02") == 29)
    check("days 2026-04=30", days_in_period("2026-04") == 30)
    check("days 2026-12=31", days_in_period("2026-12") == 31)
    check("days bad=30 (fallback)", days_in_period("bad") == 30)

    # get_prior_year_period
    check("PY 2026-03=2025-03", get_prior_year_period("2026-03") == "2025-03")
    check("PY 2025-01=2024-01", get_prior_year_period("2025-01") == "2024-01")
    check("PY 2025-12=2024-12", get_prior_year_period("2025-12") == "2024-12")

    # favorability
    check("rev up=fav", favorability("revenue", 100) == Favorability.FAVORABLE)
    check("rev down=unfav", favorability("revenue", -100) == Favorability.UNFAVORABLE)
    check("cogs up=unfav", favorability("cogs", 100) == Favorability.UNFAVORABLE)
    check("cogs down=fav", favorability("cogs", -100) == Favorability.FAVORABLE)
    check("sm up=unfav", favorability("sales_marketing", 50) == Favorability.UNFAVORABLE)
    check("ebitda up=fav", favorability("ebitda", 50) == Favorability.FAVORABLE)
    check("gp down=unfav", favorability("gross_profit", -50) == Favorability.UNFAVORABLE)
    check("zero=neutral", favorability("revenue", 0) == Favorability.NEUTRAL)

    # get_value
    row = pd.Series({"a": 100, "b": float('nan'), "c": None})
    check("get_value existing", get_value(row, "a") == 100)
    check("get_value NaN→default", get_value(row, "b") == 0.0)
    check("get_value missing→default", get_value(row, "z") == 0.0)
    check("get_value NaN→custom", get_value(row, "b", default=None) is None)

    # has_column
    df = pd.DataFrame({"x": [1, 2], "y": [None, None], "z": [1, None]})
    check("has_column x=True", has_column(df, "x") == True)
    check("has_column y=False (all null)", has_column(df, "y") == False)
    check("has_column z=True (some null)", has_column(df, "z") == True)
    check("has_column missing=False", has_column(df, "missing") == False)


# ═══════════════════════════════════════════════════════════════════════════
#  MARGINS
# ═══════════════════════════════════════════════════════════════════════════

def test_margins():
    print("\n── MARGINS ──")
    from analysis.margins import compute_margins

    df = pd.DataFrame({
        'period': ['2025-01', '2025-02', '2025-03'],
        'revenue':        [1000000, 1100000, 0],  # zero revenue in last period
        'cogs':           [ 300000,  320000, 0],
        'gross_profit':   [ 700000,  780000, 0],
        'sales_marketing':[ 200000,  220000, 0],
        'rd':             [ 100000,  110000, 0],
        'ga':             [  50000,   55000, 0],
        'total_opex':     [ 350000,  385000, 0],
        'ebitda':         [ 350000,  395000, 0],
    })

    r = compute_margins(df)
    check("3 periods", len(r.periods) == 3)

    # Period 1
    p1 = r.periods[0]
    check("P1 gross_margin=70", approx_pct(p1.gross_margin_pct, 70.0))
    check("P1 ebitda_margin=35", approx_pct(p1.ebitda_margin_pct, 35.0))
    check("P1 sm_pct=20", approx_pct(p1.sm_pct_revenue, 20.0))
    check("P1 rd_pct=10", approx_pct(p1.rd_pct_revenue, 10.0))
    check("P1 ga_pct=5", approx_pct(p1.ga_pct_revenue, 5.0))
    check("P1 opex_pct=35", approx_pct(p1.opex_pct_revenue, 35.0))
    check("P1 no MoM", p1.revenue_growth_mom is None)
    check("P1 no YoY", p1.revenue_growth_yoy is None)

    # Period 2
    p2 = r.periods[1]
    check("P2 rev_growth_mom=10%", approx_pct(p2.revenue_growth_mom, 10.0))
    check("P2 ebitda_growth_mom=12.86%", approx_pct(p2.ebitda_growth_mom, 12.857, tol=0.1))

    # Period 3 (zero revenue)
    p3 = r.periods[2]
    check("P3 zero rev→None gross", p3.gross_margin_pct is None)
    check("P3 zero rev→None ebitda", p3.ebitda_margin_pct is None)
    check("P3 zero rev→None sm", p3.sm_pct_revenue is None)
    # MoM: (0 - 1100000) / 1100000 = -100%
    check("P3 rev_growth_mom=-100%", approx_pct(p3.revenue_growth_mom, -100.0))

    # Missing optional columns
    df_no_rd = df.drop(columns=["rd", "ga"])
    r2 = compute_margins(df_no_rd)
    check("No rd→None", r2.periods[0].rd_pct_revenue is None)
    check("No ga→None", r2.periods[0].ga_pct_revenue is None)

    # Empty DataFrame
    r3 = compute_margins(pd.DataFrame())
    check("Empty→0 periods", len(r3.periods) == 0)

    # Single row
    df_single = df.iloc[:1].copy()
    r4 = compute_margins(df_single)
    check("Single row→1 period", len(r4.periods) == 1)
    check("Single row→no MoM", r4.periods[0].revenue_growth_mom is None)

    # YoY: exactly 13 months
    periods = [f'2025-{m:02d}' for m in range(1, 13)] + ['2026-01']
    df_13 = pd.DataFrame({
        'period': periods,
        'revenue': [100000 * (i + 1) for i in range(13)],
        'cogs': [30000 * (i + 1) for i in range(13)],
        'gross_profit': [70000 * (i + 1) for i in range(13)],
        'sales_marketing': [20000 * (i + 1) for i in range(13)],
        'total_opex': [20000 * (i + 1) for i in range(13)],
        'ebitda': [50000 * (i + 1) for i in range(13)],
    })
    r5 = compute_margins(df_13)
    last = r5.periods[-1]
    # 2026-01 rev: 1300000, 2025-01 rev: 100000, YoY = 1200%
    check("13mo YoY=1200%", approx_pct(last.revenue_growth_yoy, 1200.0))

    # Exactly 12 months: no YoY (2025-01 through 2025-12, no 2024-01)
    df_12 = df_13.iloc[:12].copy()
    r6 = compute_margins(df_12)
    check("12mo→no YoY", r6.periods[-1].revenue_growth_yoy is None)


# ═══════════════════════════════════════════════════════════════════════════
#  EBITDA BRIDGE
# ═══════════════════════════════════════════════════════════════════════════

def test_ebitda_bridge():
    print("\n── EBITDA BRIDGE ──")
    from analysis.ebitda_bridge import compute_ebitda_bridges

    df = pd.DataFrame({
        'period': ['2025-01', '2025-02', '2025-03'],
        'revenue':        [1000000, 1100000, 1200000],
        'cogs':           [ 300000,  330000,  350000],
        'gross_profit':   [ 700000,  770000,  850000],
        'sales_marketing':[ 200000,  210000,  230000],
        'rd':             [ 100000,  105000,  110000],
        'ga':             [  50000,   52000,   55000],
        'total_opex':     [ 350000,  367000,  395000],
        'ebitda':         [ 350000,  403000,  455000],
        'budget_revenue': [None, None, 1250000],
        'budget_ebitda':  [None, None, 480000],
    })

    r = compute_ebitda_bridges(df)

    # MoM
    m = r.mom
    check("MoM exists", m is not None)
    check("MoM base=403000", m.base_ebitda == 403000)
    check("MoM current=455000", m.current_ebitda == 455000)
    check("MoM total=52000", m.total_change == 52000)

    # Manual: rev=+100000, cogs=-(350000-330000)=-20000, sm=-(230000-210000)=-20000
    # rd=-(110000-105000)=-5000, ga=-(55000-52000)=-3000
    # SUM: 100000-20000-20000-5000-3000 = 52000 ✓
    comps = {c.name: c.value for c in m.components}
    check("MoM rev=+100000", comps["Revenue"] == 100000)
    check("MoM cogs=-20000", comps["COGS"] == -20000)
    check("MoM sm=-20000", comps["Sales & Marketing"] == -20000)
    check("MoM rd=-5000", comps["R&D"] == -5000)
    check("MoM ga=-3000", comps["G&A"] == -3000)
    check("MoM verified", m.is_verified)
    check("MoM delta<0.01", m.verification_delta < 0.01)

    # Budget
    b = r.vs_budget
    check("Budget exists", b is not None)
    check("Budget base=480000", b.base_ebitda == 480000)
    check("Budget total=-25000", b.total_change == -25000)
    # Rev variance: 1200000 - 1250000 = -50000
    # Cost variance: -25000 - (-50000) = +25000
    bcomps = {c.name: c.value for c in b.components}
    check("Budget rev_var=-50000", bcomps["Revenue Variance"] == -50000)
    check("Budget cost_var=+25000", bcomps["Total Cost Variance"] == 25000)
    check("Budget verified", b.is_verified)

    # PY: no PY data (only 3 months)
    check("No PY (3 months)", r.vs_prior_year is None)

    # Specific period
    r2 = compute_ebitda_bridges(df, current_period='2025-02')
    check("Specific period=2025-02", r2.mom.current_period == '2025-02')
    check("Specific base=2025-01", r2.mom.base_period == '2025-01')
    check("Specific total=53000", r2.mom.total_change == 53000)

    # Single row
    df_single = df.iloc[:1].copy()
    r3 = compute_ebitda_bridges(df_single)
    check("Single row→no MoM", r3.mom is None)

    # No budget columns
    df_nb = df.drop(columns=['budget_revenue', 'budget_ebitda'])
    r4 = compute_ebitda_bridges(df_nb)
    check("No budget cols→None", r4.vs_budget is None)

    # Zero budget
    df_zb = df.copy()
    df_zb.loc[2, 'budget_revenue'] = 0
    df_zb.loc[2, 'budget_ebitda'] = 0
    r5 = compute_ebitda_bridges(df_zb)
    check("Zero budget→None", r5.vs_budget is None)

    # All zeros
    df_zeros = pd.DataFrame({
        'period': ['2025-01', '2025-02'],
        'revenue': [0, 0], 'cogs': [0, 0], 'gross_profit': [0, 0],
        'sales_marketing': [0, 0], 'rd': [0, 0], 'ga': [0, 0],
        'total_opex': [0, 0], 'ebitda': [0, 0],
    })
    r6 = compute_ebitda_bridges(df_zeros)
    check("Zeros→verified", r6.mom.is_verified)
    check("Zeros→total=0", r6.mom.total_change == 0)

    # Negative EBITDA
    df_neg = pd.DataFrame({
        'period': ['2025-01', '2025-02'],
        'revenue': [500000, 600000], 'cogs': [300000, 350000],
        'gross_profit': [200000, 250000],
        'sales_marketing': [250000, 280000], 'rd': [50000, 55000],
        'ga': [30000, 35000], 'total_opex': [330000, 370000],
        'ebitda': [-130000, -120000],
    })
    r7 = compute_ebitda_bridges(df_neg)
    check("Neg EBITDA verified", r7.mom.is_verified)
    check("Neg EBITDA total=+10000", r7.mom.total_change == 10000)


# ═══════════════════════════════════════════════════════════════════════════
#  VARIANCE
# ═══════════════════════════════════════════════════════════════════════════

def test_variance():
    print("\n── VARIANCE ──")
    from analysis.variance import compute_variance
    from analysis.types import Favorability

    df = pd.DataFrame({
        'period': ['2025-01', '2025-02'],
        'revenue':        [1000000, 1100000],
        'cogs':           [ 300000,  330000],
        'gross_profit':   [ 700000,  770000],
        'sales_marketing':[ 200000,  190000],  # SM went DOWN (favorable)
        'rd':             [ 100000,  110000],
        'ga':             [  50000,   55000],
        'total_opex':     [ 350000,  355000],
        'ebitda':         [ 350000,  415000],
    })

    r = compute_variance(df)
    check("2 periods", len(r.periods) == 2)

    # Period 1: no comparators
    check("P1 no prior", r.periods[0].vs_prior_month is None)

    # Period 2 vs prior month
    p2 = r.periods[1]
    check("P2 has prior", p2.vs_prior_month is not None)

    rev = p2.vs_prior_month[0]
    check("Rev change=+100000", rev.dollar_change == 100000)
    check("Rev pct=+10%", approx_pct(rev.pct_change, 10.0))
    check("Rev favorable", rev.favorable == Favorability.FAVORABLE)
    check("Rev as_pct_rev=9.09%", approx_pct(rev.as_pct_of_revenue, 100000/1100000*100))

    cogs = p2.vs_prior_month[1]
    check("COGS change=+30000", cogs.dollar_change == 30000)
    check("COGS unfavorable", cogs.favorable == Favorability.UNFAVORABLE)

    # SM went DOWN: 190000 - 200000 = -10000, favorable (cost reduced)
    sm = p2.vs_prior_month[3]
    check("SM change=-10000", sm.dollar_change == -10000)
    check("SM favorable (cost down)", sm.favorable == Favorability.FAVORABLE)

    ebitda = p2.vs_prior_month[7]
    check("EBITDA change=+65000", ebitda.dollar_change == 65000)
    check("EBITDA favorable", ebitda.favorable == Favorability.FAVORABLE)

    # Budget test
    df_b = df.copy()
    df_b['budget_revenue'] = [None, 1200000]
    df_b['budget_ebitda'] = [None, 400000]
    r2 = compute_variance(df_b)
    p2b = r2.periods[1]
    check("Budget variance exists", p2b.vs_budget is not None)
    brev = p2b.vs_budget[0]
    check("Budget rev=-100000", brev.dollar_change == -100000)
    check("Budget rev unfav", brev.favorable == Favorability.UNFAVORABLE)
    bebitda = p2b.vs_budget[1]
    check("Budget ebitda=+15000", bebitda.dollar_change == 15000)
    check("Budget ebitda fav", bebitda.favorable == Favorability.FAVORABLE)

    # Zero comparator
    df_z = pd.DataFrame({
        'period': ['2025-01', '2025-02'],
        'revenue': [0, 100000], 'cogs': [0, 30000],
        'gross_profit': [0, 70000], 'sales_marketing': [0, 20000],
        'total_opex': [0, 20000], 'ebitda': [0, 50000],
    })
    r3 = compute_variance(df_z)
    check("Zero comp→None pct", r3.periods[1].vs_prior_month[0].pct_change is None)


# ═══════════════════════════════════════════════════════════════════════════
#  WORKING CAPITAL
# ═══════════════════════════════════════════════════════════════════════════

def test_working_capital():
    print("\n── WORKING CAPITAL ──")
    from analysis.working_capital import compute_working_capital

    # Path 2: BS + IS
    bs = pd.DataFrame({
        'period': ['2025-10', '2025-11'],
        'cash': [5000000, 5200000],
        'accounts_receivable': [3000000, 3200000],
        'inventory': [500000, 480000],
        'prepaid_expenses': [100000, 100000],
        'other_current_assets': [50000, 50000],
        'accounts_payable': [1000000, 1050000],
        'accrued_liabilities': [500000, 520000],
        'other_current_liabilities': [200000, 200000],
        'total_current_assets': [8650000, 9030000],
        'total_assets': [14650000, 14980000],
        'total_current_liabilities': [1700000, 1770000],
        'total_liabilities': [4700000, 4670000],
        'total_equity': [9950000, 10310000],
        'total_liabilities_and_equity': [14650000, 14980000],
    })
    is_df = pd.DataFrame({
        'period': ['2025-10', '2025-11'],
        'revenue': [2500000, 2600000],
        'cogs': [750000, 780000],
    })

    r = compute_working_capital(balance_sheet_df=bs, income_df=is_df)
    check("2 periods", len(r.periods) == 2)

    p1 = r.periods[0]
    # DSO = (3000000 / 2500000) * 31 = 37.2
    expected_dso = (3000000 / 2500000) * 31
    check("P1 DSO=37.2", approx(p1.dso, expected_dso, tol=0.2))
    # DPO = (1000000 / 750000) * 31 = 41.3
    expected_dpo = (1000000 / 750000) * 31
    check("P1 DPO=41.3", approx(p1.dpo, expected_dpo, tol=0.2))
    # DIO = (500000 / 750000) * 31 = 20.7
    expected_dio = (500000 / 750000) * 31
    check("P1 DIO=20.7", approx(p1.dio, expected_dio, tol=0.2))
    # CCC = DSO + DIO - DPO
    expected_ccc = expected_dso + expected_dio - expected_dpo
    check("P1 CCC formula", approx(p1.ccc, expected_ccc, tol=0.2))

    p2 = r.periods[1]
    # WC change = delta(AR) + delta(inv) + delta(prepaid) + delta(other_ca) - delta(AP) - delta(accrued) - delta(other_cl)
    # = (3200000-3000000) + (480000-500000) + 0 + 0 - (1050000-1000000) - (520000-500000) - 0
    # = 200000 - 20000 - 50000 - 20000 = 110000
    check("P2 WC change=110000", p2.wc_change == 110000, f"got {p2.wc_change}")

    # No inventory
    bs_no_inv = bs.drop(columns=['inventory'])
    r2 = compute_working_capital(balance_sheet_df=bs_no_inv, income_df=is_df)
    check("No inventory→DIO=None", r2.periods[0].dio is None)
    # CCC should still work (DIO treated as 0)
    check("No inv→CCC still works", r2.periods[0].ccc is not None)

    # Empty
    r3 = compute_working_capital()
    check("Empty→0 periods", len(r3.periods) == 0)

    # Direct WC path
    wc_df = pd.DataFrame({
        'period': ['2025-10', '2025-11'],
        'ar_current': [2000000, 2100000],
        'ar_31_60': [500000, 480000],
        'ar_61_90': [200000, 180000],
        'ar_91_120': [80000, 70000],
        'ar_over_120': [20000, 15000],
        'ar_total': [2800000, 2845000],
        'ap_total': [1000000, 1050000],
        'dso': [45, 42],
        'dpo': [28, 29],
    })
    r4 = compute_working_capital(working_capital_df=wc_df)
    check("Direct DSO=45", r4.periods[0].dso == 45)
    check("Direct CCC=17", r4.periods[0].ccc == 17)
    # AR aging
    ag = r4.periods[0].ar_aging
    check("AR aging exists", ag is not None)
    check("AR current%=71.4%", approx_pct(ag.current_pct, 2000000/2800000*100))


# ═══════════════════════════════════════════════════════════════════════════
#  FCF
# ═══════════════════════════════════════════════════════════════════════════

def test_fcf():
    print("\n── FCF ──")
    from analysis.fcf import compute_fcf

    cf = pd.DataFrame({
        'period': ['2025-10', '2025-11', '2025-12'],
        'cash_from_operations': [400000, 450000, 500000],
        'capex': [-80000, -85000, -90000],
        'cash_from_investing': [-80000, -85000, -90000],
        'cash_from_financing': [-50000, -50000, -50000],
        'net_change_in_cash': [270000, 315000, 360000],
    })
    is_df = pd.DataFrame({
        'period': ['2025-10', '2025-11', '2025-12'],
        'ebitda': [350000, 395000, 440000],
    })
    bs = pd.DataFrame({
        'period': ['2025-10', '2025-11', '2025-12'],
        'cash': [5000000, 5200000, 5500000],
        'short_term_debt': [0, 0, 0],
        'long_term_debt': [3000000, 2900000, 2800000],
    })

    r = compute_fcf(cf, is_df, bs)
    check("3 periods", len(r.periods) == 3)

    # FCF = CFO + capex
    check("P1 FCF=320000", r.periods[0].free_cash_flow == 320000)
    check("P2 FCF=365000", r.periods[1].free_cash_flow == 365000)
    check("P3 FCF=410000", r.periods[2].free_cash_flow == 410000)

    # Cash conversion = FCF / EBITDA
    check("P1 CCR=0.914", approx(r.periods[0].cash_conversion_ratio, 320000/350000, tol=0.001))

    # Net debt = STD + LTD - cash
    check("P1 net_debt=-2M", r.periods[0].net_debt == -2000000)
    check("P3 net_debt=-2.7M", r.periods[2].net_debt == -2700000)

    # CF only (no IS or BS)
    r2 = compute_fcf(cf)
    check("CF only→FCF works", r2.periods[0].free_cash_flow == 320000)
    check("CF only→no CCR", r2.periods[0].cash_conversion_ratio is None)
    check("CF only→no net_debt", r2.periods[0].net_debt is None)

    # No data
    r3 = compute_fcf()
    check("No data→0 periods", len(r3.periods) == 0)


# ═══════════════════════════════════════════════════════════════════════════
#  REVENUE ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def test_revenue_analytics():
    print("\n── REVENUE ANALYTICS ──")
    from analysis.revenue_analytics import compute_revenue_analytics

    # Concentration: 4 products, 2 periods
    rev_df = pd.DataFrame({
        'period': ['2025-01']*4 + ['2025-02']*4,
        'product': ['A', 'B', 'C', 'D'] * 2,
        'revenue': [500000, 300000, 150000, 50000,  # period 1
                    600000, 280000, 170000, 50000],  # period 2
        'units_sold': [100, 60, 30, 10,
                       110, 56, 34, 10],
        'unit_price': [5000, 5000, 5000, 5000,
                       5455, 5000, 5000, 5000],  # A got a price increase
    })

    r = compute_revenue_analytics(revenue_detail_df=rev_df)

    # Concentration period 1: total=1M, top1=500K=50%
    c1 = r.concentration[0]
    check("Conc P1 top1=50%", approx_pct(c1.top1_pct, 50.0))
    check("Conc P1 count=4", c1.count == 4)
    # HHI = (0.5)^2 + (0.3)^2 + (0.15)^2 + (0.05)^2 = 0.25 + 0.09 + 0.0225 + 0.0025 = 0.365
    check("Conc P1 HHI=0.365", approx(c1.herfindahl, 0.365, tol=0.001))

    # Price/Volume decomposition
    check("P/V has 1 period", len(r.price_volume) == 1)
    pv = r.price_volume[0]

    # Total change: (600000+280000+170000+50000) - (500000+300000+150000+50000) = 1100000 - 1000000 = 100000
    check("PV total=100000", approx(pv.total_change, 100000))

    # Price effect: A: 110*(5455-5000)=50050, B: 56*(5000-5000)=0, C: 34*(5000-5000)=0, D: 10*(5000-5000)=0
    check("PV price=50050", approx(pv.price_effect, 50050))

    # Volume effect: A: (110-100)*5000=50000, B: (56-60)*5000=-20000, C: (34-30)*5000=20000, D: (10-10)*5000=0
    check("PV volume=50000", approx(pv.volume_effect, 50000))

    # Mix = total - price - volume = 100000 - 50050 - 50000 = -50
    check("PV mix=-50", approx(pv.mix_effect, -50))
    check("PV verified", pv.is_verified)

    # KPI trends
    kpi = pd.DataFrame({
        'period': ['2025-01', '2025-02'],
        'net_revenue_retention': [105, 110],
        'monthly_churn_rate': [3.5, 3.0],
    })
    r2 = compute_revenue_analytics(kpi_df=kpi)
    check("KPI NRR trend", 'net_revenue_retention' in r2.kpi_trends)
    check("KPI NRR 2 points", len(r2.kpi_trends['net_revenue_retention']) == 2)

    # No data
    r3 = compute_revenue_analytics()
    check("No data→empty", len(r3.concentration) == 0)


# ═══════════════════════════════════════════════════════════════════════════
#  TRENDS
# ═══════════════════════════════════════════════════════════════════════════

def test_trends():
    print("\n── TRENDS ──")
    from analysis.trends import detect_trends
    from analysis.types import FlagType, Severity

    # Consecutive decline: exactly 3
    m1 = {'x': [('01', 10), ('02', 9), ('03', 8), ('04', 7)]}
    r1 = detect_trends(m1, consecutive_n_warn=3, consecutive_n_crit=5)
    flags_cd = [f for f in r1.flags if f.flag_type == FlagType.CONSECUTIVE_DECLINE]
    check("3 decline→warning", len(flags_cd) == 1 and flags_cd[0].severity == Severity.WARNING)

    # Consecutive decline: 5 → critical
    m2 = {'x': [('01', 10), ('02', 9), ('03', 8), ('04', 7), ('05', 6), ('06', 5)]}
    r2 = detect_trends(m2, consecutive_n_warn=3, consecutive_n_crit=5)
    flags_cd2 = [f for f in r2.flags if f.flag_type == FlagType.CONSECUTIVE_DECLINE]
    check("5 decline→critical", len(flags_cd2) == 1 and flags_cd2[0].severity == Severity.CRITICAL)

    # No decline (increasing)
    m3 = {'x': [('01', 1), ('02', 2), ('03', 3), ('04', 4)]}
    r3 = detect_trends(m3)
    check("Increasing→no decline", len([f for f in r3.flags if f.flag_type == FlagType.CONSECUTIVE_DECLINE]) == 0)

    # Flat → no decline
    m4 = {'x': [('01', 5), ('02', 5), ('03', 5), ('04', 5)]}
    r4 = detect_trends(m4)
    check("Flat→no decline", len([f for f in r4.flags if f.flag_type == FlagType.CONSECUTIVE_DECLINE]) == 0)

    # Margin compression: 250bps drop
    m5 = {'gross_margin_pct': [('01', 70.0), ('02', 67.5)]}
    r5 = detect_trends(m5, margin_compression_bps=200)
    mc = [f for f in r5.flags if f.flag_type == FlagType.MARGIN_COMPRESSION]
    check("250bps→margin flag", len(mc) == 1)

    # Small drop → no flag
    m6 = {'ebitda_margin_pct': [('01', 35.0), ('02', 34.8)]}
    r6 = detect_trends(m6, margin_compression_bps=200)
    check("20bps→no flag", len([f for f in r6.flags if f.flag_type == FlagType.MARGIN_COMPRESSION]) == 0)

    # Non-margin metric → no margin compression check
    m7 = {'revenue': [('01', 1000), ('02', 500)]}
    r7 = detect_trends(m7)
    check("Non-margin→no MC flag", len([f for f in r7.flags if f.flag_type == FlagType.MARGIN_COMPRESSION]) == 0)

    # Anomaly: spike
    m8 = {'y': [('01', 100), ('02', 101), ('03', 99), ('04', 100), ('05', 102), ('06', 98), ('07', 250)]}
    r8 = detect_trends(m8, trailing_window=6)
    anom = [f for f in r8.flags if f.flag_type == FlagType.ANOMALY]
    check("Spike→anomaly", len(anom) >= 1)
    check("Spike→critical", anom[0].severity == Severity.CRITICAL)

    # Normal value → no anomaly
    m9 = {'y': [('01', 100), ('02', 101), ('03', 99), ('04', 100), ('05', 102), ('06', 98), ('07', 101)]}
    r9 = detect_trends(m9, trailing_window=6)
    check("Normal→no anomaly", len([f for f in r9.flags if f.flag_type == FlagType.ANOMALY]) == 0)

    # Too few points → no anomaly
    m10 = {'y': [('01', 100), ('02', 200)]}
    r10 = detect_trends(m10)
    check("2 points→no anomaly", len([f for f in r10.flags if f.flag_type == FlagType.ANOMALY]) == 0)

    # Deceleration
    m11 = {'rev': [('01', 100), ('02', 120), ('03', 135), ('04', 145), ('05', 150)]}
    r11 = detect_trends(m11)
    accel = [f for f in r11.flags if f.flag_type == FlagType.ACCELERATION_CHANGE]
    check("Deceleration→flag", len(accel) >= 1)

    # Single point → no flags
    m12 = {'x': [('01', 100)]}
    r12 = detect_trends(m12)
    check("1 point→no flags", len(r12.flags) == 0)

    # Empty
    r13 = detect_trends({})
    check("Empty→no flags", len(r13.flags) == 0)


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def test_engine():
    print("\n── ENGINE ──")
    from analysis.engine import run_analysis
    from core.result import NormalizedResult

    # Minimal: just IS
    is_df = pd.DataFrame({
        'period': ['2025-01', '2025-02', '2025-03'],
        'revenue': [1000000, 1100000, 1200000],
        'cogs': [300000, 330000, 360000],
        'gross_profit': [700000, 770000, 840000],
        'sales_marketing': [200000, 220000, 240000],
        'rd': [100000, 110000, 120000],
        'ga': [50000, 55000, 60000],
        'total_opex': [350000, 385000, 420000],
        'ebitda': [350000, 385000, 420000],
    })

    data = {
        "income_statement": NormalizedResult(df=is_df, doc_type="income_statement"),
    }

    r = run_analysis(data)
    check("IS only→bridge", r.ebitda_bridges is not None)
    check("IS only→variance", r.variance is not None)
    check("IS only→margins", r.margins is not None)
    check("IS only→no WC", r.working_capital is None)
    check("IS only→no FCF", r.fcf is None)
    check("IS only→no rev", r.revenue_analytics is None)
    check("IS only→trends", r.trends is not None)
    check("IS only→3 modules+trends", len(r.modules_run) >= 3)
    check("IS only→0 warnings", len(r.warnings) == 0)

    # Empty
    r2 = run_analysis({})
    check("Empty→all None", r2.ebitda_bridges is None and r2.margins is None)
    check("Empty→0 modules", len(r2.modules_run) == 0)


# ═══════════════════════════════════════════════════════════════════════════
#  CROSS-VERIFICATION: Use real test data files
# ═══════════════════════════════════════════════════════════════════════════

def test_real_data():
    print("\n── REAL DATA CROSS-VERIFICATION ──")
    from core.ingest import ingest_file
    from analysis.engine import run_analysis

    data = {}
    for doc_type, path in [
        ('income_statement', 'data/sample_pl.csv'),
        ('balance_sheet', 'data/test/balance_sheet_clean.csv'),
        ('cash_flow', 'data/test/cash_flow_clean.csv'),
        ('working_capital', 'data/test/working_capital_clean.csv'),
        ('revenue_detail', 'data/test/revenue_detail_clean.csv'),
        ('kpi_operational', 'data/test/kpi_operational_clean.csv'),
    ]:
        data[doc_type] = ingest_file(path)

    r = run_analysis(data)
    check("Real: 8 modules", len(r.modules_run) == 8, f"got {len(r.modules_run)}: {r.modules_run}")
    check("Real: 0 warnings", len(r.warnings) == 0, f"got: {r.warnings}")

    # Verify EBITDA bridge math
    b = r.ebitda_bridges.mom
    check("Real: bridge verified", b.is_verified)
    comp_sum = sum(c.value for c in b.components)
    check("Real: comp_sum=total", approx(comp_sum, b.total_change))

    # Verify margins make sense
    m = r.margins.periods[-1]
    check("Real: GM 60-90%", 60 < m.gross_margin_pct < 90)
    check("Real: EBITDA margin 0-50%", 0 < m.ebitda_margin_pct < 50)

    # Verify WC
    wc = r.working_capital.periods[-1]
    check("Real: DSO>0", wc.dso is not None and wc.dso > 0)
    check("Real: CCC computed", wc.ccc is not None)

    # Verify PV decomposition
    if r.revenue_analytics.price_volume:
        pv = r.revenue_analytics.price_volume[-1]
        check("Real: PV verified", pv.is_verified)


# ═══════════════════════════════════════════════════════════════════════════
#  RUN ALL
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_utils()
    test_margins()
    test_ebitda_bridge()
    test_variance()
    test_working_capital()
    test_fcf()
    test_revenue_analytics()
    test_trends()
    test_engine()
    test_real_data()

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed out of {TOTAL} tests")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
