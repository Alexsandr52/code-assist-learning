"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  completePracticeSession,
  createPracticeSession,
  fetchLanguages,
  fetchLibraries,
  fetchTopics
} from "@/lib/api/client";
import { mockLanguages, mockLibraries, mockSession, mockTopics } from "@/lib/api/mock";
import type { Difficulty, Language, Library, PracticeSession, Topic } from "@/lib/api/types";
import { calculateAccuracy, compareCode } from "@/lib/typing/comparison";
import {
  clearPracticeState,
  getAnonymousSessionId,
  loadPracticeState,
  savePracticeState
} from "@/lib/typing/storage";

const difficulties: Difficulty[] = ["beginner", "intermediate", "advanced"];
const difficultyLabels: Record<Difficulty, string> = {
  beginner: "Начальный",
  intermediate: "Средний",
  advanced: "Сложный"
};

type CompletionSummary = {
  accuracy: number;
  pasteAttempts: number;
};

type FooterPanel = "author" | "coffee" | "about" | null;

export function PracticeApp() {
  const [languages, setLanguages] = useState<Language[]>(mockLanguages);
  const [libraries, setLibraries] = useState<Library[]>(mockLibraries);
  const [topics, setTopics] = useState<Topic[]>(mockTopics);
  const [language, setLanguage] = useState("python");
  const [library, setLibrary] = useState("requests");
  const [topic, setTopic] = useState("get-requests");
  const [difficulty, setDifficulty] = useState<Difficulty>("beginner");
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [blockIndex, setBlockIndex] = useState(0);
  const [typedText, setTypedText] = useState("");
  const [correctKeystrokes, setCorrectKeystrokes] = useState(0);
  const [totalKeystrokes, setTotalKeystrokes] = useState(0);
  const [pasteAttempts, setPasteAttempts] = useState(0);
  const [startedAt, setStartedAt] = useState(Date.now());
  const [showExplanation, setShowExplanation] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [showSolution, setShowSolution] = useState(false);
  const [notice, setNotice] = useState("");
  const [catalogNotice, setCatalogNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCatalogLoading, setIsCatalogLoading] = useState(false);
  const [completionSummary, setCompletionSummary] = useState<CompletionSummary | null>(null);
  const [footerPanel, setFooterPanel] = useState<FooterPanel>(null);

  useEffect(() => {
    const stored = loadPracticeState();
    if (stored) {
      setSession(stored.session);
      setBlockIndex(stored.blockIndex);
      setTypedText(stored.typedText);
      setCorrectKeystrokes(stored.correctKeystrokes);
      setTotalKeystrokes(stored.totalKeystrokes);
      setPasteAttempts(stored.pasteAttempts);
      setStartedAt(stored.startedAt);
    }
  }, []);

  useEffect(() => {
    void fetchLanguages()
      .then((items) => {
        setLanguages(items);
        setCatalogNotice("");
      })
      .catch(() => {
        setLanguages(mockLanguages);
        setCatalogNotice("Backend недоступен, каталог открыт из локального mock.");
      });
  }, []);

  useEffect(() => {
    let isCurrent = true;
    void fetchLibraries(language)
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setLibraries(items);
        setCatalogNotice("");
      })
      .catch(() => {
        if (!isCurrent) {
          return;
        }
        setLibraries(mockLibraries);
        setCatalogNotice("Backend недоступен, библиотеки открыты из локального mock.");
      });
    return () => {
      isCurrent = false;
    };
  }, [language]);

  useEffect(() => {
    let isCurrent = true;
    setIsCatalogLoading(true);
    setTopics([]);
    setTopic("");
    void fetchTopics(library, difficulty)
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setTopics(items);
        setCatalogNotice("");
      })
      .catch(() => {
        if (!isCurrent) {
          return;
        }
        setTopics([]);
        setCatalogNotice("Для выбранной библиотеки и сложности пока нет активных тем.");
      })
      .finally(() => {
        if (isCurrent) {
          setIsCatalogLoading(false);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [library, difficulty]);

  useEffect(() => {
    if (libraries.length > 0 && !libraries.some((item) => item.slug === library)) {
      setLibrary(libraries[0].slug);
    }
  }, [libraries, library]);

  useEffect(() => {
    if (topics.length === 0) {
      setTopic("");
      return;
    }
    if (!topics.some((item) => item.slug === topic)) {
      setTopic(topics[0].slug);
    }
  }, [topics, topic]);

  useEffect(() => {
    if (!session) {
      return;
    }
    savePracticeState({
      session,
      blockIndex,
      typedText,
      correctKeystrokes,
      totalKeystrokes,
      pasteAttempts,
      startedAt
    });
  }, [session, blockIndex, typedText, correctKeystrokes, totalKeystrokes, pasteAttempts, startedAt]);

  const currentBlock = session?.blocks[blockIndex] ?? null;
  const comparison = useMemo(
    () => compareCode(currentBlock?.code ?? "", typedText),
    [currentBlock?.code, typedText]
  );
  const accuracy = calculateAccuracy(correctKeystrokes, totalKeystrokes);
  const isTrainingDone = Boolean(session && blockIndex >= session.blocks.length);
  const selectedTopic = useMemo(
    () => topics.find((item) => item.slug === topic && item.library === library && item.difficulty === difficulty) ?? null,
    [difficulty, library, topic, topics]
  );
  const isStartDisabled = isLoading || isCatalogLoading || !selectedTopic;

  async function startPractice() {
    if (!selectedTopic) {
      setNotice(isCatalogLoading ? "Темы загружаются, подождите несколько секунд." : "Выберите тему перед стартом практики.");
      return;
    }
    setIsLoading(true);
    setNotice("");
    try {
      const created = await createPracticeSession({
        language,
        library,
        topic: selectedTopic.slug,
        difficulty,
        anonymousSessionId: getAnonymousSessionId()
      });
      beginSession(created);
    } catch (error) {
      beginSession(mockSession);
      if (error instanceof ApiError) {
        setNotice(`Backend ответил ${error.status}: ${error.detail ?? "открыт локальный fallback-урок."}`);
      } else {
        setNotice("Backend недоступен, открыт локальный fallback-урок.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  function beginSession(nextSession: PracticeSession) {
    setSession(nextSession);
    setBlockIndex(0);
    setTypedText("");
    setCorrectKeystrokes(0);
    setTotalKeystrokes(0);
    setPasteAttempts(0);
    setStartedAt(Date.now());
    setShowExplanation(false);
    setShowHint(false);
    setShowSolution(false);
    setCompletionSummary(null);
  }

  function handleTextChange(value: string) {
    const previous = typedText;
    setTypedText(value);
    if (value.length > previous.length) {
      const expected = currentBlock?.code ?? "";
      const added = value.slice(previous.length);
      let correctAdded = 0;
      for (let index = 0; index < added.length; index += 1) {
        const absoluteIndex = previous.length + index;
        if (added[index] === expected[absoluteIndex]) {
          correctAdded += 1;
        }
      }
      setCorrectKeystrokes((count) => count + correctAdded);
      setTotalKeystrokes((count) => count + added.length);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Tab") {
      event.preventDefault();
      const target = event.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      handleTextChange(`${typedText.slice(0, start)}    ${typedText.slice(end)}`);
      requestAnimationFrame(() => {
        target.selectionStart = start + 4;
        target.selectionEnd = start + 4;
      });
      return;
    }

    if (event.key === "Enter" && currentBlock && comparison.exact) {
      event.preventDefault();
      goNext();
    }
  }

  function handlePaste(event: React.ClipboardEvent<HTMLTextAreaElement>) {
    event.preventDefault();
    setPasteAttempts((count) => count + 1);
    setNotice("Вставка отключена в режиме ручной тренировки.");
  }

  function goNext() {
    if (!session) {
      return;
    }
    setTypedText("");
    setShowExplanation(false);
    setNotice("");
    setBlockIndex((index) => Math.min(index + 1, session.blocks.length));
  }

  async function completeSession() {
    if (!session) {
      return;
    }
    const summary = { accuracy, pasteAttempts };
    try {
      await completePracticeSession(session.sessionId, {
        accuracy,
        durationMs: Date.now() - startedAt,
        pasteAttempts
      });
    } catch {
      setNotice("Сессия завершена локально; backend не подтвердил сохранение.");
    }
    clearPracticeState();
    setCompletionSummary(summary);
    setSession(null);
    setBlockIndex(0);
    setTypedText("");
    setShowHint(false);
    setShowSolution(false);
  }

  function resetSession() {
    setSession(null);
    setBlockIndex(0);
    setTypedText("");
    setCompletionSummary(null);
    setShowHint(false);
    setShowSolution(false);
    setNotice("");
    clearPracticeState();
  }

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <h1 className="brand">Code Learn Assist</h1>
            <div className="subtle">Ручная практика синтаксиса Python-библиотек</div>
          </div>
          {session ? <button className="secondary" onClick={resetSession}>Новая тема</button> : null}
        </header>

        <div className="layout">
          <aside className="panel selector">
            <ChoiceGroup label="Язык" value={language} onChange={setLanguage} options={languages.map(toOption)} variant="segmented" />
            <ChoiceGroup label="Библиотека" value={library} onChange={setLibrary} options={libraries.map(toOption)} />
            <ChoiceGroup
              label="Сложность"
              value={difficulty}
              onChange={(value) => setDifficulty(value as Difficulty)}
              options={difficulties.map((item) => ({ value: item, label: difficultyLabels[item] }))}
              variant="segmented"
            />
            <ChoiceGroup
              label="Тема"
              value={topic}
              onChange={setTopic}
              options={topics.map(toOption)}
              emptyLabel="Нет активных тем"
              variant="topics"
            />
            <button className="primary" disabled={isStartDisabled} onClick={startPractice}>
              {isLoading || isCatalogLoading ? "Загрузка..." : "Начать практику"}
            </button>
            {isLoading || isCatalogLoading ? <LoadingPanel /> : null}
            {catalogNotice ? <div className="subtle">{catalogNotice}</div> : null}
            {notice ? <div className="notice">{notice}</div> : null}
          </aside>

          <section className="practice">
            {!session ? <EmptyState /> : null}
            {session && currentBlock && !isTrainingDone ? (
              <Trainer
                session={session}
                blockIndex={blockIndex}
                typedText={typedText}
                comparison={comparison}
                accuracy={accuracy}
                pasteAttempts={pasteAttempts}
                showExplanation={showExplanation}
                onToggleExplanation={() => setShowExplanation((value) => !value)}
                onTextChange={handleTextChange}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                onSkip={goNext}
                onSkipToExercise={() => {
                  if (session) {
                    setTypedText("");
                    setBlockIndex(session.blocks.length);
                  }
                }}
              />
            ) : null}
            {session && isTrainingDone ? (
              <ExerciseView
                session={session}
                accuracy={accuracy}
                pasteAttempts={pasteAttempts}
                showHint={showHint}
                showSolution={showSolution}
                onToggleHint={() => setShowHint((value) => !value)}
                onToggleSolution={() => setShowSolution((value) => !value)}
                onComplete={completeSession}
              />
            ) : null}
            {completionSummary ? (
              <CompletedView
                accuracy={completionSummary.accuracy}
                pasteAttempts={completionSummary.pasteAttempts}
                onNewSession={resetSession}
              />
            ) : null}
          </section>
        </div>
        <FooterActions activePanel={footerPanel} onSelect={setFooterPanel} />
      </div>
    </main>
  );
}

function Trainer(props: {
  session: PracticeSession;
  blockIndex: number;
  typedText: string;
  comparison: ReturnType<typeof compareCode>;
  accuracy: number;
  pasteAttempts: number;
  showExplanation: boolean;
  onToggleExplanation: () => void;
  onTextChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onPaste: (event: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  onSkip: () => void;
  onSkipToExercise: () => void;
}) {
  const block = props.session.blocks[props.blockIndex];
  const blockProgress = Math.min(100, Math.round((props.typedText.length / block.code.length) * 100));
  return (
    <>
      <div className="panel">
        <div className="meta">
          <span className="badge">{props.session.library}</span>
          <span className="badge">{props.session.topic}</span>
          <span className="badge">Источник: {props.session.source}</span>
          <span className="badge">Блок {props.blockIndex + 1} из {props.session.blocks.length}</span>
        </div>
        <h2>{block.title}</h2>
        <LinearProgress value={blockProgress} label="Набрано символов" />
        <div className="stats">
          <div className="stat">Прогресс<strong>{Math.round(((props.blockIndex + Number(props.comparison.exact)) / props.session.blocks.length) * 100)}%</strong></div>
          <div className="stat">Точность<strong>{props.accuracy}%</strong></div>
          <div className="stat">Попытки paste<strong>{props.pasteAttempts}</strong></div>
        </div>
      </div>

      <div className="typingSurface">
        <pre className="typingGhost" aria-hidden="true">{block.code}</pre>
        <pre className="typingOverlay" aria-hidden="true">{renderTypedOverlay(block.code, props.typedText, props.comparison)}</pre>
        <textarea
          className="typingInput"
          value={props.typedText}
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          inputMode="text"
          aria-label="Область ручного ввода кода"
          onChange={(event) => props.onTextChange(event.target.value)}
          onKeyDown={props.onKeyDown}
          onPaste={props.onPaste}
          autoFocus
        />
      </div>

      <div className="panel actions">
        <button className="secondary" onClick={props.onToggleExplanation}>Пояснение</button>
        <button className="secondary" onClick={props.onSkip}>Пропустить блок</button>
        <button className="secondary" onClick={props.onSkipToExercise}>К заданию</button>
        {props.comparison.exact ? <span className="badge">Блок набран верно. Нажмите Enter.</span> : null}
        {props.showExplanation ? <span className="subtle">{block.explanation}</span> : null}
      </div>
    </>
  );
}

function ExerciseView(props: {
  session: PracticeSession;
  accuracy: number;
  pasteAttempts: number;
  showHint: boolean;
  showSolution: boolean;
  onToggleHint: () => void;
  onToggleSolution: () => void;
  onComplete: () => void;
}) {
  return (
    <div className="panel exercise">
      <div className="meta">
        <span className="badge">{props.session.library}</span>
        <span className="badge">Точность: {props.accuracy}%</span>
        <span className="badge">Paste: {props.pasteAttempts}</span>
      </div>
      <h2>Практическое задание</h2>
      <p>{props.session.exercise.description}</p>
      <textarea className="textarea" defaultValue={props.session.exercise.starterCode} spellCheck={false} />
      <div className="actions">
        <button className="secondary" onClick={props.onToggleHint}>Подсказка</button>
        <button className="secondary" onClick={props.onToggleSolution}>Решение</button>
        <button className="primary" onClick={props.onComplete}>Завершить сессию</button>
      </div>
      {props.showHint ? <div className="inlineNote">{props.session.exercise.hint}</div> : null}
      {props.showSolution ? (
        <div className="codeBox">
          <pre>{props.session.exercise.solution}</pre>
        </div>
      ) : null}
    </div>
  );
}

function CompletedView(props: {
  accuracy: number;
  pasteAttempts: number;
  onNewSession: () => void;
}) {
  return (
    <div className="panel completion">
      <div className="meta">
        <span className="badge">Сессия завершена</span>
        <span className="badge">Точность: {props.accuracy}%</span>
        <span className="badge">Paste: {props.pasteAttempts}</span>
      </div>
      <h2>Готово</h2>
      <p className="subtle">Прогресс зафиксирован. Можно выбрать новую тему и продолжить практику.</p>
      <button className="primary" onClick={props.onNewSession}>Выбрать новую тему</button>
    </div>
  );
}

function FooterActions(props: {
  activePanel: FooterPanel;
  onSelect: (panel: FooterPanel) => void;
}) {
  const toggle = (panel: Exclude<FooterPanel, null>) => {
    props.onSelect(props.activePanel === panel ? null : panel);
  };

  return (
    <footer className="footerPanel">
      <div className="footerActions">
        <button className="secondary" onClick={() => toggle("author")}>Автор</button>
        <button className="secondary" onClick={() => toggle("coffee")}>Купить мне кофе</button>
        <button className="secondary" onClick={() => toggle("about")}>Узнать меня лучше</button>
      </div>
      {props.activePanel ? <FooterDetails panel={props.activePanel} /> : null}
    </footer>
  );
}

function FooterDetails(props: { panel: Exclude<FooterPanel, null> }) {
  const content = {
    author: {
      title: "Автор",
      text: "Александр Полянский, автор MVP тренажёра ручного набора Python-кода. Контакт: @ak_polyanskiy."
    },
    coffee: {
      title: "Купить мне кофе",
      text: "Что вы ждали? Платежку? А может стоит меня сводить на кофе куда-нибудь?"
    },
    about: {
      title: "Узнать меня лучше",
      text: "angel-save-me.ru."
    }
  }[props.panel];

  return (
    <div className="footerDetails">
      <strong>{content.title}</strong>
      <span>{content.text}</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="panel">
      <h2>Выберите параметры и начните практику</h2>
      <p className="subtle">В MVP поддерживается Python. Код не выполняется на сервере, тренировка проверяет только точность ручного набора.</p>
    </div>
  );
}

function ChoiceGroup(props: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
  emptyLabel?: string;
  variant?: "cards" | "segmented" | "topics";
}) {
  const hasOptions = props.options.length > 0;
  const className = props.variant === "segmented" ? "choiceGroup segmented" : props.variant === "topics" ? "choiceGroup topicChoices" : "choiceGroup";
  return (
    <div className="field">
      <label>{props.label}</label>
      <div className={className} role="listbox" aria-label={props.label}>
        {hasOptions ? (
          props.options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={option.value === props.value ? "choice active" : "choice"}
              aria-selected={option.value === props.value}
              onClick={() => props.onChange(option.value)}
            >
              {option.label}
            </button>
          ))
        ) : (
          <div className="emptyChoice">{props.emptyLabel ?? "Нет вариантов"}</div>
        )}
      </div>
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="loadingPanel" role="status" aria-live="polite">
      <div className="loadingTitle">Генерация урока</div>
      <div className="subtle">Проверяем кэш, базу и при необходимости ждём YandexGPT.</div>
      <div className="indeterminateBar" aria-hidden="true">
        <span />
      </div>
    </div>
  );
}

function LinearProgress(props: { value: number; label: string }) {
  return (
    <div className="linearProgress" aria-label={`${props.label}: ${props.value}%`}>
      <div className="progressHeader">
        <span>{props.label}</span>
        <span>{props.value}%</span>
      </div>
      <div className="progressTrack">
        <span style={{ width: `${props.value}%` }} />
      </div>
    </div>
  );
}

function toOption(item: { slug: string; name: string }) {
  return { value: item.slug, label: item.name };
}

function renderTypedOverlay(expected: string, typed: string, comparison: ReturnType<typeof compareCode>) {
  const chars = [...typed.slice(0, expected.length)].map((char, index) => (
    <span key={`typed-${index}`} className={`char ${comparison.statuses[index] === "correct" ? "correct" : "incorrect"}`}>
      {char === "\n" ? "\n" : char}
    </span>
  ));
  const extras = typed.slice(expected.length).split("").map((char, index) => (
    <span key={`extra-${index}`} className="char extra">{char}</span>
  ));
  return [...chars, ...extras];
}
