import { afterEach, describe, expect, it, vi } from "vitest";
import { createAnonymousSessionId, getAnonymousSessionId } from "../lib/typing/storage";

describe("typing storage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses crypto.randomUUID when the browser provides it", () => {
    expect(createAnonymousSessionId({ randomUUID: () => "stable-id" })).toBe("anon_stable-id");
  });

  it("creates a UUID fallback when crypto.randomUUID is unavailable", () => {
    const randomSource = {
      getRandomValues<T extends ArrayBufferView | null>(array: T): T {
        if (array instanceof Uint8Array) {
          for (let index = 0; index < array.length; index += 1) {
            array[index] = index;
          }
        }
        return array;
      }
    };

    expect(createAnonymousSessionId(randomSource)).toBe("anon_00010203-0405-4607-8809-0a0b0c0d0e0f");
  });

  it("does not fail when localStorage is unavailable", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: () => {
          throw new Error("localStorage blocked");
        },
        setItem: () => {
          throw new Error("localStorage blocked");
        }
      }
    });

    const firstId = getAnonymousSessionId();
    const secondId = getAnonymousSessionId();

    expect(firstId).toMatch(/^anon_/);
    expect(secondId).toBe(firstId);
  });
});
