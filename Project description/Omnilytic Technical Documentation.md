# Omnilytic — Полная техническая документация

> **Версия:** 1.2.0
> **Дата документа:** 10.06.2026
> **Назначение:** Передача контекста другой нейросети для продолжения разработки

---

## 1. Обзор проекта

**Omnilytic** — одностраничное веб-приложение (SPA) для аналитики продавцов Wildberries. Бэкенд на FastAPI (Python 3.13), фронтенд — vanilla JavaScript без фреймворков и сборщиков. Никаких Node.js/npm зависимостей.

**Запуск (dev):**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Деплой:** Railway (`Procfile` + `railway.json`), Nixpacks builder, порт через `$PORT`

**Зависимости (7 пакетов):**
| Пакет | Версия |
|---|---|
| fastapi | 0.104.1 |
| uvicorn[standard] | 0.24.0 |
| pandas | 2.1.3 |
| openpyxl | 3.1.5 |
| python-multipart | 0.0.6 |
| httpx | 0.25.2 |
| anthropic | 0.39.0 |

**Файл запуска:** `dashboard.html` открывается браузером, JS загружается через `<script defer>`

---

## 2. Структура проекта

```
WB_Analytics_Dashboard_codex/
├── backend/
│   ├── main.py                  # ~1826 строк — FastAPI приложение, все роуты, DATA_STORE
│   └── wb_api_client.py         # ~428 строк — WB Seller API клиент
├── static/
│   ├── css/
│   │   └── app.css              # ~1535 строк — вся стилизация
│   └── js/
│       ├── state.js             # ~237 строк — глобальное состояние, фильтры (window.WBApp)
│       ├── render-command.js    # ~374 строк — рендер командного центра + дропдауны
│       ├── render-unit-economics.js  # ~203 строк — рендер юнит-экономики
│       ├── api.js               # ~444 строк — все запросы к бэкенду
│       ├── main.js              # ~320 строк — инициализация, глобальные обработчики
│       └── export.js            # экспорт данных (не используется активно)
├── dashboard.html               # корневой HTML, структура страницы
├── README.md
├── CHANGELOG.md                 # v1.0 → v1.2
├── requirements.txt
├── .gitignore
├── Procfile                     # web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
└── railway.json
```

### Порядок загрузки JS (строгий, через `<script defer>`):

1. `state.js` — создаёт `window.WBApp`
2. `render-command.js` — добавляет `app.renderCommandCenter`, `app.renderDateFilter`, `app.renderProductDropdown`
3. `render-unit-economics.js` — добавляет `app.renderUnitEconomicsPage`
4. `export.js` — экспорт (второстепенно)
5. `api.js` — добавляет все async-функции (load*, upload, reset, checkHealth)
6. `main.js` — инициализация (`initialize()`) при `DOMContentLoaded`, добавляет глобальные `window.*` обработчики

---

## 3. Бэкенд — DATA_STORE

Единственное глобальное состояние (in-memory, без БД):

```python
DATA_STORE = {
    "raw_data": None | list[dict],          # сырые записи из Excel
    "processed_data": None | list[dict],    # обогащённые записи
    "upload_date": None | str,              # ISO datetime
    "period": None | dict,                  # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}
    "filename": None | str,                 # имя файла
    "source": None | "excel" | "wb_api",   # источник
    "search_report_metrics": None | dict,   # метрики Search Report
    "metrics_availability": None | dict,    # какие метрики доступны
    "metrics_origin": None | dict,          # откуда каждая метрика
    "unit_cache": {},                        # кэш юнит-экономики
    "commission_cache": {},                  # кэш комиссий
    "dashboard_cache": {},                   # кэш дашборда
    "wb_api_key": None | str,               # последний ключ WB API
}
```

---

## 4. Бэкенд — Все роуты FastAPI

### 4.1 `GET /` — отдача `dashboard.html`

### 4.2 `GET /health` (строка ~1780)
```json
{
  "status": "ok",
  "data_loaded": bool,
  "source": null | "excel" | "wb_api",
  "products_count": int,
  "filename": null | str,
  "period": null | dict
}
```

