import type { PracticeSession } from "@/lib/api/types";

const ANON_KEY = "cla:anonymous-session-id";
const PRACTICE_KEY = "cla:practice-state";
const UUID_BYTE_LENGTH = 16;

let inMemoryAnonymousSessionId: string | null = null;

type RandomSource = {
  randomUUID?: () => string;
  getRandomValues?: <T extends ArrayBufferView | null>(array: T) => T;
};

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

  try {
    const existing = window.localStorage.getItem(ANON_KEY);
    if (existing) {
      return existing;
    }
    const created = createAnonymousSessionId();
    window.localStorage.setItem(ANON_KEY, created);
    return created;
  } catch {
    if (!inMemoryAnonymousSessionId) {
      inMemoryAnonymousSessionId = createAnonymousSessionId();
    }
    return inMemoryAnonymousSessionId;
  }
}

export function createAnonymousSessionId(randomSource: RandomSource | undefined = getRandomSource()): string {
  if (typeof randomSource?.randomUUID === "function") {
    return `anon_${randomSource.randomUUID()}`;
  }
  if (typeof randomSource?.getRandomValues === "function") {
    return `anon_${createUuidFromRandomValues(randomSource)}`;
  }
  return `anon_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

function getRandomSource(): RandomSource | undefined {
  return typeof globalThis.crypto === "object" ? globalThis.crypto : undefined;
}

function createUuidFromRandomValues(randomSource: RandomSource): string {
  const bytes = new Uint8Array(UUID_BYTE_LENGTH);
  randomSource.getRandomValues?.(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join("")
  ].join("-");
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
