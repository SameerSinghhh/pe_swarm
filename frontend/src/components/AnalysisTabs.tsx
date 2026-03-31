'use client';

import { useState } from 'react';
import { AnalysisData, EBITDABridge, EBITDABridgesResponse, BridgeComponent, Margins, LineVariance, VariancePeriod, WCPeriod, FCFPeriod, TrendFlag } from '@/lib/types';
import { fmtDollar, fmtPct, fmtDays, fmtRatio, valueColor } from '@/lib/format';

interface AnalysisTabsProps {
  analysis: AnalysisData | null;
}

const TABS = ['Bridge', 'Margins', 'Variance', 'WC', 'FCF', 'Flags'] as const;
type TabName = typeof TABS[number];

export default function AnalysisTabs({ analysis }: AnalysisTabsProps) {
  const [activeTab, setActiveTab] = useState<TabName>('Bridge');

  if (!analysis) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <EmptyState message="No analysis data available" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      {/* Tab bar */}
      <div className="border-b border-gray-200 px-6">
        <nav className="flex space-x-8" aria-label="Analysis tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="p-6">
        {activeTab === 'Bridge' && <BridgeTab bridges={analysis.ebitda_bridges} />}
        {activeTab === 'Margins' && <MarginsTab margins={analysis.margins} />}
        {activeTab === 'Variance' && <VarianceTab variance={analysis.variance} />}
        {activeTab === 'WC' && <WCTab wc={analysis.working_capital} />}
        {activeTab === 'FCF' && <FCFTab fcf={analysis.fcf} />}
        {activeTab === 'Flags' && <FlagsTab trends={analysis.trends} />}
      </div>
    </div>
  );
}