### 4.3 `POST /api/upload` — загрузка Excel
- Multipart file upload (`.xlsx`/`.xls`)
- `pd.read_excel(io.BytesIO(contents))`
- Переименовывает колонки через `COLUMN_MAPPING`
- `process_data(df)` — добавляет расчётные поля
- Очищает кэши, `source = "excel"`
- Возвращает `{success, message, products_count, filename}`

### 4.4 `POST /api/fetch-from-wb` — загрузка через WB API
- Body: `{ wb_api_key, date_from, date_to, past_from?, past_to? }`
- `fetch_sales_funnel()` → `fetch_search_report_overview()`
- `map_api_to_internal()` → маппинг в формат Excel
- `source = "wb_api"`, сохраняет `period`, `wb_api_key`
- Возвращает `{success, message, products_count}`

### 4.5 `GET /api/filter-options` — список товаров
```json
{"products": [{"id": "seller_article or wb_article", "seller_article": "...", "wb_article": "...", "name": "...", "category": "...", "label": "..."}]}
```

### 4.6 `GET /api/dashboard/summary` — KPI + воронка
- Параметры: `product_ids` (csv), `date_from`, `date_to`
- Если даты заданы + `source="wb_api"` + ключ есть → перестраивает snapshot через WB API
- Средневзвешенные KPI: выручка, заказы, выкупы, процент выкупа, процент отмен, средний чек
- Воронка: показы, переходы, корзина, заказы, выкупы, отмены
- Конверсии: CTR, в корзину, в заказ, выкуп, отмены

### 4.7 `GET /api/dashboard/hits` — хиты продаж
- Параметры: `limit` (default 10), `product_ids`, `date_from`, `date_to`
- Топ N по выручке

### 4.8 `GET /api/dashboard/outsiders` — зоны внимания
- Категории: "Нет заказов", "Низкий CTR" (Excel), "Низкий выкуп"

### 4.9 `GET /api/dashboard/matrix` — BCG-матрица
- Классификация: star / question / cash_cow / dog
- Пороги: рост >10%, выручка >10000₽

### 4.10 `GET /api/dashboard/actions` — план действий
- critical: OOS с продажами, падение >30%
- important: низкий рейтинг, CTR>5% + конверсия<2%
- opportunities: звёзды с <50 остатком, вопросы для A/B теста

### 4.11 `POST /api/unit-economics` — юнит-экономика
- Body: `{ wb_api_key, date_from, date_to, product_id }`
- `resolve_wb_product_id()` → подмена seller_article на реальный nmId из DATA_STORE
- `fetch_sales_report_details_by_period()` → финансы от WB
- Компоненты: retail_price, commission, logistics, storage, acquiring, penalties, acceptance, deductions, additional_payments, seller_payout
- Возвращает: шкалы (scale-bar), круговую диаграмму (pie), таблицу тарифов (tariffs)
- **Ошибки:** 400 (вход), 401 (ключ), 429 (rate limit), 404 (нет данных), 502 (WB ошибка), 503 (WB недоступен)

### 4.12 `POST /api/reset` — сброс данных
- Чистит весь DATA_STORE

### 4.13 `POST /api/ai/analyze` — AI-анализ (зарезервировано)
- Anthropic Claude, требует VPN (Китай)

---

## 5. Backend — COLUMN_MAPPING (Excel → internal)

