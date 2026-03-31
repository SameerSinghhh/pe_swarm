'use client';

import { LTMMetrics, Returns } from '@/lib/types';
import { fmtDollar, fmtPct, fmtRatio } from '@/lib/format';

interface MetricCardsProps {
  ltm: LTMMetrics | null;
  returns: Returns | null;
}

interface CardData {
  label: string;
  value: string;
  delta?: string;
  deltaPositive?: boolean;
}

export default function MetricCards({ ltm, returns }: MetricCardsProps) {
  const revenueGrowth = ltm?.ltm_revenue_growth_yoy ?? null;
  const ruleOf40 = ltm?.rule_of_40 ?? null;

  const cards: CardData[] = [
    {
      label: 'LTM Revenue',
      value: fmtDollar(ltm?.ltm_revenue ?? null),
      delta: revenueGrowth != null
        ? `${revenueGrowth > 0 ? '+' : ''}${revenueGrowth.toFixed(1)}% YoY`
        : undefined,
      deltaPositive: revenueGrowth != null ? revenueGrowth > 0 : undefined,
    },
    {
      label: 'LTM EBITDA',
      value: fmtDollar(ltm?.ltm_ebitda ?? null),
    },
    {
      label: 'EBITDA Margin',
      value: fmtPct(ltm?.ltm_ebitda_margin_pct ?? null),
    },
    {
      label: 'Rule of 40',
      value: ruleOf40 != null ? ruleOf40.toFixed(1) : '—',
      deltaPositive: ruleOf40 != null ? ruleOf40 >= 40 : undefined,
      delta: ruleOf40 != null
        ? (ruleOf40 >= 40 ? 'Above threshold' : 'Below threshold')
        : undefined,
    },
    {
      label: 'MOIC',
      value: fmtRatio(returns?.moic ?? null),
    },
    {
      label: 'IRR',
      value: fmtPct(returns?.irr ?? null),
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 flex flex-col"
        >
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            {card.label}
          </p>
          <p className="text-2xl font-semibold text-gray-900 tracking-tight">
            {card.value}
          </p>
          {card.delta && (
            <p
              className={`text-xs mt-1 font-medium ${
                card.deltaPositive === true
                  ? 'text-emerald-600'
                  : card.deltaPositive === false
                  ? 'text-red-600'
                  : 'text-gray-500'
              }`}
            >
              {card.delta}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
