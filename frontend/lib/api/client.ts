import type { Difficulty, Language, Library, PracticeSession, Topic } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function fetchLanguages(): Promise<Language[]> {
  return request<Language[]>("/api/languages");
}

export async function fetchLibraries(language: string): Promise<Library[]> {
  return request<Library[]>(`/api/libraries?language=${encodeURIComponent(language)}`);
}

export async function fetchTopics(library: string, difficulty: Difficulty): Promise<Topic[]> {
  return request<Topic[]>(`/api/topics?library=${encodeURIComponent(library)}&difficulty=${difficulty}`);
}

export async function createPracticeSession(input: {
  language: string;
  library: string;
  topic: string;
  difficulty: Difficulty;
  anonymousSessionId: string;
}): Promise<PracticeSession> {
  return request<PracticeSession>("/api/practice-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
}

export async function completePracticeSession(sessionId: string, stats: {
  accuracy: number;
  durationMs: number;
  pasteAttempts: number;
}): Promise<void> {
  await request(`/api/practice-sessions/${sessionId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(stats)
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