| Русская колонка | Internal key |
|---|---|
| Артикул продавца | `seller_article` |
| Артикул WB | `wb_article` |
| Название | `name` |
| Предмет | `category` |
| Бренд | `brand` |
| Удаленный товар | `is_deleted` |
| Рейтинг карточки | `card_rating` |
| Рейтинг по отзывам | `review_rating` |
| Показы | `impressions` |
| Показы (предыдущий период) | `impressions_prev` |
| CTR | `ctr` |
| CTR (предыдущий период) | `ctr_prev` |
| Переходы в карточку | `card_views` |
| Переходы в карточку (предыдущий период) | `card_views_prev` |
| Доля карточки в выручке | `revenue_share` |
| Доля карточки в выручке (предыдущий период) | `revenue_share_prev` |
| Положили в корзину | `add_to_cart` |
| Положили в корзину (предыдущий период) | `add_to_cart_prev` |
| Добавили в отложенные | `add_to_favorites` |
| Добавили в отложенные (предыдущий период) | `add_to_favorites_prev` |
| Заказали, шт | `orders_qty` |
| Заказали, шт (предыдущий период) | `orders_qty_prev` |
| Выкупили, шт | `purchased_qty` |
| Выкупы, шт (предыдущий период) | `purchased_qty_prev` |
| Отменили, шт | `cancelled_qty` |
| Отменили, шт (предыдущий период) | `cancelled_qty_prev` |
| Конверсия в корзину, % | `cart_conversion` |
| Конверсия в корзину, % (предыдущий период) | `cart_conversion_prev` |
| Конверсия в заказ, % | `order_conversion` |
| Конверсия в заказ, % (предыдущий период) | `order_conversion_prev` |
| Процент выкупа | `purchase_rate` |
| Процент выкупа (предыдущий период) | `purchase_rate_prev` |
| Заказали на сумму, ₽ | `orders_value` |
| Заказали на сумму, ₽ (предыдущий период) | `orders_value_prev` |
| Динамика суммы заказов, ₽ | `orders_dynamics` |
| Выкупили на сумму, ₽ | `purchased_value` |
| Выкупили на сумму, ₽ (предыдущий период) | `purchased_value_prev` |
| Отменили на сумму, ₽ | `cancelled_value` |
| Отменили на сумму, ₽ (предыдущий период) | `cancelled_value_prev` |
| Средняя цена, ₽ | `avg_price` |
| Средняя цена, ₽ (предыдущий период) | `avg_price_prev` |
| Среднее количество заказов в день, шт | `avg_daily_orders` |
| Среднее количество заказов в день, шт (предыдущий период) | `avg_daily_orders_prev` |
| Остатки склад ВБ, шт | `stock_wb` |
| Остатки МП, шт | `stock_mp` |
| Сумма остатков на складах, ₽ | `stock_value` |
| Среднее время доставки | `delivery_time` |
| Среднее время доставки (предыдущий период) | `delivery_time_prev` |
| Локальные заказы, % | `local_orders_pct` |
| Локальные заказы, % (предыдущий период) | `local_orders_pct_prev` |

После загрузки через WB API (`map_api_to_internal`):
- `seller_article = product.vendorCode`
- `wb_article = product.nmId` (int)

---

## 6. Backend — WB API Client (`wb_api_client.py`)

**Базовые URL:**
- `WB_ANALYTICS_BASE = "https://statistics-api.wildberries.ru"`
- `WB_FINANCE_BASE = "https://statistics-api.wildberries.ru"`
- `WB_COMMON_BASE = "https://common-api.wildberries.ru"`

**Rate limit:** 21 секунда между попытками при 429
**Максимум истории:** 365 дней (`MAX_HISTORY_DAYS = 365`)
**Таймаут:** 30–60 секунд

### Функции:

| Функция | URL | Описание |
|---|---|---|
| `fetch_sales_funnel()` | `POST /api/analytics/v3/sales-funnel/products` | Пагинация по 1000, полная выгрузка |
| `fetch_search_report_overview()` | `POST /api/v2/search-report/report` | Тариф Jam, показы/CTR |
| `fetch_sales_report_details_by_period()` | `POST /api/finance/v1/sales-reports/detailed` | Пагинация по rrdId, лимит 100000 |
| `fetch_commission_tariffs()` | `GET /api/v1/tariffs/commission` | Комиссии по категориям |
| `map_api_to_internal()` | — | Маппинг Sales Funnel → internal |
| `resolve_periods()` | — | Валидация дат, расчёт предыдущего периода |

---

## 7. Фронтенд — Структура состояния (`state.js`)

### Внутренние структуры:

