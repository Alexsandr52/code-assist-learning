from app.schemas.catalog import LanguageOut, LibraryOut, TopicOut
from app.schemas.content import Difficulty


LANGUAGES = [LanguageOut(id="lang_python", name="Python", slug="python")]

LIBRARIES = [
    LibraryOut(id="lib_requests", language="python", name="requests", slug="requests", description="HTTP-запросы."),
    LibraryOut(id="lib_pandas", language="python", name="pandas", slug="pandas", description="Таблицы и анализ данных."),
    LibraryOut(id="lib_numpy", language="python", name="numpy", slug="numpy", description="Массивы и численные вычисления."),
    LibraryOut(id="lib_fastapi", language="python", name="FastAPI", slug="fastapi", description="HTTP API на Python."),
    LibraryOut(id="lib_bs4", language="python", name="BeautifulSoup", slug="beautifulsoup", description="Парсинг HTML."),
    LibraryOut(id="lib_matplotlib", language="python", name="matplotlib", slug="matplotlib", description="Графики."),
    LibraryOut(id="lib_sqlalchemy", language="python", name="SQLAlchemy", slug="sqlalchemy", description="ORM и SQL."),
]

TOPICS = [
    TopicOut(id="topic_requests_get_beginner", library="requests", name="GET-запросы", slug="get-requests", difficulty="beginner"),
    TopicOut(id="topic_requests_json_beginner", library="requests", name="JSON-ответы", slug="json-responses", difficulty="beginner"),
    TopicOut(id="topic_requests_headers_beginner", library="requests", name="Заголовки запроса", slug="headers", difficulty="beginner"),
    TopicOut(id="topic_requests_params_beginner", library="requests", name="Query-параметры", slug="query-params", difficulty="beginner"),
    TopicOut(id="topic_requests_post_intermediate", library="requests", name="POST-запросы", slug="post-requests", difficulty="intermediate"),
    TopicOut(id="topic_requests_timeout_intermediate", library="requests", name="Таймауты и ошибки", slug="timeouts-errors", difficulty="intermediate"),
    TopicOut(id="topic_requests_session_intermediate", library="requests", name="Session и cookies", slug="sessions-cookies", difficulty="intermediate"),
    TopicOut(id="topic_requests_auth_intermediate", library="requests", name="Авторизация", slug="auth", difficulty="intermediate"),
    TopicOut(id="topic_requests_retry_advanced", library="requests", name="Повторные попытки", slug="retries", difficulty="advanced"),
    TopicOut(id="topic_requests_streaming_advanced", library="requests", name="Потоковая загрузка", slug="streaming", difficulty="advanced"),
    TopicOut(id="topic_requests_adapters_advanced", library="requests", name="HTTPAdapter", slug="http-adapters", difficulty="advanced"),
    TopicOut(id="topic_pandas_select_beginner", library="pandas", name="Выбор столбцов", slug="select-columns", difficulty="beginner"),
    TopicOut(id="topic_pandas_dataframe_beginner", library="pandas", name="Создание DataFrame", slug="dataframes", difficulty="beginner"),
    TopicOut(id="topic_pandas_filter_beginner", library="pandas", name="Фильтрация строк", slug="filter-rows", difficulty="beginner"),
    TopicOut(id="topic_pandas_groupby_intermediate", library="pandas", name="Группировка groupby", slug="groupby", difficulty="intermediate"),
    TopicOut(id="topic_pandas_missing_intermediate", library="pandas", name="Пропущенные значения", slug="missing-values", difficulty="intermediate"),
    TopicOut(id="topic_pandas_merge_intermediate", library="pandas", name="Объединение таблиц", slug="merge-join", difficulty="intermediate"),
    TopicOut(id="topic_pandas_datetime_intermediate", library="pandas", name="Дата и время", slug="datetime", difficulty="intermediate"),
    TopicOut(id="topic_pandas_pivot_advanced", library="pandas", name="Pivot tables", slug="pivot-tables", difficulty="advanced"),
    TopicOut(id="topic_pandas_window_advanced", library="pandas", name="Оконные функции", slug="rolling-window", difficulty="advanced"),
    TopicOut(id="topic_pandas_apply_advanced", library="pandas", name="Apply и transform", slug="apply-transform", difficulty="advanced"),
    TopicOut(id="topic_numpy_arrays_beginner", library="numpy", name="Создание массивов", slug="arrays", difficulty="beginner"),
    TopicOut(id="topic_numpy_indexing_beginner", library="numpy", name="Индексация массивов", slug="indexing", difficulty="beginner"),
    TopicOut(id="topic_numpy_math_beginner", library="numpy", name="Векторные операции", slug="vector-operations", difficulty="beginner"),
    TopicOut(id="topic_numpy_reshape_intermediate", library="numpy", name="Изменение формы", slug="reshape", difficulty="intermediate"),
    TopicOut(id="topic_numpy_broadcasting_intermediate", library="numpy", name="Broadcasting", slug="broadcasting", difficulty="intermediate"),
    TopicOut(id="topic_numpy_boolean_intermediate", library="numpy", name="Булевы маски", slug="boolean-masks", difficulty="intermediate"),
    TopicOut(id="topic_numpy_random_intermediate", library="numpy", name="Случайные числа", slug="random", difficulty="intermediate"),
    TopicOut(id="topic_numpy_linalg_advanced", library="numpy", name="Линейная алгебра", slug="linear-algebra", difficulty="advanced"),
    TopicOut(id="topic_numpy_einsum_advanced", library="numpy", name="einsum", slug="einsum", difficulty="advanced"),
    TopicOut(id="topic_numpy_memory_advanced", library="numpy", name="Views и копии", slug="views-copies", difficulty="advanced"),
    TopicOut(id="topic_fastapi_routes_beginner", library="fastapi", name="Маршруты", slug="routes", difficulty="beginner"),
    TopicOut(id="topic_fastapi_path_beginner", library="fastapi", name="Path-параметры", slug="path-params", difficulty="beginner"),
    TopicOut(id="topic_fastapi_query_beginner", library="fastapi", name="Query-параметры", slug="query-params", difficulty="beginner"),
    TopicOut(id="topic_fastapi_pydantic_intermediate", library="fastapi", name="Pydantic-модели", slug="pydantic-models", difficulty="intermediate"),
    TopicOut(id="topic_fastapi_status_intermediate", library="fastapi", name="Статусы ответа", slug="response-status", difficulty="intermediate"),
    TopicOut(id="topic_fastapi_dependencies_intermediate", library="fastapi", name="Dependencies", slug="dependencies", difficulty="intermediate"),
    TopicOut(id="topic_fastapi_errors_intermediate", library="fastapi", name="HTTPException", slug="http-exception", difficulty="intermediate"),
    TopicOut(id="topic_fastapi_middleware_advanced", library="fastapi", name="Middleware", slug="middleware", difficulty="advanced"),
    TopicOut(id="topic_fastapi_background_advanced", library="fastapi", name="BackgroundTasks", slug="background-tasks", difficulty="advanced"),
    TopicOut(id="topic_fastapi_security_advanced", library="fastapi", name="OAuth2 и security", slug="oauth2-security", difficulty="advanced"),
    TopicOut(id="topic_bs4_find_beginner", library="beautifulsoup", name="Поиск элементов", slug="find-elements", difficulty="beginner"),
    TopicOut(id="topic_bs4_select_beginner", library="beautifulsoup", name="CSS-селекторы", slug="css-selectors", difficulty="beginner"),
    TopicOut(id="topic_bs4_text_beginner", library="beautifulsoup", name="Получение текста", slug="extract-text", difficulty="beginner"),
    TopicOut(id="topic_bs4_attrs_intermediate", library="beautifulsoup", name="Атрибуты элементов", slug="attributes", difficulty="intermediate"),
    TopicOut(id="topic_bs4_tree_intermediate", library="beautifulsoup", name="Навигация по дереву", slug="tree-navigation", difficulty="intermediate"),
    TopicOut(id="topic_bs4_tables_intermediate", library="beautifulsoup", name="HTML-таблицы", slug="html-tables", difficulty="intermediate"),
    TopicOut(id="topic_bs4_cleanup_intermediate", library="beautifulsoup", name="Очистка текста", slug="text-cleanup", difficulty="intermediate"),
    TopicOut(id="topic_bs4_nested_advanced", library="beautifulsoup", name="Вложенные селекторы", slug="nested-selectors", difficulty="advanced"),
    TopicOut(id="topic_bs4_parsers_advanced", library="beautifulsoup", name="Выбор парсера", slug="parser-choice", difficulty="advanced"),
    TopicOut(id="topic_bs4_robust_advanced", library="beautifulsoup", name="Устойчивый парсинг", slug="robust-parsing", difficulty="advanced"),
    TopicOut(id="topic_matplotlib_line_beginner", library="matplotlib", name="Линейный график", slug="line-plot", difficulty="beginner"),
    TopicOut(id="topic_matplotlib_bar_beginner", library="matplotlib", name="Столбчатый график", slug="bar-chart", difficulty="beginner"),
    TopicOut(id="topic_matplotlib_labels_beginner", library="matplotlib", name="Подписи и легенда", slug="labels-legend", difficulty="beginner"),
    TopicOut(id="topic_matplotlib_subplots_intermediate", library="matplotlib", name="Несколько графиков", slug="subplots", difficulty="intermediate"),
    TopicOut(id="topic_matplotlib_scatter_intermediate", library="matplotlib", name="Scatter plot", slug="scatter-plot", difficulty="intermediate"),
    TopicOut(id="topic_matplotlib_styles_intermediate", library="matplotlib", name="Стили графика", slug="plot-styles", difficulty="intermediate"),
    TopicOut(id="topic_matplotlib_save_intermediate", library="matplotlib", name="Сохранение графика", slug="save-figure", difficulty="intermediate"),
    TopicOut(id="topic_matplotlib_axes_advanced", library="matplotlib", name="Axes API", slug="axes-api", difficulty="advanced"),
    TopicOut(id="topic_matplotlib_twin_advanced", library="matplotlib", name="Две оси Y", slug="twin-axes", difficulty="advanced"),
    TopicOut(id="topic_matplotlib_annotations_advanced", library="matplotlib", name="Аннотации", slug="annotations", difficulty="advanced"),
    TopicOut(id="topic_sqlalchemy_model_beginner", library="sqlalchemy", name="Модель таблицы", slug="models", difficulty="beginner"),
    TopicOut(id="topic_sqlalchemy_engine_beginner", library="sqlalchemy", name="Engine и подключение", slug="engine", difficulty="beginner"),
    TopicOut(id="topic_sqlalchemy_session_beginner", library="sqlalchemy", name="Session", slug="session", difficulty="beginner"),
    TopicOut(id="topic_sqlalchemy_select_intermediate", library="sqlalchemy", name="SELECT-запросы", slug="select-queries", difficulty="intermediate"),
    TopicOut(id="topic_sqlalchemy_insert_intermediate", library="sqlalchemy", name="INSERT и commit", slug="insert-commit", difficulty="intermediate"),
    TopicOut(id="topic_sqlalchemy_relationships_intermediate", library="sqlalchemy", name="Relationships", slug="relationships", difficulty="intermediate"),
    TopicOut(id="topic_sqlalchemy_filters_intermediate", library="sqlalchemy", name="Фильтры запросов", slug="query-filters", difficulty="intermediate"),
    TopicOut(id="topic_sqlalchemy_joins_advanced", library="sqlalchemy", name="JOIN-запросы", slug="joins", difficulty="advanced"),
    TopicOut(id="topic_sqlalchemy_transactions_advanced", library="sqlalchemy", name="Транзакции", slug="transactions", difficulty="advanced"),
    TopicOut(id="topic_sqlalchemy_async_advanced", library="sqlalchemy", name="Async SQLAlchemy", slug="async-sqlalchemy", difficulty="advanced"),
]


def list_languages() -> list[LanguageOut]:
    return LANGUAGES


def list_libraries(language: str) -> list[LibraryOut]:
    return [library for library in LIBRARIES if library.language == language]


def list_topics(library: str, difficulty: Difficulty | None = None) -> list[TopicOut]:
    topics = [topic for topic in TOPICS if topic.library == library]
    if difficulty:
        topics = [topic for topic in topics if topic.difficulty == difficulty]
    return topics


def is_allowed_selection(language: str, library: str, topic: str, difficulty: Difficulty) -> bool:
    return any(item.slug == language for item in LANGUAGES) and any(
        item.library == library and item.slug == topic and item.difficulty == difficulty for item in TOPICS
    )
