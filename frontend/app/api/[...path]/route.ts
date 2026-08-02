import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";
const BACKEND_PROXY_ATTEMPTS = 5;
const BACKEND_PROXY_RETRY_DELAY_MS = 500;

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const url = new URL(request.url);
  const target = `${BACKEND_URL}/api/${path.join("/")}${url.search}`;
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  const bodyLength = body?.length ?? 0;

  if (request.method !== "GET" && request.method !== "HEAD" && bodyLength === 0) {
    console.error("Backend proxy received an empty request body", {
      method: request.method,
      target,
      path
    });
    return NextResponse.json({ detail: "Frontend sent an empty request body" }, { status: 400 });
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    console.info("Backend proxy forwarding request body", {
      method: request.method,
      target,
      bodyLength
    });
  }

  try {
    const response = await fetchBackend(target, {
      method: request.method,
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json"
      },
      body,
      cache: "no-store"
    });

    const responseBody = await response.text();
    if (!response.ok) {
      console.error("Backend proxy returned an error", {
        method: request.method,
        target,
        status: response.status,
        body: responseBody
      });
    }
    return new NextResponse(responseBody, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json"
      }
    });
  } catch (error) {
    console.error("Backend proxy request failed", {
      method: request.method,
      target,
      error
    });
    return NextResponse.json({ detail: "Backend is unavailable" }, { status: 502 });
  }
}

async function fetchBackend(target: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= BACKEND_PROXY_ATTEMPTS; attempt += 1) {
    try {
      return await fetch(target, init);
    } catch (error) {
      lastError = error;
      if (attempt === BACKEND_PROXY_ATTEMPTS) {
        break;
      }
      console.warn("Backend proxy request failed; retrying", {
        target,
        attempt,
        nextAttemptInMs: BACKEND_PROXY_RETRY_DELAY_MS,
        error
      });
      await sleep(BACKEND_PROXY_RETRY_DELAY_MS);
    }
  }
  throw lastError;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
