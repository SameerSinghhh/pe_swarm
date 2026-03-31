import { SessionData, ResearchData, ValueCreationData } from './types';

const API = 'http://localhost:8000';

export async function loadDemo(key: string): Promise<SessionData> {
  const res = await fetch(`${API}/demo/${key}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to load demo: ${res.statusText}`);
  return res.json();
}

export async function updateModel(
  sessionId: string,
  changes: Record<string, number>
): Promise<SessionData> {
  const res = await fetch(`${API}/session/${sessionId}/assumptions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  });
  if (!res.ok) throw new Error(`Failed to update model: ${res.statusText}`);
  return res.json();
}

export async function sendChat(
  sessionId: string,
  message: string
): Promise<string> {
  const res = await fetch(`${API}/session/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`Failed to send chat: ${res.statusText}`);
  const data = await res.json();
  return data.response || data.message || JSON.stringify(data);
}

export async function runResearch(
  sessionId: string
): Promise<ResearchData> {
  const res = await fetch(`${API}/session/${sessionId}/research`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to run research: ${res.statusText}`);
  return res.json();
}

export async function runValueCreation(
  sessionId: string
): Promise<ValueCreationData> {
  const res = await fetch(`${API}/session/${sessionId}/value-creation`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to run value creation: ${res.statusText}`);
  return res.json();
}

export function getExcelUrl(sessionId: string): string {
  return `${API}/session/${sessionId}/excel`;
}