```javascript
state = {
    currentPage: "command",           // "command" | "unit" | "geo"
    dashboardData: null,              // { summary, hits, outsiders, matrix, matrixRules, actions }
    products: [],                     // [{ id, label, name, seller_article, wb_article, category }]
    unitEconomics: { ue_block1: null, ue_block2: null },
}

sectionDates = {
    general: { from: "", to: "" },
    kpi: { from: "", to: "" },
    funnel: { from: "", to: "" },
    tables: { from: "", to: "" },
    ue_block1: { from: "", to: "" },
    ue_block2: { from: "", to: "" },
}

productFilters = {
    general:  [],   kpi: [],   funnel: [],   tables: [],
    ue_block1: [],  ue_block2: [],
}

sectionOverrides = {
    kpi: { date: false, product: false },
    funnel: { date: false, product: false },
    tables: { date: false, product: false },
    ue_block1: { date: false, product: false },
    ue_block2: { date: false, product: false },
}
```

### Все методы `window.WBApp`:

| Метод | Сигнатура | Описание |
|---|---|---|
| `getCurrentPage()` | → `string` | Текущая страница |
| `setCurrentPage(pageId)` | → void | Установить страницу |
| `getDashboardData()` | → `object|null` | Данные дашборда |
| `setDashboardData(data)` | → `object` | Сохранить данные |
| `getProducts()` | → `array` | Список товаров |
| `setProducts(products)` | → void | Установить товары |
| `getProductOption(productId)` | → `object|null` | Найти товар по id |
| `getDateFilters(sectionId?)` | → `{from, to}` | Даты секции (клон) |
| `setDateFilters(filters, sectionId?, options?)` | → void | Установить даты + propagate |
| `resetDateOverride(sectionId)` | → void | Сбросить override дат |
| `getProductFilters(sectionId?)` | → `array` | Фильтр товаров (клон) |
| `setProductFilters(sectionId, selected, options?)` | → void | Установить фильтр + propagate |
| `resetProductOverride(sectionId)` | → void | Сбросить override товаров |
| `getSectionOverrides(sectionId)` | → `{date, product}` | Флаги override |
| `getUnitEconomicsData(sectionId)` | → `any` | Данные UE блока |
| `setUnitEconomicsData(sectionId, payload)` | → `any` | Сохранить UE данные |
| `resolveUnitProduct(sectionId)` | → `string|null` | Единственный товар для UE |
| `renderCommandCenter()` | → void | Рендер командного центра |
| `renderDateFilter(sectionId, options?)` | → HTML string | Рендер фильтров |
| `renderProductDropdown(sectionId, options?)` | → HTML string | Рендер дропдауна |
| `renderUnitEconomicsPage()` | → void | Рендер страницы UE |

### Каскадное наследование фильтров:

`propagateGeneralFilters()` — копирует `sectionDates.general` в `sectionDates[секция]` и `productFilters.general` в `productFilters[секция]` ДЛЯ ВСЕХ секций, у которых `sectionOverrides[секция].date === false` / `.product === false`.

**Принцип:** `general` — источник истины. Любая секция может локально переопределить через `markOverride: true`. Сброс override копирует текущий `general` обратно.

---

## 8. Фронтенд — Ключевые сценарии

### 8.1 Инициализация страницы

```
DOMContentLoaded → initialize()
  1. initNavigation()             — клики по вкладкам
  2. initUploadZone()             — drag'n'drop
  3. initDateFilters()            — general даты: сегодня и -7 дней
  4. renderHeaderFilters()        — фильтры в шапке
  5. updateDropdownButtons()      — синхронизация подписей
  6. app.initWbApi()              — восстановление WB ключа из localStorage
  7. app.checkHealth()
       → GET /health
       → loadFilterOptions()      — подгрузка списка товаров
           → GET /api/filter-options
           → app.setProducts()
           → renderHeaderFilters()
       → if data_loaded: loadDashboard()
  8. switchPage("command")        — показать командный центр
```

### 8.2 Загрузка дашборда (`loadDashboard`)

