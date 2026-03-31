'use client';

import { useState, useCallback } from 'react';
import { Download, Loader2, Building2, ChevronDown } from 'lucide-react';
import { SessionData, ChatMessage, ResearchData, ValueCreationData } from '@/lib/types';
import { loadDemo, updateModel, sendChat, runResearch, runValueCreation, getExcelUrl } from '@/lib/api';
import MetricCards from '@/components/MetricCards';
import AnalysisTabs from '@/components/AnalysisTabs';
import Assumptions from '@/components/Assumptions';
import ChatPanel from '@/components/ChatPanel';
import ResearchPanel from '@/components/ResearchPanel';
import ValueCreation from '@/components/ValueCreation';

const DEMO_COMPANIES = [
  { key: 'meridian', name: 'Meridian Software', sector: 'B2B SaaS' },
  { key: 'atlas', name: 'Atlas Manufacturing', sector: 'Manufacturing' },
  { key: 'acme', name: 'Acme Corp', sector: 'B2B SaaS' },
];

export default function Home() {
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const [research, setResearch] = useState<ResearchData | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);

  const [valueCreation, setValueCreation] = useState<ValueCreationData | null>(null);
  const [vcLoading, setVcLoading] = useState(false);

  const [companyOpen, setCompanyOpen] = useState(false);

  const handleLoadDemo = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    setChatMessages([]);
    setResearch(null);
    setValueCreation(null);
    setCompanyOpen(false);
    try {
      const data = await loadDemo(key);
      setSession(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load demo data');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleUpdateAssumptions = useCallback(
    async (changes: Record<string, number>) => {
      if (!session) return;
      try {
        const data = await updateModel(session.session_id, changes);
        setSession(data);
      } catch (e: unknown) {
        console.error('Failed to update assumptions:', e);
      }
    },
    [session]
  );

  const handleSendChat = useCallback(
    async (message: string) => {
      if (!session) return;
      setChatMessages((prev) => [...prev, { role: 'user', content: message }]);
      setChatLoading(true);
      try {
        const response = await sendChat(session.session_id, message);
        setChatMessages((prev) => [...prev, { role: 'assistant', content: response }]);
      } catch (e: unknown) {
        setChatMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `Error: ${e instanceof Error ? e.message : 'Unknown error'}` },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [session]
  );

  const handleRunResearch = useCallback(async () => {
    if (!session) return;
    setResearchLoading(true);
    try {
      const data = await runResearch(session.session_id);
      setResearch(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Research failed');
    } finally {
      setResearchLoading(false);
    }
  }, [session]);

  const handleRunValueCreation = useCallback(async () => {
    if (!session) return;
    setVcLoading(true);
    try {
      const data = await runValueCreation(session.session_id);
      setValueCreation(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Value creation failed');
    } finally {
      setVcLoading(false);
    }
  }, [session]);

  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                  <Building2 className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-bold text-gray-900">PE Platform</span>
              </div>

              {/* Company selector */}
              <div className="relative ml-6">
                <button
                  onClick={() => setCompanyOpen(!companyOpen)}
                  className="flex items-center space-x-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                >
                  <span>{session?.company_name ?? 'Select Company'}</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
                {companyOpen && (
                  <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden z-50">
                    {DEMO_COMPANIES.map((co) => (
                      <button
                        key={co.key}
                        onClick={() => handleLoadDemo(co.key)}
                        className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-0"
                      >
                        <p className="text-sm font-medium text-gray-900">{co.name}</p>
                        <p className="text-xs text-gray-500">{co.sector}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {session && (
                <>
                  <span className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                    {session.sector ?? '—'}
                  </span>
                  <a
                    href={getExcelUrl(session.session_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Excel</span>
                  </a>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error state */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-xs text-red-500 underline mt-1"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-32">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-4" />
              <p className="text-sm text-gray-500">Loading analysis...</p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!session && !loading && (
          <div className="flex items-center justify-center py-32">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Building2 className="w-8 h-8 text-indigo-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                PE Value Creation Platform
              </h1>
              <p className="text-gray-500 mb-8">
                Select a portfolio company to view financial analysis, model scenarios, and identify value creation opportunities.
              </p>
              <div className="grid grid-cols-1 gap-3">
                {DEMO_COMPANIES.map((co) => (
                  <button
                    key={co.key}
                    onClick={() => handleLoadDemo(co.key)}
                    className="bg-white border border-gray-200 rounded-xl p-4 text-left hover:border-indigo-300 hover:shadow-md transition-all"
                  >
                    <p className="text-sm font-semibold text-gray-900">{co.name}</p>
                    <p className="text-xs text-gray-500">{co.sector}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Dashboard */}
        {session && !loading && (
          <div className="space-y-6">
            {/* Metric cards */}
            <MetricCards
              ltm={session.analysis?.ltm ?? null}
              returns={session.returns ?? null}
            />

            {/* Analysis tabs */}
            <AnalysisTabs analysis={session.analysis ?? null} />

            {/* Assumptions */}
            <Assumptions
              assumptions={session.assumptions ?? null}
              onUpdate={handleUpdateAssumptions}
            />

            {/* Two-column: Research + Value Creation */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ResearchPanel
                data={research}
                onRun={handleRunResearch}
                loading={researchLoading}
              />
              <ValueCreation
                data={valueCreation}
                onRun={handleRunValueCreation}
                loading={vcLoading}
              />
            </div>

            {/* Chat panel */}
            <ChatPanel
              messages={chatMessages}
              onSend={handleSendChat}
              loading={chatLoading}
              companyName={session.company_name ?? 'Company'}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-xs text-gray-400 text-center">
            PE Value Creation Platform &mdash; Financial analysis powered by deterministic math, AI reasoning on top.
          </p>
        </div>
      </footer>
    </div>
  );
}
