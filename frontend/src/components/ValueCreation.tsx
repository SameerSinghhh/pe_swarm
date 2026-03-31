'use client';

import { Loader2, TrendingUp, Clock, DollarSign, Target } from 'lucide-react';
import { ValueCreationData, SizedInitiative } from '@/lib/types';
import { fmtDollar } from '@/lib/format';

interface ValueCreationProps {
  data: ValueCreationData | null;
  onRun: () => Promise<void>;
  loading: boolean;
}

const confidenceColor = (c: string) => {
  switch (c.toLowerCase()) {
    case 'high': return 'bg-emerald-50 text-emerald-700';
    case 'medium': return 'bg-amber-50 text-amber-700';
    case 'low': return 'bg-red-50 text-red-700';
    default: return 'bg-gray-50 text-gray-600';
  }
};

const categoryColor = (c: string) => {
  const colors: Record<string, string> = {
    revenue: 'bg-blue-50 text-blue-700',
    pricing: 'bg-purple-50 text-purple-700',
    margin: 'bg-emerald-50 text-emerald-700',
    cost: 'bg-amber-50 text-amber-700',
    working_capital: 'bg-cyan-50 text-cyan-700',
    growth: 'bg-indigo-50 text-indigo-700',
  };
  return colors[c.toLowerCase()] || 'bg-gray-50 text-gray-600';
};

export default function ValueCreation({ data, onRun, loading }: ValueCreationProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="p-6 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Target className="w-4 h-4 text-indigo-600" />
          <h2 className="text-base font-semibold text-gray-900">Value Creation Plan</h2>
        </div>
        <button
          onClick={onRun}
          disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center space-x-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <span>Run Value Creation</span>
          )}
        </button>
      </div>

      {data && (
        <div className="p-6 space-y-6">
          {/* Total opportunity */}
          <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-xl p-6 text-white">
            <p className="text-sm font-medium text-indigo-200 uppercase tracking-wider">
              Total Annual EBITDA Opportunity
            </p>
            <p className="text-3xl font-bold mt-1">
              {fmtDollar(data.total_opportunity)}
            </p>
            <p className="text-sm text-indigo-200 mt-1">
              Across {data.initiatives.length} identified initiatives
            </p>
          </div>

          {/* Initiative cards */}
          <div className="space-y-4">
            {data.initiatives.map((init: SizedInitiative, i: number) => (
              <div
                key={i}
                className="border border-gray-200 rounded-xl p-5 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-700 rounded-lg flex items-center justify-center text-sm font-bold">
                      {i + 1}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">{init.name}</h3>
                      <p className="text-sm text-gray-500 mt-0.5">{init.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${categoryColor(init.category)}`}>
                      {init.category}
                    </span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${confidenceColor(init.confidence)}`}>
                      {init.confidence}
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-6 text-sm">
                  <div className="flex items-center space-x-1.5 text-emerald-600">
                    <DollarSign className="w-3.5 h-3.5" />
                    <span className="font-semibold">{fmtDollar(init.ebitda_impact_annual)}/yr</span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-gray-500">
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>Cost: {fmtDollar(init.implementation_cost)}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-gray-500">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{init.timeline_months} months</span>
                  </div>
                </div>

                {init.specific_tools?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {init.specific_tools.map((tool, j) => (
                      <span
                        key={j}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!data && !loading && (
        <div className="p-12 text-center">
          <p className="text-sm text-gray-500">
            Run value creation analysis to identify EBITDA improvement opportunities
          </p>
        </div>
      )}
    </div>
  );
}
