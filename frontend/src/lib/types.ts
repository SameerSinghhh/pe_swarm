export interface LTMMetrics {
  ltm_revenue: number | null;
  ltm_ebitda: number | null;
  ltm_ebitda_margin_pct: number | null;
  rule_of_40: number | null;
  ltm_revenue_growth_yoy: number | null;
}

export interface Returns {
  moic: number | null;
  irr: number | null;
  exit_equity: number | null;
}

export interface BridgeComponent {
  name: string;
  value: number;
}

export interface EBITDABridge {
  label: string;
  base_period: string;
  current_period: string;
  base_ebitda: number;
  current_ebitda: number;
  components: BridgeComponent[];
  total_change: number;
  is_verified: boolean;
}

/** The actual API shape for ebitda_bridges */
export interface EBITDABridgesResponse {
  current_period: string;
  mom: EBITDABridge | null;
  vs_budget: EBITDABridge | null;
  vs_prior_year: EBITDABridge | null;
}

export interface Margins {
  period: string;
  gross_margin_pct: number | null;
  ebitda_margin_pct: number | null;
  sm_pct_revenue: number | null;
  rd_pct_revenue: number | null;
  ga_pct_revenue: number | null;
  revenue_growth_mom: number | null;
  revenue_growth_yoy: number | null;
}

export interface LineVariance {
  line_item: string;
  actual: number;
  comparator: number;
  dollar_change: number;
  pct_change: number | null;
  as_pct_of_revenue: number | null;
  favorable: string;
}

/** Single period of variance data from the API */
export interface VariancePeriod {
  period: string;
  vs_budget: LineVariance[] | null;
  vs_prior_month: LineVariance[] | null;
  vs_prior_year: LineVariance[] | null;
}

export interface WCPeriod {
  period: string;
  dso: number | null;
  dpo: number | null;
  dio: number | null;
  ccc: number | null;
  wc_change: number | null;
  dso_cash_impact: number | null;
  ar_aging: Record<string, number> | null;
}

export interface FCFPeriod {
  period: string;
  free_cash_flow: number | null;
  cash_conversion_ratio: number | null;
  net_debt: number | null;
  ltm_ebitda: number | null;
  net_debt_to_ltm_ebitda: number | null;
}

export interface TrendFlag {
  metric: string;
  flag_type: string;
  severity: string;
  current_value: number | null;
  period: string | null;
  detail: string;
}

export interface PeerCompany {
  name: string;
  ticker: string;
  revenue: number | null;
  gross_margin_pct: number | null;
  ebitda_margin_pct: number | null;
  revenue_growth_yoy_pct: number | null;
  ev_to_ebitda: number | null;
}

export interface GapAnalysis {
  metric: string;
  company_value: number;
  peer_median: number;
  gap: number;
  opportunity: string;
}

export interface SizedInitiative {
  name: string;
  category: string;
  description: string;
  ebitda_impact_annual: number;
  implementation_cost: number;
  timeline_months: number;
  confidence: string;
  specific_tools: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AnalysisData {
  ltm: LTMMetrics | null;
  ebitda_bridges: EBITDABridgesResponse | null;
  margins: { periods: Margins[]; as_dataframe?: Record<string, unknown>[] } | null;
  variance: { periods: VariancePeriod[] } | null;
  working_capital: { periods: WCPeriod[] } | null;
  fcf: { periods: FCFPeriod[] } | null;
  trends: { flags: TrendFlag[] } | null;
  modules_run: string[];
}

export interface SessionData {
  session_id: string;
  company_name: string;
  sector: string;
  analysis: AnalysisData;
  assumptions: Record<string, number> | null;
  returns: Returns | null;
}

export interface ResearchData {
  peers: PeerCompany[];
  gap_analysis: GapAnalysis[];
}

export interface ValueCreationData {
  total_opportunity: number;
  initiatives: SizedInitiative[];
}
