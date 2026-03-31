'use client';

import { Search, Loader2 } from 'lucide-react';
import { ResearchData, PeerCompany, GapAnalysis } from '@/lib/types';
import { fmtDollar, fmtPct, fmtRatio } from '@/lib/format';

interface ResearchPanelProps {
  data: ResearchData | null;
  onRun: () => Promise<void>;
  loading: boolean;
}

export default function ResearchPanel({ data, onRun, loading }: ResearchPanelProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="p-6 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="w-4 h-4 text-indigo-600" />
          <h2 className="text-base font-semibold text-gray-900">Peer Research & Benchmarking</h2>
        </div>
        <button
          onClick={onRun}
          disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center space-x-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Researching...</span>
            </>
          ) : (
            <span>Run Research</span>
          )}
        </button>
      </div>

      {data && (
        <div className="p-6 space-y-8">
          {/* Peer Comparison Table */}
          {data.peers?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Peer Comparison</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Gross Margin</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">EBITDA Margin</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue Growth</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">EV/EBITDA</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.peers.map((peer: PeerCompany, i: number) => (
                      <tr
                        key={i}
                        className={i === 0 ? 'bg-indigo-50/50' : i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}
                      >
                        <td className={`px-4 py-3 text-sm ${i === 0 ? 'font-semibold text-indigo-700' : 'text-gray-900'}`}>
                          {peer.name}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">{peer.ticker || '—'}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtDollar(peer.revenue)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(peer.gross_margin_pct)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(peer.ebitda_margin_pct)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtPct(peer.revenue_growth_yoy_pct)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtRatio(peer.ev_to_ebitda)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Gap Analysis Table */}
          {data.gap_analysis?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Gap Analysis</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Metric</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Peer Median</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Gap</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Opportunity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.gap_analysis.map((gap: GapAnalysis, i: number) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{gap.metric}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{gap.company_value.toFixed(1)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">{gap.peer_median.toFixed(1)}</td>
                        <td className={`px-4 py-3 text-sm text-right font-medium ${gap.gap >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                          {gap.gap > 0 ? '+' : ''}{gap.gap.toFixed(1)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">{gap.opportunity}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {!data && !loading && (
        <div className="p-12 text-center">
          <p className="text-sm text-gray-500">
            Run research to see peer comparisons and gap analysis
          </p>
        </div>
      )}
    </div>
  );
}
