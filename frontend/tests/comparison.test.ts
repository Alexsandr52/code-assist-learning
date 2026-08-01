import { describe, expect, it } from "vitest";
import { calculateAccuracy, compareCode, isExactMatch } from "../lib/typing/comparison";

describe("typing comparison", () => {
  it("requires exact characters by default", () => {
    const result = compareCode("print(\"ok\")", "print('ok')");
    expect(result.exact).toBe(false);
    expect(result.statuses).toContain("incorrect");
  });

  it("allows one optional final newline", () => {
    expect(isExactMatch("import requests", "import requests\n")).toBe(true);
  });

  it("marks extra characters", () => {
    const result = compareCode("abc", "abcd");
    expect(result.exact).toBe(false);
    expect(result.extraStatuses).toEqual(["extra"]);
  });

  it("calculates one-decimal accuracy", () => {
    expect(calculateAccuracy(2, 3)).toBe(66.7);
  });
});

