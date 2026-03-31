'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react';

interface AssumptionsProps {
  assumptions: Record<string, number> | null;
  onUpdate: (changes: Record<string, number>) => Promise<void>;
}

const FIELDS = [
  { key: 'revenue_growth_pct', label: 'Revenue Growth %', suffix: '%' },
  { key: 'cogs_pct', label: 'COGS %', suffix: '%' },
  { key: 'sm_pct', label: 'S&M %', suffix: '%' },
  { key: 'rd_pct', label: 'R&D %', suffix: '%' },
  { key: 'ga_pct', label: 'G&A %', suffix: '%' },
  { key: 'dso', label: 'DSO', suffix: ' days' },
  { key: 'dpo', label: 'DPO', suffix: ' days' },
  { key: 'exit_multiple', label: 'Exit Multiple', suffix: 'x' },
];

export default function Assumptions({ assumptions, onUpdate }: AssumptionsProps) {
  const [expanded, setExpanded] = useState(false);
  const [localValues, setLocalValues] = useState<Record<string, string>>({});
  const [updating, setUpdating] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (assumptions) {
      const vals: Record<string, string> = {};
      for (const f of FIELDS) {
        if (assumptions[f.key] != null) {
          vals[f.key] = String(assumptions[f.key]);
        }
      }
      setLocalValues(vals);
    }
  }, [assumptions]);

  const handleChange = useCallback(
    (key: string, value: string) => {
      setLocalValues((prev) => ({ ...prev, [key]: value }));

      if (debounceRef.current) clearTimeout(debounceRef.current);

      debounceRef.current = setTimeout(async () => {
        const numVal = parseFloat(value);
        if (!isNaN(numVal)) {
          setUpdating(true);
          try {
            await onUpdate({ [key]: numVal });
          } catch (e) {
            console.error('Failed to update:', e);
          } finally {
            setUpdating(false);
          }
        }
      }, 500);
    },
    [onUpdate]
  );

  // Calculate implied EBITDA margin
  const impliedMargin = (() => {
    const cogs = parseFloat(localValues.cogs_pct || '0') || 0;
    const sm = parseFloat(localValues.sm_pct || '0') || 0;
    const rd = parseFloat(localValues.rd_pct || '0') || 0;
    const ga = parseFloat(localValues.ga_pct || '0') || 0;
    const gross = 100 - cogs;
    const ebitda = gross - sm - rd - ga;
    return ebitda;
  })();

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-6 text-left"
      >
        <div className="flex items-center space-x-3">
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
          <h2 className="text-base font-semibold text-gray-900">
            Assumptions & Scenario Inputs
          </h2>
        </div>
        <div className="flex items-center space-x-3">
          {updating && (
            <span className="flex items-center text-xs text-indigo-600">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              Updating...
            </span>
          )}
          <span className="text-sm text-gray-500">
            Implied EBITDA Margin:{' '}
            <span className={`font-semibold ${impliedMargin >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {impliedMargin.toFixed(1)}%
            </span>
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-gray-100 pt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {FIELDS.map((field) => (
              <div key={field.key}>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                  {field.label}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    value={localValues[field.key] ?? ''}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                    placeholder="—"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">
                    {field.suffix}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
