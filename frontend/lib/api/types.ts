export type Difficulty = "beginner" | "intermediate" | "advanced";
export type ContentSource = "cache" | "database" | "generated" | "fallback";

export type Language = {
  id: string;
  name: string;
  slug: string;
};

export type Library = {
  id: string;
  language: string;
  name: string;
  slug: string;
  description: string;
};

export type Topic = {
  id: string;
  library: string;
  name: string;
  slug: string;
  difficulty: Difficulty;
};

export type CodeBlock = {
  title: string;
  code: string;
  explanation: string;
};

export type Exercise = {
  description: string;
  starterCode: string;
  hint: string;
  solution: string;
};

export type PracticeSession = {
  sessionId: string;
  source: ContentSource;
  language: string;
  library: string;
  topic: string;
  difficulty: Difficulty;
  blocks: CodeBlock[];
  exercise: Exercise;
};