```
Promise.all([5×GET]):
  GET /api/dashboard/summary?product_ids=&date_from=...&date_to=...
  GET /api/dashboard/hits?limit=10&product_ids=...&date_from=...&date_to=...
  GET /api/dashboard/outsiders?limit=10&product_ids=...
  GET /api/dashboard/matrix?product_ids=...
  GET /api/dashboard/actions?product_ids=...

Если любой !ok → return (без обновления данных)

app.setDashboardData({ summary, hits, outsiders, matrix, matrixRules, actions })
loadFilterOptions()                — обновить товары
Проверка stale IDs в productFilters.general → сброс если нужно
app.renderCommandCenter()
```

### 8.3 Применение фильтра дат

```
applyDateFilter(sectionId)
  → читает input.df-from / .df-to из DOM
  → app.setDateFilters({from, to}, sectionId, {markOverride: true/false})
    → обновляет sectionDates[sectionId]
    → если general → propagateGeneralFilters() (все секции)
    → если не general → sectionOverrides[sectionId].date = true
  → loadSummaryForSection() для kpi/funnel
  → loadUnitEconomics() для ue_block1/ue_block2
  → refreshCurrentPage() для остальных
```

### 8.4 Применение фильтра товаров

```
applyProductFilters(sectionId)
  → читает .selected из DOM
  → нормализует (__all__ → [])
  → app.setProductFilters() + propagateGeneralFilters() если general
  → обновление кнопок дропдауна
  → вызов loadSummaryForSection / loadUnitEconomics / refreshCurrentPage
```

### 8.5 Страница юнит-экономики

```
switchPage("unit")
  → loadUnitEconomicsPage()
    1. await loadFilterOptions()             — гарантирует загрузку товаров
    2. app.renderUnitEconomicsPage()         — рендер 2 блоков с дропдаунами (single mode)
    3. Promise.all([
         loadUnitEconomics("ue_block1"),    — POST /api/unit-economics
         loadUnitEconomics("ue_block2"),
       ])
```

**`loadUnitEconomics(sectionId)`:**

1. `resolveUnitProduct(sectionId)` — возвращает один ID или null
2. Нет `wb_api_key` → `state: "needs_token"`
3. Нет `productId` → `state: "needs_product"`
4. Нет дат → `error: "Для блока не задан период."`
5. `POST /api/unit-economics { wb_api_key, date_from, date_to, product_id }`
6. Успех → `app.setUnitEconomicsData()` → `app.renderUnitEconomicsPage()`

### 8.6 Загрузка через WB API

```
fetchFromWbApi()
  1. Валидация: ключ, даты (from ≤ to, не старше 365 дней, не в будущем)
  2. POST /api/fetch-from-wb { wb_api_key, date_from, date_to }
  3. localStorage.setItem("wb_api_key", ...)
  4. updateFileInfo(), setWbStatus()
  5. await loadDashboard()
```

### 8.7 Сброс данных

```
resetData()
  1. confirm("Сбросить все загруженные данные?")
  2. POST /api/reset
  3. app.setDashboardData(null)
  4. app.setProducts([])
  5. app.setUnitEconomicsData("ue_block1", null) / ("ue_block2", null)
  6. Скрыть #fileInfo
  7. Перерендерить текущую страницу + хедер
```

---

## 9. Фронтенд — UI-состояния всех компонентов

### Командный центр (`renderCommandCenter`)

| Состояние | Условие | UI |
|---|---|---|
| loading / нет данных | `data === null` | Ничего не рендерит |
| empty | `data && (!summary.kpi \|\| !summary.funnel)` | `<div class="empty-state">` — "Загрузите данные" / "Нет данных по выбранным товарам" |
| data | всё есть | 5 секций: заголовок, KPI (4+5 карточек), воронка+конверсии, AI-блок, таблицы хитов+проблем |

### Юнит-экономика (`renderUnitBlockContent`)

| Состояние | Условие | UI |
|---|---|---|
| needs_token | `state === "needs_token"` | Placeholder: "Нужен WB API токен" |
| needs_product | `state === "needs_product"` | Placeholder: "Выберите один товар" |
| error | `payload.error` | Placeholder с текстом ошибки |
| empty (null) | `payload === null` | Placeholder: "Данные ещё не загружены" |
| data (block 1) | `payload.scales + payload.pie` | Шкалы + круговая диаграмма |
| data (block 2) | `payload.tariffs.rows` | Таблица тарифов |
| empty_pie | `pie.segments.length === 0` | Placeholder: "Нет данных для диаграммы" |
| empty_tariffs | `tariffs.rows.length === 0` | Placeholder: "Нет тарифов" |