/** Render a single EBITDA bridge table */
function BridgeSection({ bridge, title }: { bridge: EBITDABridge; title: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">{bridge.label ?? title}</h3>
        {bridge.is_verified && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
            Verified
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Component
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Impact
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr className="bg-gray-50/50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                Base EBITDA ({bridge.base_period ?? '—'})
              </td>
              <td className="px-4 py-3 text-sm text-right text-gray-900 font-medium">
                {fmtDollar(bridge.base_ebitda ?? null)}
              </td>
            </tr>
            {(bridge.components ?? []).map((comp: BridgeComponent, i: number) => (
              <tr key={i}>
                <td className="px-4 py-3 text-sm text-gray-700">{comp?.name ?? '—'}</td>
                <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(comp?.value ?? null)}`}>
                  {(comp?.value ?? 0) > 0 ? '+' : ''}{fmtDollar(comp?.value ?? null)}
                </td>
              </tr>
            ))}
            <tr className="bg-gray-50/50 font-semibold">
              <td className="px-4 py-3 text-sm text-gray-900">
                Current EBITDA ({bridge.current_period ?? '—'})
              </td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">
                {fmtDollar(bridge.current_ebitda ?? null)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BridgeTab({ bridges }: { bridges: EBITDABridgesResponse | null }) {
  if (!bridges) {
    return <EmptyState message="No EBITDA bridge data available" />;
  }

  // Extract the named bridges, filtering out nulls
  const entries: { key: string; bridge: EBITDABridge }[] = [];
  if (bridges.mom) entries.push({ key: 'mom', bridge: bridges.mom });
  if (bridges.vs_budget) entries.push({ key: 'vs_budget', bridge: bridges.vs_budget });
  if (bridges.vs_prior_year) entries.push({ key: 'vs_prior_year', bridge: bridges.vs_prior_year });

  if (entries.length === 0) {
    return <EmptyState message="No EBITDA bridge data available" />;
  }

  return (
    <div className="space-y-6">
      {entries.map(({ key, bridge }) => (
        <BridgeSection key={key} bridge={bridge} title={key.replace(/_/g, ' ')} />
      ))}
    </div>
  );
}

function MarginsTab({ margins }: { margins: { periods: Margins[] } | null }) {
  if (!margins?.periods?.length) {
    return <EmptyState message="No margin data available" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Period</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Gross Margin</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">EBITDA Margin</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">S&M %</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">R&D %</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">G&A %</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Rev Growth MoM</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Rev Growth YoY</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {margins.periods.map((p, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{p?.period ?? '—'}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.gross_margin_pct ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.ebitda_margin_pct ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.sm_pct_revenue ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.rd_pct_revenue ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.ga_pct_revenue ?? null)}</td>
              <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(p?.revenue_growth_mom ?? null)}`}>
                {fmtPct(p?.revenue_growth_mom ?? null)}
              </td>
              <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(p?.revenue_growth_yoy ?? null)}`}>
                {fmtPct(p?.revenue_growth_yoy ?? null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Render a single variance comparison table */
function VarianceSection({ items, title }: { items: LineVariance[]; title: string }) {
  if (!items?.length) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-900 mb-3 capitalize">
        {title}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Line Item</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actual</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Comparator</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">$ Change</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">% Change</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">F/U</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item: LineVariance, i: number) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
                <td className="px-4 py-3 text-sm text-gray-900">{item?.line_item ?? '—'}</td>
                <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDollar(item?.actual ?? null)}</td>
                <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDollar(item?.comparator ?? null)}</td>
                <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(item?.dollar_change ?? null)}`}>
                  {(item?.dollar_change ?? 0) > 0 ? '+' : ''}{fmtDollar(item?.dollar_change ?? null)}
                </td>
                <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(item?.pct_change ?? null)}`}>
                  {fmtPct(item?.pct_change ?? null)}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    item?.favorable === 'favorable'
                      ? 'bg-emerald-50 text-emerald-700'
                      : item?.favorable === 'unfavorable'
                      ? 'bg-red-50 text-red-700'
                      : 'bg-gray-50 text-gray-600'
                  }`}>
                    {item?.favorable === 'favorable' ? 'F' : item?.favorable === 'unfavorable' ? 'U' : '—'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function VarianceTab({ variance }: { variance: { periods: VariancePeriod[] } | null }) {
  if (!variance?.periods?.length) {
    return <EmptyState message="No variance data available" />;
  }

  return (
    <div className="space-y-6">
      {variance.periods.map((period, pi) => {
        if (!period) return null;
        const sections: { key: string; title: string; items: LineVariance[] | null }[] = [
          { key: 'vs_prior_month', title: `${period.period ?? ''} vs Prior Month`, items: period.vs_prior_month },
          { key: 'vs_budget', title: `${period.period ?? ''} vs Budget`, items: period.vs_budget },
          { key: 'vs_prior_year', title: `${period.period ?? ''} vs Prior Year`, items: period.vs_prior_year },
        ];

        const validSections = sections.filter(s => s.items && s.items.length > 0);

        if (validSections.length === 0) return null;

        return (
          <div key={pi} className="space-y-4">
            {validSections.map((s) => (
              <VarianceSection key={`${pi}-${s.key}`} items={s.items!} title={s.title} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

function WCTab({ wc }: { wc: { periods: WCPeriod[] } | null }) {
  if (!wc?.periods?.length) {
    return <EmptyState message="No working capital data available" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Period</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">DSO</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">DPO</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">DIO</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">CCC</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">WC Change</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {wc.periods.map((p, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{p?.period ?? '—'}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDays(p?.dso ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDays(p?.dpo ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDays(p?.dio ?? null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDays(p?.ccc ?? null)}</td>
              <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(p?.wc_change ?? null)}`}>
                {fmtDollar(p?.wc_change ?? null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FCFTab({ fcf }: { fcf: { periods: FCFPeriod[] } | null }) {
  if (!fcf?.periods?.length) {
    return <EmptyState message="No FCF data available" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Period</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Free Cash Flow</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Cash Conversion</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Net Debt / EBITDA</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {fcf.periods.map((p, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{p?.period ?? '—'}</td>
              <td className={`px-4 py-3 text-sm text-right font-medium ${valueColor(p?.free_cash_flow ?? null)}`}>
                {fmtDollar(p?.free_cash_flow ?? null)}
              </td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(p?.cash_conversion_ratio != null ? p.cash_conversion_ratio * 100 : null)}</td>
              <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtRatio(p?.net_debt_to_ltm_ebitda ?? null)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FlagsTab({ trends }: { trends: { flags: TrendFlag[] } | null }) {
  if (!trends?.flags?.length) {
    return <EmptyState message="No trend flags detected" />;
  }

  const severityColor = (severity: string | null | undefined) => {
    switch ((severity ?? '').toLowerCase()) {
      case 'high': return 'bg-red-50 text-red-700 border-red-200';
      case 'medium': case 'warning': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'low': case 'info': return 'bg-blue-50 text-blue-700 border-blue-200';
      default: return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className="space-y-3">
      {trends.flags.map((flag, i) => {
        if (!flag) return null;
        return (
          <div
            key={i}
            className={`rounded-lg border p-4 ${severityColor(flag.severity)}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold">{flag.metric ?? '—'}</span>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-medium uppercase">{(flag.flag_type ?? '').replace(/_/g, ' ')}</span>
                {flag.period && (
                  <span className="text-xs opacity-75">{flag.period}</span>
                )}
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold uppercase">
                  {flag.severity ?? '—'}
                </span>
              </div>
            </div>
            <p className="text-sm opacity-90">{flag.detail ?? ''}</p>
          </div>
        );
      })}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
