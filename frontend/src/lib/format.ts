export function fmtDollar(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  const abs = Math.abs(val);
  const sign = val < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
  return `${sign}$${abs.toLocaleString()}`;
}

export function fmtPct(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${val.toFixed(1)}%`;
}

export function fmtRatio(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${val.toFixed(2)}x`;
}

export function fmtNumber(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function fmtDays(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${val.toFixed(0)} days`;
}

export function valueColor(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'text-gray-900';
  if (val > 0) return 'text-emerald-600';
  if (val < 0) return 'text-red-600';
  return 'text-gray-900';
}