### Фильтры (даты + товары)

| Состояние | UI |
|---|---|
| neutral | date inputs + кнопка "Применить" |
| override active | Нотификация: "Локальный фильтр переопределяет..." |
| dropdown closed | Кнопка с лейблом |
| dropdown open | Поиск + список товаров + Reset/Apply |
| dropdown empty (0 products) | "Нет загруженных товаров. Загрузите Excel или подтяните данные через WB API." |
| dropdown search empty | Все items hidden (фильтр поиска) |
| single mode | Нет "Все товаров", при пустом — placeholder "Выберите один товар" |

### WB API панель

| Состояние | UI |
|---|---|
| closed | Скрыта |
| open | Поле API-ключа + кнопка "Загрузить" |
| loading | Кнопка disabled + spinner |
| success | Сообщение "Данные загружены" |
| error | Сообщение с ошибкой |

### Загрузка файла

| Состояние | UI |
|---|---|
| idle | "Загрузить Excel" |
| dragover | `.dragover` outline |
| file_loaded | `#fileInfo` с именем файла и периодом |

### AI-анализ

| Состояние | UI |
|---|---|
| idle | "Нажмите кнопку, чтобы получить AI-анализ." |
| loading | Спиннер + "Анализируем данные..." |
| success | Текст анализа |
| error | Текст ошибки |

---

## 10. HTML-структура страницы (`dashboard.html`)

```html
.page-shell
├── header.app-header (sticky, blur, z-index:40)
│   ├── .app-header-top
│   │   ├── a.brand (Omnilytic)
│   │   ├── nav.page-nav (3 кнопки: Командный центр, Юнит-экономика, Гео-аналитика)
│   │   └── .header-actions
│   │       ├── #fileInfo (скрыт по умолчанию)
│   │       ├── label#uploadZone (input[type=file])
│   │       ├── button#wbApiToggle ("Загрузить API-токен")
│   │       └── button#resetBtn ("Сбросить данные")
│   ├── .app-header-bottom → #headerFilters (даты + дропдаун товаров)
│   └── .wb-api-bar#wbApiBar (скрыт, input password + кнопка + статус)
│
└── main.app-main
    ├── #commandPage.page-section.active → #commandContent
    ├── #unitPage.page-section → #unitEconomicsContent
    └── #geoPage.page-section → #geoAnalyticsContent
```

---

## 11. CSS-архитектура (`app.css`)

**Цветовая схема:** monochrome (black/white) + oversized pastel color-blocks

**Переменные:**
- `--ink` / `--canvas` — текст/фон
- `--block-lime`, `--block-lilac`, `--block-cream`, `--block-pink`, `--block-mint`, `--block-coral`, `--block-navy`
- `--accent-magenta` / `--success` / `--danger` / `--warning`
- `--radius-sm`(6px) / `--radius-md`(8px) / `--radius-lg`(24px) / `--radius-pill`(50px) / `--radius-full`(9999px)

**Шрифты:** Inter (body) + JetBrains Mono (KPI, метрики, бейджи)

**Ключевые элементы:**
- `.page-shell` — 100% ширина, padding h:24px
- `.app-header` — sticky top:0, backdrop-filter:blur
- `.kpi-grid` — 4 колонки / `.kpi-grid-5` — 5 колонок
- `.section-wrapper.block-*` — border-radius:24px, padding:32px
- `.ai-block` — navy фон, белый текст
- `.empty-state` — центрированный, padding:64px 20px
- `.ue-layout` — grid: 1fr + minmax(320px)
- `.product-dropdown` — position:relative, min-width:360px, z-index:100
- `.product-dropdown-item` → `.selected` — подсветка
- `.product-dropdown-actions` — sticky bottom:0

