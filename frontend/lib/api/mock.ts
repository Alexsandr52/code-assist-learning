import type { Language, Library, PracticeSession, Topic } from "./types";

export const mockLanguages: Language[] = [
  { id: "lang_python", name: "Python", slug: "python" },
  { id: "lang_terminal", name: "Terminal", slug: "terminal" }
];

export const mockLibraries: Library[] = [
  { id: "lib_requests", language: "python", name: "requests", slug: "requests", description: "HTTP-запросы" },
  { id: "lib_pandas", language: "python", name: "pandas", slug: "pandas", description: "Таблицы и анализ данных" },
  { id: "lib_numpy", language: "python", name: "numpy", slug: "numpy", description: "Массивы и вычисления" },
  { id: "lib_fastapi", language: "python", name: "FastAPI", slug: "fastapi", description: "HTTP API" },
  { id: "lib_bs4", language: "python", name: "BeautifulSoup", slug: "beautifulsoup", description: "Парсинг HTML" },
  { id: "lib_matplotlib", language: "python", name: "matplotlib", slug: "matplotlib", description: "Графики" },
  { id: "lib_sqlalchemy", language: "python", name: "SQLAlchemy", slug: "sqlalchemy", description: "ORM и SQL" },
  { id: "lib_re", language: "python", name: "re", slug: "re", description: "Регулярные выражения" },
  { id: "lib_linux", language: "terminal", name: "Linux", slug: "linux", description: "Команды, файлы, процессы и диагностика" },
  { id: "lib_git", language: "terminal", name: "Git", slug: "git", description: "Контроль версий в терминале" },
  { id: "lib_conda", language: "terminal", name: "Conda", slug: "conda", description: "Окружения и зависимости" },
  { id: "lib_docker", language: "terminal", name: "Docker", slug: "docker", description: "Контейнеры и Docker Compose" }
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
  { id: "topic_sqlalchemy_async_advanced", library: "sqlalchemy", name: "Async SQLAlchemy", slug: "async-sqlalchemy", difficulty: "advanced" },
  { id: "topic_re_functions_beginner", library: "re", name: "Выбор функции re", slug: "regex-functions", difficulty: "beginner" },
  { id: "topic_re_classes_beginner", library: "re", name: "Символьные классы", slug: "character-classes", difficulty: "beginner" },
  { id: "topic_re_quantifiers_beginner", library: "re", name: "Квантификаторы", slug: "quantifiers", difficulty: "beginner" },
  { id: "topic_re_anchors_beginner", library: "re", name: "Якоря и границы слов", slug: "anchors-boundaries", difficulty: "beginner" },
  { id: "topic_re_groups_intermediate", library: "re", name: "Группы и извлечение", slug: "groups-extraction", difficulty: "intermediate" },
  { id: "topic_re_iteration_intermediate", library: "re", name: "findall и finditer", slug: "findall-finditer", difficulty: "intermediate" },
  { id: "topic_re_split_sub_intermediate", library: "re", name: "split и sub", slug: "split-sub", difficulty: "intermediate" },
  { id: "topic_re_flags_intermediate", library: "re", name: "Флаги поиска", slug: "flags", difficulty: "intermediate" },
  { id: "topic_re_named_advanced", library: "re", name: "Именованные группы", slug: "named-groups", difficulty: "advanced" },
  { id: "topic_re_backrefs_advanced", library: "re", name: "Обратные ссылки", slug: "backreferences", difficulty: "advanced" },
  { id: "topic_re_logs_advanced", library: "re", name: "Парсинг логов", slug: "log-parsing", difficulty: "advanced" },
  { id: "topic_re_cleanup_advanced", library: "re", name: "Очистка и преобразование", slug: "cleanup-pipelines", difficulty: "advanced" },
  { id: "topic_linux_basics_beginner", library: "linux", name: "Основы Linux", slug: "linux-basics", difficulty: "beginner" },
  { id: "topic_linux_pipes_intermediate", library: "linux", name: "Pipes, grep и перенаправления", slug: "pipes-grep-redirection", difficulty: "intermediate" },
  { id: "topic_linux_diagnostics_advanced", library: "linux", name: "Диагностика системы", slug: "system-diagnostics", difficulty: "advanced" },
  { id: "topic_git_basics_beginner", library: "git", name: "Git: базовый цикл", slug: "git-basics", difficulty: "beginner" },
  { id: "topic_git_branches_intermediate", library: "git", name: "Git: ветки и синхронизация", slug: "git-branches-remotes", difficulty: "intermediate" },
  { id: "topic_git_history_advanced", library: "git", name: "Git: история и восстановление", slug: "git-history-recovery", difficulty: "advanced" },
  { id: "topic_conda_basics_beginner", library: "conda", name: "Conda: основы", slug: "conda-basics", difficulty: "beginner" },
  { id: "topic_conda_envs_intermediate", library: "conda", name: "Conda: окружения проекта", slug: "conda-project-envs", difficulty: "intermediate" },
  { id: "topic_conda_repro_advanced", library: "conda", name: "Conda: воспроизводимость", slug: "conda-reproducibility", difficulty: "advanced" },
  { id: "topic_docker_basics_beginner", library: "docker", name: "Docker: основы", slug: "docker-basics", difficulty: "beginner" },
  { id: "topic_docker_compose_intermediate", library: "docker", name: "Docker Compose", slug: "docker-compose", difficulty: "intermediate" },
  { id: "topic_docker_debug_advanced", library: "docker", name: "Docker: отладка и сборка", slug: "docker-debug-build", difficulty: "advanced" }
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
