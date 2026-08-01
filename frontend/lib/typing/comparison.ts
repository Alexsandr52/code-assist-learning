export type CharStatus = "correct" | "incorrect" | "pending" | "extra";

export type ComparisonResult = {
  exact: boolean;
  statuses: CharStatus[];
  extraStatuses: CharStatus[];
  correctChars: number;
};

export function stripOptionalFinalNewline(value: string): string {
  return value.endsWith("\n") ? value.slice(0, -1) : value;
}

export function isExactMatch(expected: string, typed: string): boolean {
  return stripOptionalFinalNewline(expected) === stripOptionalFinalNewline(typed);
}

export function compareCode(expected: string, typed: string): ComparisonResult {
  const normalizedExpected = stripOptionalFinalNewline(expected);
  const normalizedTyped = stripOptionalFinalNewline(typed);
  const statuses: CharStatus[] = [];
  let correctChars = 0;

  for (let index = 0; index < normalizedExpected.length; index += 1) {
    const expectedChar = normalizedExpected[index];
    const typedChar = normalizedTyped[index];
    if (typedChar === undefined) {
      statuses.push("pending");
    } else if (typedChar === expectedChar) {
      statuses.push("correct");
      correctChars += 1;
    } else {
      statuses.push("incorrect");
    }
  }

  const extraCount = Math.max(0, normalizedTyped.length - normalizedExpected.length);
  return {
    exact: normalizedExpected === normalizedTyped,
    statuses,
    extraStatuses: Array.from({ length: extraCount }, () => "extra"),
    correctChars
  };
}

export function calculateAccuracy(correctKeystrokes: number, totalKeystrokes: number): number {
  if (totalKeystrokes === 0) {
    return 100;
  }
  return Math.round((correctKeystrokes / totalKeystrokes) * 1000) / 10;
}