**Адаптивность:**
- ≤1100px: header → 1 колонка, UE → 1 колонка
- ≤860px: KPI grid → 1 колонка
- ≤810px: все гриды → 1 колонка

---

## 12. Текущий статус (что работает / что нет)

### Работает (✅)
- **Командный центр** — KPI, воронка, конверсии, хиты, проблемы
- **Фильтры дат и товаров** — per-section, каскадное наследование от general
- **Загрузка Excel** — multipart upload, парсинг, маппинг колонок
- **Загрузка через WB API** — Sales Funnel, Search Report, маппинг
- **Сброс данных** — POST /api/reset + кнопка "Сбросить данные"
- **Юнит-экономика** — resolve ID (seller_article → nmId), data + tariffs
- **Resolve ID** — подмена внутреннего артикула на реальный nmId при запросе к WB API
- **Загрузка товаров на UE странице** — `loadFilterOptions()` перед рендером

### Требует доработки (⚠️)
- **Юнит-экономика** — если нет «Артикула WB» (nmId) в DATA_STORE, UE не работает (404). Это by design, но сообщение понятное
- **Нет постоянного хранения** — in-memory DATA_STORE теряется при рестарте
- **Нет аутентификации** — CORS `allow_origins=["*"]`
- **Railway-деплой** — настроен, но не тестирован
- **requirements.txt** — версии могут не совпадать с установленными
- **Логи не ротируются** — растут до перезапуска
- **Битые cp1252 строки** — `cleanText()` фронтенд-фикс, не панацея

### Заглушка / не работает (❌)
- **Гео-аналитика** — пустая страница-заглушка
- **AI-анализ** — требует ключ Anthropic + VPN (Китай)
- **Страница Матрицы решений** — API (`/matrix`) работает, но отдельной страницы нет
- **Страница Плана действий** — API (`/actions`) работает, но отдельной страницы нет

---

## 13. Порядок чтения для быстрого входа в контекст

Для другой нейросети, чтобы быстро разобраться:

1. **`state.js`** — вся система фильтров и state (первым делом)
2. **`api.js`** — все запросы к бэкенду, 5 endpoint-коллов в loadDashboard
3. **`backend/main.py:850-1208`** — `get_dashboard_snapshot` + `get_dashboard_summary`
4. **`backend/main.py:1408-1440`** — unit-economics endpoint
5. **`backend/main.py:1795-1810`** — reset endpoint + DATA_STORE init

Файлы для правок в порядке приоритета:
1. `backend/main.py` — если менять API
2. `static/js/api.js` — если менять запросы или загрузку
3. `static/js/render-command.js` — если менять UI дашборда или дропдауны
4. `static/js/render-unit-economics.js` — если менять UI юнит-экономики
5. `static/js/main.js` — если менять инициализацию или глобальные обработчики
6. `static/css/app.css` — если менять стили
7. `dashboard.html` — если менять структуру страницы (редко)

---

## 14. Git-история (10 коммитов)

```
3526578 fix: дропдаун товаров на странице юнит-экономики был пустой
d846ad9 fix: юнит-экономика резолвит seller_article → nmId через DATA_STORE
7ae12f9 Заработал интерфейс командного центра, остальное - нет
98c653f feat: переработан UI под стилистику Figma, доработаны фильтры, улучшение интерфейса
9f91892 Merge pull request #1 from Watizzzlove/devin/1778762472-add-wb-api-integration
c0a4fb2 fix: validate date range — WB API max 365 days, clamp past period
1331d49 fix: save WB API key in localStorage + improve error messages
53fc726 feat: add WB API integration alongside Excel upload
bc2e782 Add anthropic to requirements.txt
06672d1 Initial commit: WB Analytics Dashboard
```

---

## 15. Версии окружения (фактические)

- **OS:** Windows (win32)
- **Python:** 3.13.7
- **uvicorn:** 0.46.0
- **pandas:** 3.0.0 (в requirements.txt указана 2.1.3)
- **Сервер:** `http://127.0.0.1:8001`
- **Логи:** `uvicorn-8001.out.log` / `uvicorn-8001.err.log` (в корне проекта)
