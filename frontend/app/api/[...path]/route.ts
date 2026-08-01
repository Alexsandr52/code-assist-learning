import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";

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

  try {
    const response = await fetch(target, {
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
