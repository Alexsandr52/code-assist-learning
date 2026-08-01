import type { Language, Library, PracticeSession, Topic } from "./types";

export const mockLanguages: Language[] = [{ id: "lang_python", name: "Python", slug: "python" }];

export const mockLibraries: Library[] = [
  { id: "lib_requests", language: "python", name: "requests", slug: "requests", description: "HTTP-запросы" },
  { id: "lib_pandas", language: "python", name: "pandas", slug: "pandas", description: "Таблицы и анализ данных" },
  { id: "lib_numpy", language: "python", name: "numpy", slug: "numpy", description: "Массивы и вычисления" },
  { id: "lib_fastapi", language: "python", name: "FastAPI", slug: "fastapi", description: "HTTP API" },
  { id: "lib_bs4", language: "python", name: "BeautifulSoup", slug: "beautifulsoup", description: "Парсинг HTML" },
  { id: "lib_matplotlib", language: "python", name: "matplotlib", slug: "matplotlib", description: "Графики" },
  { id: "lib_sqlalchemy", language: "python", name: "SQLAlchemy", slug: "sqlalchemy", description: "ORM и SQL" }
];

export const mockTopics: Topic[] = [
  { id: "topic_requests_get_beginner", library: "requests", name: "GET-запросы", slug: "get-requests", difficulty: "beginner" },
  { id: "topic_requests_json_beginner", library: "requests", name: "JSON-ответы", slug: "json-responses", difficulty: "beginner" },
  { id: "topic_requests_post_intermediate", library: "requests", name: "POST-запросы", slug: "post-requests", difficulty: "intermediate" },
  { id: "topic_requests_retry_advanced", library: "requests", name: "Повторные попытки", slug: "retries", difficulty: "advanced" },
  { id: "topic_pandas_dataframe_beginner", library: "pandas", name: "Создание DataFrame", slug: "dataframes", difficulty: "beginner" },
  { id: "topic_pandas_groupby_intermediate", library: "pandas", name: "Группировка groupby", slug: "groupby", difficulty: "intermediate" },
  { id: "topic_pandas_pivot_advanced", library: "pandas", name: "Pivot tables", slug: "pivot-tables", difficulty: "advanced" },
  { id: "topic_numpy_arrays_beginner", library: "numpy", name: "Создание массивов", slug: "arrays", difficulty: "beginner" },
  { id: "topic_numpy_broadcasting_intermediate", library: "numpy", name: "Broadcasting", slug: "broadcasting", difficulty: "intermediate" },
  { id: "topic_numpy_linalg_advanced", library: "numpy", name: "Линейная алгебра", slug: "linear-algebra", difficulty: "advanced" },
  { id: "topic_fastapi_routes_beginner", library: "fastapi", name: "Маршруты", slug: "routes", difficulty: "beginner" },
  { id: "topic_fastapi_dependencies_intermediate", library: "fastapi", name: "Dependencies", slug: "dependencies", difficulty: "intermediate" },
  { id: "topic_fastapi_security_advanced", library: "fastapi", name: "OAuth2 и security", slug: "oauth2-security", difficulty: "advanced" },
  { id: "topic_bs4_find_beginner", library: "beautifulsoup", name: "Поиск элементов", slug: "find-elements", difficulty: "beginner" },
  { id: "topic_bs4_tree_intermediate", library: "beautifulsoup", name: "Навигация по дереву", slug: "tree-navigation", difficulty: "intermediate" },
  { id: "topic_bs4_robust_advanced", library: "beautifulsoup", name: "Устойчивый парсинг", slug: "robust-parsing", difficulty: "advanced" },
  { id: "topic_matplotlib_line_beginner", library: "matplotlib", name: "Линейный график", slug: "line-plot", difficulty: "beginner" },
  { id: "topic_matplotlib_subplots_intermediate", library: "matplotlib", name: "Несколько графиков", slug: "subplots", difficulty: "intermediate" },
  { id: "topic_matplotlib_axes_advanced", library: "matplotlib", name: "Axes API", slug: "axes-api", difficulty: "advanced" },
  { id: "topic_sqlalchemy_model_beginner", library: "sqlalchemy", name: "Модель таблицы", slug: "models", difficulty: "beginner" },
  { id: "topic_sqlalchemy_relationships_intermediate", library: "sqlalchemy", name: "Relationships", slug: "relationships", difficulty: "intermediate" },
  { id: "topic_sqlalchemy_async_advanced", library: "sqlalchemy", name: "Async SQLAlchemy", slug: "async-sqlalchemy", difficulty: "advanced" }
];

export const mockSession: PracticeSession = {
  sessionId: "session_local_fallback",
  source: "fallback",
  language: "python",
  library: "requests",
  topic: "GET-запросы",
  difficulty: "beginner",
  blocks: [
    {
      title: "Импорт библиотеки",
      code: "import requests",
      explanation: "Подключает requests для HTTP-запросов."
    },
    {
      title: "GET-запрос",
      code: "response = requests.get(\"https://example.com\")",
      explanation: "Отправляет GET-запрос и сохраняет ответ."
    },
    {
      title: "Код ответа",
      code: "print(response.status_code)",
      explanation: "Выводит HTTP-код ответа."
    }
  ],
  exercise: {
    description: "Отправьте GET-запрос на https://example.com и выведите код ответа.",
    starterCode: "import requests\n\n",
    hint: "Создайте response через requests.get, затем напечатайте status_code.",
    solution: "import requests\n\nresponse = requests.get(\"https://example.com\")\nprint(response.status_code)"
  }
};
