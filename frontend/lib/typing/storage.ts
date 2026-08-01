import type { PracticeSession } from "@/lib/api/types";

const ANON_KEY = "cla:anonymous-session-id";
const PRACTICE_KEY = "cla:practice-state";

export type StoredPracticeState = {
  session: PracticeSession;
  blockIndex: number;
  typedText: string;
  correctKeystrokes: number;
  totalKeystrokes: number;
  pasteAttempts: number;
  startedAt: number;
};

export function getAnonymousSessionId(): string {
  if (typeof window === "undefined") {
    return "anonymous-server";
  }
  const existing = window.localStorage.getItem(ANON_KEY);
  if (existing) {
    return existing;
  }
  const created = `anon_${crypto.randomUUID()}`;
  window.localStorage.setItem(ANON_KEY, created);
  return created;
}

export function savePracticeState(state: StoredPracticeState): void {
  window.localStorage.setItem(PRACTICE_KEY, JSON.stringify(state));
}

export function loadPracticeState(): StoredPracticeState | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(PRACTICE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as StoredPracticeState;
  } catch {
    window.localStorage.removeItem(PRACTICE_KEY);
    return null;
  }
}

export function clearPracticeState(): void {
  window.localStorage.removeItem(PRACTICE_KEY);
}

