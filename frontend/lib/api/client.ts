import type { Difficulty, Language, Library, PracticeSession, Topic } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const REQUEST_TIMEOUT_MS = 25000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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
  assertPracticeSessionInput(input);
  const body = JSON.stringify(input);
  console.info("Sending practice session request", {
    bodyLength: body.length,
    input
  });
  return request<PracticeSession>("/api/practice-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body
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
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal
    });
    if (!response.ok) {
      const detail = await readErrorDetail(response);
      throw new ApiError(`API request failed: ${response.status}`, response.status, detail);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("API request timed out", 408, "Запрос к backend занял слишком много времени.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function readErrorDetail(response: Response): Promise<string | undefined> {
  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = await response.json() as { detail?: unknown };
      return typeof payload.detail === "string" ? payload.detail : undefined;
    }
    const text = await response.text();
    return text || undefined;
  } catch {
    return undefined;
  }
}

function assertPracticeSessionInput(input: {
  language: string;
  library: string;
  topic: string;
  difficulty: Difficulty;
  anonymousSessionId: string;
}): void {
  if (!input.language || !input.library || !input.topic || !input.difficulty || !input.anonymousSessionId) {
    throw new ApiError("Practice session request is incomplete", 400, "Фронтенд сформировал неполный запрос на создание урока.");
  }
}
