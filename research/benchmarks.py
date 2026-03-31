"""
Static industry benchmarks from known sources.

Data compiled from NYU Stern Damodaran database, SaaS benchmarking reports,
and industry standard ranges. These are reference points, not real-time data.
"""

from research.types import IndustryBenchmark


# Benchmark data by sector
# Format: (metric, 25th percentile, median, 75th percentile)
_BENCHMARKS = {
    "B2B SaaS": [
        ("gross_margin_pct", 68.0, 75.0, 82.0),
        ("ebitda_margin_pct", 5.0, 15.0, 25.0),
        ("revenue_growth_yoy_pct", 15.0, 28.0, 45.0),
        ("sm_pct_revenue", 25.0, 35.0, 50.0),
        ("rd_pct_revenue", 15.0, 22.0, 30.0),
        ("ga_pct_revenue", 8.0, 12.0, 18.0),
        ("nrr_pct", 100.0, 110.0, 120.0),
        ("cac_payback_months", 12.0, 18.0, 24.0),
        ("ltv_cac_ratio", 3.0, 5.0, 8.0),
        ("rule_of_40", 20.0, 35.0, 55.0),
    ],
    "Software": [
        ("gross_margin_pct", 65.0, 72.0, 80.0),
        ("ebitda_margin_pct", 8.0, 18.0, 28.0),
        ("revenue_growth_yoy_pct", 10.0, 20.0, 35.0),
        ("sm_pct_revenue", 20.0, 30.0, 42.0),
        ("rd_pct_revenue", 12.0, 18.0, 25.0),
        ("ga_pct_revenue", 6.0, 10.0, 15.0),
    ],
    "Manufacturing": [
        ("gross_margin_pct", 25.0, 35.0, 45.0),
        ("ebitda_margin_pct", 8.0, 13.0, 18.0),
        ("revenue_growth_yoy_pct", 3.0, 6.0, 12.0),
        ("sm_pct_revenue", 5.0, 8.0, 12.0),
        ("rd_pct_revenue", 2.0, 4.0, 7.0),
        ("ga_pct_revenue", 4.0, 7.0, 10.0),
        ("dso_days", 35.0, 45.0, 55.0),
        ("dio_days", 40.0, 60.0, 80.0),
        ("dpo_days", 30.0, 40.0, 50.0),
    ],
    "Services": [
        ("gross_margin_pct", 35.0, 50.0, 65.0),
        ("ebitda_margin_pct", 8.0, 15.0, 22.0),
        ("revenue_growth_yoy_pct", 5.0, 10.0, 18.0),
        ("sm_pct_revenue", 8.0, 12.0, 18.0),
        ("rd_pct_revenue", 1.0, 3.0, 6.0),
        ("ga_pct_revenue", 6.0, 10.0, 14.0),
    ],
    "Healthcare Services": [
        ("gross_margin_pct", 30.0, 42.0, 55.0),
        ("ebitda_margin_pct", 8.0, 14.0, 20.0),
        ("revenue_growth_yoy_pct", 5.0, 10.0, 18.0),
    ],
    "Distribution": [
        ("gross_margin_pct", 15.0, 22.0, 30.0),
        ("ebitda_margin_pct", 3.0, 6.0, 10.0),
        ("revenue_growth_yoy_pct", 3.0, 7.0, 12.0),
        ("dso_days", 30.0, 40.0, 50.0),
        ("dio_days", 25.0, 35.0, 50.0),
    ],
    "Retail": [
        ("gross_margin_pct", 25.0, 35.0, 50.0),
        ("ebitda_margin_pct", 4.0, 8.0, 14.0),
        ("revenue_growth_yoy_pct", 2.0, 5.0, 10.0),
    ],
}

# Sector aliases
_ALIASES = {
    "saas": "B2B SaaS",
    "b2b saas": "B2B SaaS",
    "technology": "Software",
    "tech": "Software",
    "software": "Software",
    "industrial": "Manufacturing",
    "industrial manufacturing": "Manufacturing",
    "manufacturing": "Manufacturing",
    "services": "Services",
    "professional services": "Services",
    "healthcare": "Healthcare Services",
    "healthcare services": "Healthcare Services",
    "distribution": "Distribution",
    "logistics": "Distribution",
    "logistics & distribution": "Distribution",
    "retail": "Retail",
    "data & analytics": "Software",
}


def get_benchmarks(sector: str) -> list[IndustryBenchmark]:
    """Get industry benchmarks for a sector."""
    normalized = _ALIASES.get(sector.lower().strip(), sector)

    if normalized not in _BENCHMARKS:
        # Try partial match
        for key in _BENCHMARKS:
            if key.lower() in sector.lower() or sector.lower() in key.lower():
                normalized = key
                break

    if normalized not in _BENCHMARKS:
        return []

    return [
        IndustryBenchmark(
            sector=normalized,
            metric=metric,
            percentile_25=p25,
            median=med,
            percentile_75=p75,
            source="Industry benchmarks (Damodaran / SaaS benchmarking reports)",
        )
        for metric, p25, med, p75 in _BENCHMARKS[normalized]
    ]


def get_all_sectors() -> list[str]:
    """Return all available sector names."""
    return list(_BENCHMARKS.keys())
