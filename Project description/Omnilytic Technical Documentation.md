# Omnilytic — Полное описание программы

> **Версия:** 1.2.0
> **Дата:** 10.06.2026
> **Назначение:** Руководство пользователя + техническая документация + план доработок

---

## Раздел 1. Руководство пользователя

### 1.1 Назначение приложения

**Omnilytic** — одностраничное веб-приложение (SPA) для аналитики продавцов на Wildberries. Бэкенд на FastAPI (Python 3.13), фронтенд — vanilla JavaScript без фреймворков и сборщиков. Никаких Node.js/npm зависимостей.

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

---

### 1.2 Загрузка данных

#### 1.2.1 Загрузка через Excel

**Где:** хедер страницы → кнопка «Загрузить Excel» (drag-n-drop или выбор файла).

**Как работает:**
1. Выбираете `.xlsx` / `.xls` файл стандартного отчёта WB
2. Файл отправляется на сервер (`POST /api/upload`)
3. Сервер читает Excel через `pd.read_excel(io.BytesIO(contents))`, переименовывает колонки (COLUMN_MAPPING — 47 наименований), добавляет расчётные поля (динамика, BCG-классификация, total_stock, lost_revenue)
4. Данные сохраняются в оперативную память (DATA_STORE)
5. После загрузки: автоматически подгружаются список товаров, КПЭ, воронка, хиты, проблемные товары

**Ограничения Excel:**
- Фильтр дат в интерфейсе игнорируется — период зафиксирован в файле (подсказка в tooltip на `#fileInfo`)
- Работает только для структуры отчёта WB (47 колонок с русскими заголовками)

#### 1.2.2 Загрузка через WB API

**Где:** хедер → кнопка «Загрузить API-токен» → панель с полем токена + выбор дат + кнопка «Загрузить».

**Как работает:**
1. Вводите WB API токен (ключ доступа к статистике)
2. Выбираете даты (max 365 дней, не в будущем)
3. Нажимаете «Загрузить»
4. Сервер вызывает `GET /api/v3/sales-funnel` (с пагинацией по 1000 товаров, rate limit 21 сек при 429)
5. Дополнительно: `POST /api/v2/search-report/report` (тариф Jam) — если недоступен, данные просто помечаются как неполные
6. Ответ WB API маппится во внутренний формат (vendorCode → seller_article, nmId → wb_article, и т.д.)
7. Рассчитывается динамика: orders_dynamics, revenue_dynamics, BCG-классификация, total_stock, lost_revenue
8. Ключ API сохраняется в `localStorage` браузера — при следующем открытии страницы он подставится автоматически

**После загрузки (оба источника):**
- Командный центр автоматически обновляется
- В хедере появляется `#fileInfo`: название источника + период (например, «WB API · 2024-01-01 — 2024-01-31»)
- Фильтр дат и товаров активируется

---

### 1.3 Командный центр (страница «Командный центр»)

Набор виджетов для быстрой оценки ситуации. Состоит из 5 блоков:

#### 1.3.1 KPI-панель

Два ряда карточек:

**Ряд 1 (4 карточки):**
- **Выручка (заказы):** суммарная выручка за период, ₽
- **Заказы:** количество заказов, шт
- **Выкупы:** сумма выкупов, ₽
- **Процент выкупа:** доля выкупов от заказов, %

**Ряд 2 (5 карточек):**
- **Конверсия в корзину:** сколько переходов в карточку привели к добавлению в корзину, %
- **Конверсия в заказ:** сколько добавлений в корзину привели к заказу, %
- **Средний чек:** средняя стоимость заказа, ₽
- **Отмены:** сумма отмен, ₽
- **Процент отмен:** доля отмен от заказов, %

**В каждой KPI-карточке:**
- Текущее значение (жирный шрифт)
- Динамика (зелёный ↑ / красный ↓ / серый —)
- Разница с предыдущим периодом в ₽ или п.п.
- Подпись «пред: X» — значение предыдущего периода

Все KPI — средневзвешенные (сумма по выбранным товарам / количество товаров с данными).

#### 1.3.2 Воронка продаж и конверсии

**Воронка продаж:** три визуальные полосы, ширина каждой пропорциональна объёму:
- Добавления в корзину → Заказы → Выкупы
- У каждой полосы: динамика (↑/↓) и «было X» (пред. период)

**Конверсии:** три линейные шкалы-заливки:
- Конверсия в корзину, Конверсия в заказ, Выкуп
- Цвет: зелёный (≥30%), жёлтый (≥10%), красный (<10%)
- Динамика в процентных пунктах, значение предыдущего периода

#### 1.3.3 Хиты продаж

Таблица товаров, отсортированных по выручке (топ-N, по умолчанию 10):
- Порядковый номер
- Артикул (seller_article или wb_article) + название
- Выручка, ₽
- Динамика (badge: зелёный рост / красный падение)
- Остаток: число, или «OOS» (ноль), или жёлтый (<50 шт)

#### 1.3.4 Зоны внимания

Таблица проблемных товаров с категориями:
- **Нет заказов:** товары с ≥1000 показов/переходов, но 0 заказов → рекомендация проверить цену и контент карточки
- **Низкий CTR (только Excel):** CTR <1% при ≥5000 показах → рекомендация улучшить фото
- **Низкий выкуп:** процент выкупа <30% при ≥10 заказах → рекомендация проверить качество/описание

#### 1.3.5 AI-анализ

Блок с нейросетью:
- Кнопка «Получить анализ» → `POST /api/ai/analyze`
- Сервер собирает сводку (категории, BCG-распределение, проблемы, топ-10 товаров)
- Отправляет промпт в Claude Sonnet 4 (Anthropic)
- Показывает текст анализа

**Текущее ограничение:** требует `ANTHROPIC_API_KEY` на сервере. Без ключа — ошибка. В плане — замена на бесплатную нейросеть.

---

### 1.4 Юнит-экономика (страница «Юнит-экономика»)

Два блока: **«Юнит-экономика»** (шкалы + круговая диаграмма) и **«Изменение тарифов»** (таблица).

**Общее:** каждый блок работает ТОЛЬКО для одного товара (single-mode). В дропдауне нет галочки «Все товары», только конкретный товар. Если товар не выбран — placeholder «Выберите один товар».

#### 1.4.1 Шкалы (scale bars) — Блок 1

**Идея (как должно работать):**
10 вертикальных элементов, каждый — полоса разделённая на два сегмента:
- **Левый сегмент (start):** значение компонента на дату начала периода. Ширина = его доля от выручки на начало периода
- **Правый сегмент (end):** значение компонента на дату конца периода. Ширина = его доля от выручки на конец периода

Визуально: слева направо идёт эволюция структуры затрат — как изменилась доля каждого компонента относительно выручки.

**Компоненты (10 шт):**
1. Итоговая цена (retail_price) — жирным, сводная
2. Комиссия WB
3. Логистика
4. Хранение
5. Эквайринг
6. Штрафы
7. Приёмка
8. Удержания
9. Доплаты
10. К перечислению продавцу (payout) — зелёным, сводная

Сверху — две сводки: «Начало периода: X₽» и «Конец периода: Y₽» (общая выручка на дату).

**Проблема (текущее состояние):**
Не все шкалы показывают данные, а те что показывают — часто только левый сегмент (start). Правый сегмент (end) нулевой.

**Причина:** сервер группирует финансовые операции по точной дате через `group_report_rows_by_rr_date()`. `start_rows` берётся ТОЛЬКО за `date_from` (конкретный день начала периода). Если в этот день не было операций у товара — `start_rows = []` → `start_components` = 0 → левый сегмент нулевой ширины. Аналогично для `end_rows` — только за `date_to`.

**Исправление:** если на `date_from` (или `date_to`) данные не найдены — нужно:
1. Записать в лог, что именно нашлось на `date_from` и `date_to` (по отдельности и вместе)
2. Параллельно сделать поиск по ближайшим датам, на которых есть данные
3. Вернуть сообщение: «Данные на указанные даты не найдены, есть данные на: [дата_где_есть_данные]»
4. Для случая когда `date_to` = сегодняшняя дата — идти от неё вниз (к более ранним датам)

#### 1.4.2 Круговая диаграмма (pie chart) — Блок 1

Структура затрат за весь период:
- Общая выручка (retail_price за весь период) = 100%
- Каждый компонент — цветной сегмент (кроме payout, он не показывается на диаграмме)
- Под диаграммой: подписи с цветом, названием, суммой и процентом

**Проблема:** работает некорректно. На диаграмме отображается всего 3 сегмента (вместо 8), плюс сама диаграмма (conic-gradient) отрисовывается с визуальным багом — сегменты съезжают или накладываются друг на друга.

Если нет данных для диаграммы — placeholder «Нет данных для диаграммы».

#### 1.4.3 Таблица тарифов — Блок 2

8 строк тарифов, каждая с двумя измерениями:

| Колонки |||
|---|---|---|
| На начало периода | Стандарт | Факт |
| На конец периода | Стандарт | Факт |
| Изменение | Стандарт | Факт |

**Строки:**
1. Комиссия за продажу — в % (стандарт = справочная ставка WB по категории + метод доставки)
2. Логистика — в ₽
3. Хранение — в ₽
4. Эквайринг — в %
5. Штрафы — в ₽
6. Приёмка — в ₽
7. Удержания — в ₽
8. Доплаты — в ₽

**Стандарт vs Факт:**
- Стандарт: комиссия WB из справочника (кэшируется по ключу API). Если не удалось получить — прочерк в колонке
- Факт: реальные цифры из `/finance/v1/sales-reports/detailed`
- Изменение: для % — разница в п.п., для ₽ — процент изменения

---

### 1.5 Фильтры (даты и товары)

Система фильтрации — одна из ключевых возможностей. Работает в два слоя:

#### 1.5.1 Общие фильтры (general) — в шапке страницы

- **Даты:** два календаря (с ___ по ___) + кнопка «Применить». По умолчанию: последние 7 дней
- **Товары:** дропдаун с поиском → мультивыбор (галочки) → «Выбрано товаров: N» / «Все товары»
- Кнопки: «Сбросить» (очистить выбор) → «Применить» (загрузить данные)

#### 1.5.2 Локальные фильтры (per-секция)

Каждый блок на странице (KPI, Воронка, Таблицы, ue_block1, ue_block2) может переопределить даты и/или товары для себя:
- Фильтр дат + дропдаун товаров внутри блока
- Кнопка «Сбросить» рядом с датами → возврат к общему фильтру
- Нотификация «Локальный фильтр переопределяет общий только для этого блока» при активном переопределении

#### 1.5.3 Принцип каскадного наследования

1. Меняете общие фильтры → применяются ко всем блокам (которые не переопределены локально)
2. Меняете локальный фильтр в блоке → этот блок отвязывается от общего (override = true)
3. Нажимаете «Сбросить» в локальном → override снимается, блок наследует общие настройки

#### 1.5.4 Известный баг

**Поиск в дропдауне товаров не работает.** Функция `filterProductDropdown()` проверяет `data-search` атрибут каждого элемента на совпадение с введённым текстом. На практике — поиск не находит товары. Требует отладки: возможно, `data-search` формируется некорректно или `hidden` не применяется из-за CSS-специфичности.

---

### 1.6 Сброс данных

Кнопка «Сбросить данные» в хедере → диалог подтверждения → очистка всех данных на сервере + ререндер текущей страницы.

**Что сбрасывается:**
- Все данные в DATA_STORE (processed_data, raw_data, метрики, кэши)
- Список товаров на фронтенде
- Данные юнит-экономики (оба блока)
- `#fileInfo` скрывается

---

### 1.7 UI-состояния (сводка)

| Компонент | Состояние | Что видит пользователь |
|---|---|---|
| Командный центр | Нет данных | Ничего (пустая страница) |
| Командный центр | Товары есть, метрик нет | Empty-state: «Нет данных по выбранным товарам» |
| Командный центр | Нет загруженных данных | Empty-state: «Загрузите данные» |
| UE-блок | `needs_token` | Placeholder: «Нужен WB API токен» |
| UE-блок | `needs_product` | Placeholder: «Выберите один товар» |
| UE-блок | `error` | Placeholder с текстом ошибки |
| UE-блок | `null` (не загружен) | Placeholder: «Данные ещё не загружены» |
| UE-блок | payload (шкалы) | Scales + pie chart |
| UE-блок (тарифы) | payload (тарифы) | Tariffs table |
| UE pie | Нет сегментов | Placeholder: «Нет данных для диаграммы» |
| UE тарифы | Нет строк | Placeholder: «Нет тарифов» |
| Дропдаун товаров | 0 товаров | «Нет загруженных товаров. Загрузите Excel или подтяните данные через WB API.» |
| Дропдаун UE (single) | Не выбран товар | Placeholder: «Выберите один товар» |
| Фильтр дат | Override активен | Нотификация: «Локальный фильтр переопределяет...» |
| WB API панель | Открыта | Поле токена + кнопка «Загрузить» |
| WB API панель | Загрузка | Кнопка disabled + spinner |
| AI-анализ | idle | «Нажмите кнопку, чтобы получить AI-анализ» |
| AI-анализ | loading | Спиннер + «Анализируем данные...» |
| AI-анализ | success | Текст анализа |
| AI-анализ | error | Текст ошибки |

---

### 1.8 Планируемые функции (подробно)

#### 1.8.1 AI-анализ (бесплатная модель)

**Проблема:** текущая привязка к Claude (Anthropic) требует платного API-ключа и VPN в РФ/Китае.

**План:** заменить на бесплатную нейросеть. Варианты:
- DeepSeek (самый дешёвый, есть open-source модель)
- YandexGPT (доступна в РФ, есть бесплатный лимит)
- Локальная модель через Ollama (Mistral, Llama) — полностью бесплатно

Пока модель не выбрана (TBD). Главное — чтобы не требовала ключа или требовала бесплатный.

#### 1.8.2 Ручной ввод себестоимости

**Проблема:** текущий `payout` (выручка минус комиссии WB) — это не чистая прибыль. Продавец может нести доп. расходы: закупочная цена товара, доставка до WB, упаковка.

**План:** добавить для каждого товара поля закупочной цены, доставки до WB, упаковки, прочих расходов. Тогда: `чистая_прибыль = payout — себестоимость`.

**ВАЖНО:** прежде чем приступать к реализации, нужно очень детально продумать всю механику:
- Как и где вводить данные (модальное окно, отдельная таблица, inline-редактирование)?
- Как хранить (localStorage, новый endpoint, DATA_STORE)?
- Как рассчитывать (на фронтенде или на бэкенде)?
- Как учитывать разные единицы товара (штуки, кг, комплекты)?
- Что будет если себестоимость больше payout (убыток)?
- Нужна ли история изменения себестоимости?

Без детального ТЗ эта функция рискует стать источником багов.

#### 1.8.3 Экспорт отчётов (CSV/PDF)

**Проблема:** `export.js` существует, но нигде не подключён.

**Статус:** пока не реализуется. Возможно в будущем.

#### 1.8.4 Гео-аналитика (страница-заглушка)

**План:**
- Карта РФ с регионами
- Таблица «Регион → Выручка → Заказы → Доля»
- Фильтр по датам и товарам
- Тепловая карта или пузырьковая диаграмма

#### 1.8.5 Постоянное хранение (БД)

**Проблема:** DATA_STORE в оперативной памяти. При перезапуске сервера все данные пропадают.

**Статус:** оставляем in-memory для локальной разработки. При деплое — SQLite или PostgreSQL.

#### 1.8.6 Кэширование на фронтенде + страница отладки

**Проблема:** каждый вызов `loadDashboard()`, `loadUnitEconomics()` делает HTTP-запрос к серверу, даже если фильтры не менялись.

**План:** сохранять на фронтенде последний ответ для каждой комбинации фильтров. Если фильтры не изменились с прошлого раза — не отправлять запрос, а использовать кэш. **При условии**, что с первого запроса по API пришли все данные целиком.

**Страница отладки:**
Возможно стоит добавить отдельную страницу (или режим) с логированием, где видно:
- Какие запросы уходят на сервер
- Какие приходят ответы (статус, тело)
- Какие данные сохранены в state (dashboardData, products, sectionDates, productFilters)
- Какие ошибки выскакивают (конкретные endpoint, конкретные переменные)

Это поможет быстро выявлять: не передаёт ли какой-то endpoint данные, не падает ли конкретная переменная.

---

### 1.9 Структура страницы (HTML)

```
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
│   └── .wb-api-bar#wbApiBar (input password + кнопка + статус, скрыта)
│
└── main.app-main
    ├── #commandPage.page-section.active → #commandContent
    ├── #unitPage.page-section → #unitEconomicsContent
    └── #geoPage.page-section → #geoAnalyticsContent
```

### 1.10 CSS-архитектура (app.css)

**Цветовая схема:** монохром (black/white) + пастельные цветные блоки

**Переменные:**
- `--ink` / `--canvas` — текст/фон
- `--block-lime`, `--block-lilac`, `--block-cream`, `--block-pink`, `--block-mint`, `--block-coral`, `--block-navy` — блоки
- `--accent-magenta` / `--success` / `--danger` / `--warning`
- `--radius-sm`(6px) / `--radius-md`(8px) / `--radius-lg`(24px) / `--radius-pill`(50px) / `--radius-full`(9999px)

**Шрифты:** Inter (body) + JetBrains Mono (KPI, метрики, бейджи)

**Ключевые элементы:**
- `.page-shell` — 100% ширина, padding h:24px
- `.app-header` — sticky top:0, backdrop-filter:blur, z-index:40
- `.kpi-grid` — 4 колонки / `.kpi-grid-5` — 5 колонок
- `.section-wrapper.block-*` — border-radius:24px, padding:32px
- `.ai-block` — navy фон, белый текст
- `.empty-state` — центрированный, padding:64px 20px
- `.ue-layout` — grid: 1fr + minmax(320px)
- `.product-dropdown` — relative, min-width:360px, z-index:100
- `.product-dropdown-item` → `.selected` — подсветка
- `.product-dropdown-actions` — sticky bottom:0

**Адаптивность:**
- ≤1100px: header → 1 колонка, UE → 1 колонка
- ≤860px: KPI grid → 1 колонка
- ≤810px: все гриды → 1 колонка

### 1.11 Порядок загрузки JS (строгий, через `<script defer>`)

1. `state.js` — создаёт `window.WBApp`
2. `render-command.js` — добавляет `app.renderCommandCenter()`, `app.renderDateFilter()`, `app.renderProductDropdown()`
3. `render-unit-economics.js` — добавляет `app.renderUnitEconomicsPage()`
4. `export.js` — экспорт (второстепенно, не используется)
5. `api.js` — добавляет все async-функции (`loadDashboard()`, `uploadFile()`, `resetData()`, `checkHealth()` и т.д.)
6. `main.js` — инициализация при `DOMContentLoaded`

---

## Раздел 2. Логическое и техническое описание процессов

Для каждого модуля: **что делает → как работает → реализация в коде (файл:строка → строка)**.

### 2.1 DATA_STORE — единое хранилище состояния

**Что:** глобальный словарь Python, хранящий все данные приложения. Живёт в памяти процесса uvicorn.

**Структура** (`main.py:147-169`):
```python
DATA_STORE = {
    "raw_data": None | list[dict],          # сырые записи (из Excel, до process_data)
    "processed_data": None | list[dict],    # обогащённые записи (после process_data)
    "upload_date": None | str,              # ISO datetime
    "period": None | dict,                  # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}
    "filename": None | str,                 # имя файла / "WB API: date_from — date_to"
    "source": None | "excel" | "wb_api",    # источник данных
    "search_report_metrics": None | dict,   # метрики Search Report (если доступны)
    "metrics_availability": None | dict,    # какие метрики доступны для отображения
    "metrics_origin": None | dict,          # откуда каждая метрика (search_report/sales_funnel)
    "unit_cache": {},                        # кэш ответов юнит-экономики
    "commission_cache": {},                  # кэш тарифов комиссий
    "dashboard_cache": {},                   # кэш дашборда
    "wb_api_key": None | str,               # последний успешный WB API ключ
}
```

**Как очищается:** `reset_data()` (`main.py:1795-1810`) — обнуляет все поля. Также очищается при загрузке новых данных (Excel или WB API): `unit_cache = {}`, `dashboard_cache = {}`.

### 2.2 COLUMN_MAPPING — маппинг Excel → internal

**Что:** словарь соответствия русских заголовков колонок Excel → внутренние ключи (английские). Определён как константа на уровне модуля (`main.py:63-122`). 47 записей:

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
| Показы (пред. период) | `impressions_prev` |
| CTR | `ctr` |
| CTR (пред. период) | `ctr_prev` |
| Переходы в карточку | `card_views` |
| Переходы в карточку (пред. период) | `card_views_prev` |
| Доля карточки в выручке | `revenue_share` |
| Доля карточки в выручке (пред. период) | `revenue_share_prev` |
| Положили в корзину | `add_to_cart` |
| Положили в корзину (пред. период) | `add_to_cart_prev` |
| Добавили в отложенные | `add_to_favorites` |
| Добавили в отложенные (пред. период) | `add_to_favorites_prev` |
| Заказали, шт | `orders_qty` |
| Заказали, шт (пред. период) | `orders_qty_prev` |
| Выкупили, шт | `purchased_qty` |
| Выкупы, шт (пред. период) | `purchased_qty_prev` |
| Отменили, шт | `cancelled_qty` |
| Отменили, шт (пред. период) | `cancelled_qty_prev` |
| Конверсия в корзину, % | `cart_conversion` |
| Конверсия в корзину, % (пред. период) | `cart_conversion_prev` |
| Конверсия в заказ, % | `order_conversion` |
| Конверсия в заказ, % (пред. период) | `order_conversion_prev` |
| Процент выкупа | `purchase_rate` |
| Процент выкупа (пред. период) | `purchase_rate_prev` |
| Заказали на сумму, ₽ | `orders_value` |
| Заказали на сумму, ₽ (пред. период) | `orders_value_prev` |
| Динамика суммы заказов, ₽ | `orders_dynamics` |
| Выкупили на сумму, ₽ | `purchased_value` |
| Выкупили на сумму, ₽ (пред. период) | `purchased_value_prev` |
| Отменили на сумму, ₽ | `cancelled_value` |
| Отменили на сумму, ₽ (пред. период) | `cancelled_value_prev` |
| Средняя цена, ₽ | `avg_price` |
| Средняя цена, ₽ (пред. период) | `avg_price_prev` |
| Среднее количество заказов в день, шт | `avg_daily_orders` |
| Среднее количество заказов в день, шт (пред. период) | `avg_daily_orders_prev` |
| Остатки склад ВБ, шт | `stock_wb` |
| Остатки МП, шт | `stock_mp` |
| Сумма остатков на складах, ₽ | `stock_value` |
| Среднее время доставки | `delivery_time` |
| Среднее время доставки (пред. период) | `delivery_time_prev` |
| Локальные заказы, % | `local_orders_pct` |
| Локальные заказы, % (пред. период) | `local_orders_pct_prev` |

**Как применяется:** при загрузке Excel `upload_file()` → `pd.read_excel()` → `df.rename(columns=COLUMN_MAPPING)`. После rename остаются только те колонки, которые есть в mapping. Лишние колонки из Excel отбрасываются.

**Для WB API:** маппинг не используется — `map_api_to_internal()` (`wb_api_client.py`) сразу формирует dict с ключами: `seller_article = product.vendorCode`, `wb_article = product.nmId` (int).

### 2.3 safe_float / safe_int — защитное приведение типов

**Что:** обёртки для безопасного преобразования значений в числа. Возвращают 0 (или значение по умолчанию) при NaN, None, ошибке.

**Код:** `safe_float(value, default=0.0)` и `safe_int(value, default=0)` (`main.py:125-142`).

Используются во всех вычислениях: KPI, компоненты UE, BCG-классификация, сумма выручки и т.д.

### 2.4 resolve_wb_product_id — поиск товара в DATA_STORE

**Что:** подмена артикула из UI (может быть seller_article, wb_article или произвольная строка) на реальный nmId для запроса к WB API.

**Логика:**
1. Приходит `product_id` из дропдауна UI
2. Ищем товар в `DATA_STORE["processed_data"]` через `find_product_record()` (`main.py:304-310`) — проход по всем записям, сравнение `product_id` с `seller_article` и `wb_article`
3. Если товар найден:
   - Если есть `wb_article` → используем его (приоритет: wb_article)
   - Если нет wb_article, но есть seller_article → используем seller_article
4. Если товар не найден → возвращаем переданную строку как есть (`source="as_is"`)
5. NaN/None/null/none → пустая строка (`_normalize()`, `main.py:340-344`)

**Код:** `resolve_wb_product_id()` (`main.py:313-361`). Возвращает словарь:
```python
{
    "input": product_id,        # что пришло
    "wb_id": wb_id,            # что будет отправлено в WB API
    "source": "wb_article"     # откуда взяли: wb_article | seller_article | as_is
       | "seller_article"
       | "as_is",
    "seller_article": "...",   # найденный seller_article
    "wb_article": "...",       # найденный wb_article
    "name": "...",             # название товара
    "matched": True|False      # найден ли в DATA_STORE
}
```

**Логирование:** `UE resolve: input='123' -> wb_id='456' (source=wb_article, seller='123', wb='456')`.

### 2.5 Загрузка через WB API

**Что:** получение данных из Wildberries API вместо Excel.

**Логика:**
1. `resolve_periods()` (`wb_api_client.py`) — валидация дат (from ≤ to, max 365 дней, не в будущем). Если `past_from/past_to` не указаны — рассчитывает предыдущий период равной длины
2. `fetch_sales_funnel()` — POST к `/analytics/v3/sales-funnel/products`
   - Пагинация: страницы по 1000 товаров, курсор `last_id`
   - Rate limit: при 429 → пауза 21 секунда (глобальный `asyncio.Lock`)
3. `map_api_to_internal()` — маппинг полей API: `vendorCode → seller_article`, `nmId → wb_article`, и т.д.
4. `fetch_search_report_overview()` (опционально) — POST к `/v2/search-report/report`
   - Если упало → мягкая ошибка, метрики помечаются как недоступные
   - `format_search_report_error()` — дифференцированное сообщение для 401/403, 429
5. `process_data()` — enrich: динамика (`orders_dynamics_pct`, `revenue_dynamics_pct`), BCG-классификация, `total_stock`, `lost_revenue`
6. Сохранение в DATA_STORE, очистка кэшей

**Код:** `fetch_from_wb()` (`main.py:1514-1647`). Обработка ошибок:
- `ValueError` → 400 Bad Request
- `httpx.HTTPStatusError` → маппинг (401→токен, 429→лимит, остальные→502)
- `httpx.ConnectError`/`TimeoutException` → 503 Сервис недоступен
- `HTTPException` → проброс

### 2.6 Загрузка Excel

**Что:** чтение Excel-файла стандартного отчёта WB.

**Логика:**
1. Multipart file upload → `pd.read_excel(io.BytesIO(contents))`
2. `df.rename(columns=COLUMN_MAPPING)` — переименование колонок
3. `process_data(df)` (`main.py:733-780`) — enrich:
   - Динамика: `calculate_dynamics(current, prev)` для orders_qty, orders_value, impressions, card_views
   - `classify_product()` → `bcg_category` (star/question/cash_cow/dog)
   - `total_stock = stock_wb + stock_mp`
   - `lost_revenue`: если `total_stock=0` и были продажи в prev → упущенная выручка
4. `build_metrics_meta_for_excel()` — отмечает, какие метрики доступны

**Код:** `upload_file()` (`main.py:830-920`). Очищает `unit_cache` и `dashboard_cache`.

### 2.7 Командный центр — KPI и воронка

**Что:** основная страница, 5 параллельных запросов к API.

**Логика (фронтенд** — `api.js:277-320`):
1. `loadDashboard()` → `Promise.all([5×GET])`:
   - `GET /api/dashboard/summary?product_ids=...&date_from=...&date_to=...`
   - `GET /api/dashboard/hits?limit=10&product_ids=...`
   - `GET /api/dashboard/outsiders?limit=10&product_ids=...`
   - `GET /api/dashboard/matrix?product_ids=...`
   - `GET /api/dashboard/actions?product_ids=...`
2. Если любой ответ не `ok` → return без обновления данных
3. `app.setDashboardData({summary, hits, outsiders, matrix, matrixRules, actions})`
4. Проверка stale IDs в `productFilters.general` → сброс если нужно
5. `app.renderCommandCenter()` → рендер HTML

**Логика (бэкенд)** — `get_dashboard_summary()` (`main.py:1090-1208`):
1. **`get_dashboard_snapshot()`** (`main.py:850-1000`):
   - Если `source=wb_api` + даты заданы + ключ есть → `build_wb_dashboard_snapshot()` (перестраивает данные через WB API Sales Funnel)
   - Иначе → фильтрует `DATA_STORE["processed_data"]` по `product_ids` (csv → список) и датам (фильтр по диапазону `period.from` / `period.to`)
2. **Агрегация:**
   - Суммы: `revenue = sum(orders_value)`, `orders = sum(orders_qty)`, `purchased = sum(purchased_qty)`
   - Средневзвешенные: `avg_price = revenue / orders`, `purchase_rate = purchased / orders * 100`, `cancel_rate = cancelled / orders * 100`
3. **Конверсии:** `cart_rate = add_to_cart / card_views * 100`, `order_rate = orders / add_to_cart * 100`
4. **Форматирование:** `build_absolute_metric(value, prev)` / `build_percentage_metric(value, prev)` — создают KPI-объект с `{value, prev, dynamics, diff, available, reason}`

### 2.8 BCG-классификация

**Что:** каждый товар классифицируется в один из 4 квадрантов.

**Логика:**
- `high_dynamics = orders_dynamics > 10%`
- `high_sales = orders_value > 10 000 ₽`

| Динамика >10% | Продажи >10000₽ | Класс |
|---|---|---|
| Да | Да | `star` |
| Да | Нет | `question` |
| Нет | Да | `cash_cow` |
| Нет | Нет | `dog` |

**Код:** `classify_product()` (`main.py:715-730`). Пороги жёстко заданы (не настраиваются).

### 2.9 Юнит-экономика — полный поток

**Что:** расчёт структуры затрат по одному товару через WB API.

**Шаг 1 — resolve ID** (`get_unit_economics_payload()`, `main.py:529-535`):
```python
resolution = resolve_wb_product_id(product_id)
wb_product_id = resolution["wb_id"]
```

Если товар не найден в DATA_STORE → `source="as_is"`, WB API будет искать по введённой строке как есть.

**Шаг 2 — запрос к WB API** (`main.py:557-563`):
```python
rows = await fetch_sales_report_details_by_period(
    api_key=api_key, date_from=date_from, date_to=date_to,
    period="daily", fields=[...]
)
```
- URL: `POST /api/finance/v1/sales-reports/detailed`
- Пагинация: курсор `rrdId`, лимит 100000 строк
- Поля: rrdId, nmId, vendorCode, title, subjectName, rrDate, saleDt, deliveryMethod, retailPriceWithDisc, ppvzSalesCommission, acquiringFee, rebillLogisticCost, paidStorage, penalty, deduction, additionalPayment, paidAcceptance

**Шаг 3 — фильтр совпадений** (`main.py:564`):
```python
matched_rows = [row for row in rows if match_report_row_to_product(row, wb_product_id)]
```

`match_report_row_to_product()` (`main.py:397-402`) — сравнивает `product_id` с `vendorCode` или `nmId` строки отчёта.

Если `matched_rows` пустой → **HTTP 404 с подсказкой**:
- Если товар не найден в DATA_STORE → сообщение про пустой «Артикул WB»
- Если источник Excel → сообщение, что UE всегда работает через WB API
- Если WB API не вернул строк → сообщение про 365 дней

**Шаг 4 — группировка по датам** (`main.py:595-601`):
```python
grouped_rows = group_report_rows_by_rr_date(matched_rows)  # main.py:387-394
start_rows = grouped_rows.get(date_from, [])   # ТОЛЬКО date_from
end_rows = grouped_rows.get(date_to, [])       # ТОЛЬКО date_to
```

**⚠️ ЭТО МЕСТО БАГА:** данные берутся строго за одну дату. Если в `date_from` не было операций → `start_rows = []` → start_components = 0 → левый сегмент шкалы нулевой.

**Исправление:**
1. Проверить, есть ли данные на `date_from` и `date_to` (по отдельности и вместе)
2. Записать в лог результат проверки
3. Если на `date_from` данных нет — найти ближайшую дату С данными (идти вперёд от `date_from`)
4. Если на `date_to` данных нет:
   - Если `date_to` = сегодня — идти вниз (к более ранним датам)
   - Иначе — идти вниз от `date_to` к ближайшей дате с данными
5. Вернуть пользователю: «Данные на указанные даты не найдены, есть данные на: YYYY-MM-DD»

**Шаг 5 — расчёт компонентов** (`main.py:600-602`):
```python
start_components = compute_unit_components(start_rows)
end_components = compute_unit_components(end_rows)
period_components = compute_unit_components(matched_rows)
```

`compute_unit_components()` (`main.py:405-439`):
```python
retail_price = sum(retailPriceWithDisc)
commission = sum(ppvzSalesCommission)
logistics = sum(rebillLogisticCost)
storage = sum(paidStorage)
acquiring = sum(acquiringFee)
penalties = sum(penalty)
acceptance = sum(paidAcceptance)
deductions = sum(deduction)
additional_payments = sum(additionalPayment)
seller_payout = retail_price - commission - logistics - storage
               - acquiring - penalties - acceptance
               - deductions - additional_payments
```

**Шаг 6 — шкалы** (`main.py:610-613`):
```python
scales = [build_scale_item(meta, start_components, end_components)
          for meta in UNIT_SCALE_META]
```

`UNIT_SCALE_META` (`main.py:264-275`):
```python
[
    {"key": "retail_price", "label": "Итоговая цена", "color": "#111111", "is_summary": True},
    {"key": "commission", "label": "Комиссия WB", "color": "#1f1d3d"},
    {"key": "logistics", "label": "Логистика", "color": "#d98c10"},
    {"key": "storage", "label": "Хранение", "color": "#8c6a3c"},
    {"key": "acquiring", "label": "Эквайринг", "color": "#0b7285"},
    {"key": "penalties", "label": "Штрафы", "color": "#d8373a"},
    {"key": "acceptance", "label": "Приемка", "color": "#7c4dff"},
    {"key": "deductions", "label": "Удержания", "color": "#9c36b5"},
    {"key": "additional_payments", "label": "Доплаты", "color": "#ff7b00"},
    {"key": "seller_payout", "label": "К перечислению продавцу", "color": "#1ea64a"},
]
```

`build_scale_item()` (`main.py:442-467`):
- `start_pct = start_value / start_revenue * 100`
- `end_pct = end_value / end_revenue * 100`
- `total_pct = abs(start_pct) + abs(end_pct)`
- `start.width = abs(start_pct) / total_pct`
- `end.width = abs(end_pct) / total_pct`

**Шаг 7 — круговая диаграмма** (`main.py:615-630`):
- Без `is_summary` (retail_price, seller_payout исключены)
- Каждый компонент → `{key, label, value, pct, color}`
- Сегменты с нулевым `value` исключаются

**Шаг 8 — комиссионные тарифы** (`main.py:632-666`):
1. `get_commission_tariffs_cached(api_key)` — GET к `/api/v1/tariffs/commission`, кэш по `api_key`
2. `resolve_standard_commission_rate(payload, subject_name, delivery_method)` — поиск ставки:
   - Матчинг по `subjectName` (категория товара)
   - Если FBS/DBS → `kgvpSupplier`
   - Иначе → `kgvpMarketplace`
3. `build_tariff_actual_row(key, kind, components)` — фактические ставки из start/end
4. `build_tariff_change(kind, start, end)` — изменение: для pct → разница в п.п., для rub → процент изменения

**Шаг 9 — ответ** (`main.py:669-711`):
```python
payload = {
    "product": {"id", "name", "subject_name", "seller_article", "wb_article", "label"},
    "filters": {"date_from", "date_to", "product_id"},
    "start_date": {"date": date_from, "retail_price": ...},
    "end_date": {"date": date_to, "retail_price": ...},
    "scales": [...],  # 10 элементов
    "pie": {"total_revenue": ..., "product_breakdown": [...], "segments": [...]},
    "tariffs": {"rows": [...], "standard_note": "..."},
}
```

Кэшируется в `DATA_STORE["unit_cache"][cache_key]`.

### 2.10 state.js — система состояния

**5 ключевых структур** (`state.js`):

1. **`state`** — `{currentPage, dashboardData, products, unitEconomics, API_BASE}`
2. **`sectionDates`** — `{general, kpi, funnel, tables, ue_block1, ue_block2}` → `{from, to}`
3. **`productFilters`** — те же ключи → `[id1, id2, ...]`
4. **`sectionOverrides`** — те же ключи (кроме general) → `{date: bool, product: bool}`
5. **`unitEconomics`** — `{ue_block1: null | payload, ue_block2: null | payload}`

**Все методы (20 шт):**

| Метод | Сигнатура | Описание |
|---|---|---|
| `getCurrentPage()` | → `string` | Текущая страница |
| `setCurrentPage(pageId)` | → void | Установить страницу |
| `getDashboardData()` | → `object | null` | Данные дашборда |
| `setDashboardData(data)` | → `object` | Сохранить данные |
| `getProducts()` | → `array` | Список товаров |
| `setProducts(products)` | → void | Установить товары |
| `getProductOption(productId)` | → `object | null` | Найти товар по id |
| `getDateFilters(sectionId?)` | → `{from, to}` | Даты секции (клон) |
| `setDateFilters(filters, sectionId?, options?)` | → void | Обновить даты + propagate |
| `resetDateOverride(sectionId)` | → void | Сбросить override дат |
| `getProductFilters(sectionId?)` | → `array` | Фильтр товаров (клон) |
| `setProductFilters(sectionId, selected, options?)` | → void | Обновить фильтр + propagate |
| `resetProductOverride(sectionId)` | → void | Сбросить override товаров |
| `getSectionOverrides(sectionId)` | → `{date, product}` | Флаги override |
| `getUnitEconomicsData(sectionId)` | → `any` | Данные UE блока |
| `setUnitEconomicsData(sectionId, payload)` | → `any` | Сохранить UE данные |
| `resolveUnitProduct(sectionId)` | → `string | null` | Единственный товар для UE |
| `renderCommandCenter()` | → void | Рендер командного центра |
| `renderDateFilter(sectionId, options?)` | → HTML string | Рендер фильтров |
| `renderProductDropdown(sectionId, options?)` | → HTML string | Рендер дропдауна |
| `renderUnitEconomicsPage()` | → void | Рендер страницы UE |

**Ключевой механизм — `propagateGeneralFilters()`:**
Копирует `sectionDates.general` в `sectionDates[секция]` и `productFilters.general` в `productFilters[секция]` для ВСЕХ секций, у которых `sectionOverrides[секция].date === false` / `.product === false`.

### 2.11 main.js — инициализация

**`initialize()` (`main.js:303-319`):**
```
1. initNavigation()             — клики по вкладкам
2. initUploadZone()             — drag'n'drop Excel
3. initDateFilters()            — general даты = сегодня -7 дней
4. renderHeaderFilters()        — даты + дропдаун в шапке
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

**Глобальные функции (window.*):**
- `toggleProductDropdown(button)` — открыть/закрыть дропдаун
- `filterProductDropdown(input)` — поиск по товарам (НЕ РАБОТАЕТ)
- `toggleProductItem(element)` — выбор товара (с поддержкой single-mode)
- `applyProductFilters(sectionId)` — применить фильтр товаров
- `resetProductFilters(sectionId)` — сбросить фильтр товаров
- `applyDateFilter(sectionId)` — применить фильтр дат
- `resetDateFilter(sectionId)` — сбросить фильтр дат

### 2.12 api.js — сетевые запросы

| Функция | Метод | URL | Описание |
|---|---|---|---|
| `loadFilterOptions()` | GET | `/api/filter-options` | Список товаров |
| `loadDashboard(ids?)` | 5×GET | `/api/dashboard/*` | Все данные командного центра |
| `loadSummaryForSection(id)` | GET | `/api/dashboard/summary` | KPI+воронка для секции |
| `loadUnitEconomics(sectionId)` | POST | `/api/unit-economics` | Юнит-экономика |
| `uploadFile(file)` | POST | `/api/upload` | Загрузка Excel |
| `fetchFromWbApi()` | POST | `/api/fetch-from-wb` | Загрузка WB API |
| `resetData()` | POST | `/api/reset` | Сброс данных |
| `checkHealth()` | GET | `/health` | Проверка статуса |
| `getAIAnalysis()` | POST | `/api/ai/analyze` | AI-анализ |

**Особенности:**
- `loadDashboard()` — чекает каждый из 5 ответов. Если любой не `ok` → не обновляет данные, только логирует через `console.log`
- `loadUnitEconomics()` — проверяет token, product, dates перед запросом. Возвращает `state: "needs_token" / "needs_product"` если чего-то не хватает
- `uploadFile()` — использует `app.cleanText()` для очистки cp1252-искажений в сообщениях
- Все запросы с `t: Date.now()` для предотвращения кэширования браузером

### 2.13 WB API client (wb_api_client.py)

**Базовые URL:**
- `https://statistics-api.wildberries.ru` — Sales Funnel, Finance
- `https://common-api.wildberries.ru` — Тарифы комиссий

**Функции (~428 строк):**

| Функция | HTTP | URL | Параметры | Возврат |
|---|---|---|---|---|
| `fetch_sales_funnel()` | POST | `/api/analytics/v3/sales-funnel/products` | api_key, date_from, date_to, past_from, past_to | list[dict] — товары |
| `fetch_search_report_overview()` | POST | `/api/v2/search-report/report` | api_key, date_from, date_to, past_from, past_to | dict — показы/CTR |
| `fetch_sales_report_details_by_period()` | POST | `/api/finance/v1/sales-reports/detailed` | api_key, date_from, date_to, period, fields | list[dict] — строки |
| `fetch_commission_tariffs()` | GET | `/api/v1/tariffs/commission` | api_key, locale | dict — ставки |
| `map_api_to_internal()` | — | — | sales funnel list | internal list |
| `resolve_periods()` | — | — | date_from, date_to, past?, past? | dict с периодами |

**Rate limit:** 21 секунда при 429 (глобальный `asyncio.Lock` + `last_request_time`).
**Максимум истории:** 365 дней (`MAX_HISTORY_DAYS = 365`).
**Таймауты:** 30–60 секунд.

### 2.14 process_data — обогащение записей

**Что:** применяется к данным из Excel и WB API. Добавляет:
- Динамику: `orders_dynamics_pct`, `revenue_dynamics_pct` (через `calculate_dynamics(current, prev)`)
- BCG-класс: `bcg_category` (через `classify_product()`)
- Остаток: `total_stock = stock_wb + stock_mp`
- Упущенную выручку: `lost_revenue` (если stock=0 и были продажи в prev)

**Код:** `process_data()` (`main.py:733-780`). Принимает DataFrame → преобразует каждую строку в dict → возвращает list[dict].

### 2.15 render-command.js — рендер UI

**Функции:**
- `renderCommandCenter()` — рендер всей страницы командного центра. Проверяет `data === null` → ничего. Проверяет `!summary.kpi || !summary.funnel` → empty-state. Иначе → 5 блоков HTML
- `renderKPI(label, data, type)` — карточка KPI (значение, динамика, разница, пред. период)
- `renderFunnel(funnel)` — 3 полосы воронки (width пропорционален max)
- `renderConversions(conversions)` — 3 шкалы конверсий с цветовой индикацией
- `renderHitsTable(hits, sectionId)` — таблица хитов (фильтрация по выбранным товарам)
- `renderOutsidersTable(outsiders)` — таблица проблем с badge и рекомендациями
- `renderDateFilter(sectionId, options?)` — HTML фильтра дат + дропдаун товаров
- `renderProductDropdown(sectionId, options?)` — HTML дропдауна товаров (с поиском, списком, кнопками)

**Состояния:**
- Empty-state для командного центра: два варианта — «Нет данных по выбранным товарам» (если товары есть) / «Загрузите данные» (если товаров нет)

### 2.16 render-unit-economics.js — рендер UE

**Функции:**
- `renderUnitEconomicsPage()` — рендер двух блоков (ue_block1 + ue_block2) с фильтрами
- `renderUnitBlockContent(sectionId, payload)` — диспетчер состояний:
  - `null` → «Данные ещё не загружены»
  - `payload.error` → текст ошибки
  - `payload.state === "needs_token"` → «Нужен WB API токен»
  - `payload.state === "needs_product"` → «Выберите один товар»
  - `sectionId === "ue_block1"` → `renderScale()` + `renderUnitPie()`
  - `sectionId === "ue_block2"` → `renderTariffsTable()`
- `renderScale(scale)` — одна шкала: два сегмента (start/end), ширина в % от total
- `renderUnitPie(pie)` — круговая диаграмма через conic-gradient + легенда
- `renderTariffsTable(payload)` — таблица 8×6 колонок (стандарт/факт × начало/конец/изменение)
- `renderTariffValue(value, kind)` — форматирование (pct → %, rub → ₽)
- `renderTariffChange(value, kind)` — форматирование изменения (+/- п.п. или %)

---

## Раздел 3. Неработающие / отключённые модули

| Модуль | Статус | Причина / Описание |
|---|---|---|
| **Матрица BCG (UI)** | ❌ | `render-matrix.js` (118 строк) существует, но **не импортирован** в `dashboard.html`. Элемент `#matrixContent` отсутствует в DOM. Данные **получаются** (5-й запрос в `loadDashboard()`), **сохраняются** (`dashboardData.matrix`), но никогда не рендерятся. |
| **План действий (UI)** | ❌ | `render-actions.js` (137 строк) существует, но **не импортирован**. Элемент `#actionsContent` отсутствует. Те же данные (`dashboardData.actions`) не рендерятся. |
| **Гео-аналитика** | ❌ Заглушка | Вкладка в навигации есть. Контент: `<div class="empty-state">` с текстом «Страница подготовлена как отдельный раздел без наполнения.» |
| **AI-анализ** | ⚠️ | Бэкенд (`POST /api/ai/analyze`) работает, но требует `ANTHROPIC_API_KEY` на сервере (Claude Sonnet 4). Без ключа — HTTP 500. Фронтенд не даёт ввести ключ. |
| **Экспорт (CSV/PDF)** | ⚠️ | `export.js` существует, функции `exportMatrixToExcel()` и `exportActionsToExcel()` есть. Кнопки нигде не отображаются (т.к. матрица и действия не рендерятся). |
| **Поиск в дропдауне товаров** | ❌ Баг | `filterProductDropdown()` в `main.js:132-140` проверяет `data-search` атрибут на совпадение с вводом. На практике — поиск не находит товары. |
| **Постоянное хранение** | ❌ | DATA_STORE в оперативной памяти (словарь Python). При рестарте uvicorn все данные пропадают. |
| **Юнит-экономика: шкалы (scale bars)** | ⚠️ | Работают частично. Баг: `start_rows = grouped_rows.get(date_from, [])` — берёт данные строго за одну дату. Если в `date_from` не было операций → start-сегмент нулевой. |
| **Юнит-экономика: круговая диаграмма (pie)** | ⚠️ | Показывает всего 3 сегмента (вместо 8). Визуальный баг отрисовки conic-gradient — сегменты съезжают или накладываются. |
| **Проверка stale ID товаров** | ⚠️ | В `loadDashboard()` (`api.js:312-318`) есть проверка устаревших ID в фильтрах, но она может не отрабатывать корректно во всех сценариях. |

---

## Раздел 4. Сравнительный анализ (план vs реальность)

### 4.1 Юнит-экономика: шкалы (scale bars)

**План:** шкала разделена на два сегмента — «на начало периода» (слева) и «на конец периода» (справа). Ширина каждого = доля компонента от выручки своей даты. Визуальное сравнение структуры затрат на старте и в конце периода.

**Реальность:** план верный, реализация недоделана. Конкретная проблема — в `get_unit_economics_payload()` (`main.py:595-601`):
```python
grouped_rows = group_report_rows_by_rr_date(matched_rows)  # группировка по точной дате
start_rows = grouped_rows.get(date_from, [])                # ТОЛЬКО date_from
end_rows = grouped_rows.get(date_to, [])                    # ТОЛЬКО date_to
```

Если в день `date_from` (или `date_to`) не было операций у товара — `start_rows = []` / `end_rows = []` → сегмент не отображается.

**Что нужно исправить:**
1. Проверить, есть ли данные на `date_from` и `date_to` (по отдельности и вместе)
2. Записать в лог результат: «На date_from данных нет, на date_to есть N записей»
3. Если на `date_from` данных нет — найти ближайшую дату ВПЕРЁД от `date_from`, на которой есть данные
4. Если на `date_to` данных нет:
   - Если `date_to` = сегодняшняя дата — идти НАЗАД (к более ранним датам)
   - Иначе — идти назад от `date_to` к ближайшей дате с данными
5. Вернуть пользователю сообщение: «Данные на указанные даты не найдены, есть данные на: [найденная_дата]»

### 4.2 Юнит-экономика: круговая диаграмма (pie chart)

**План:** наглядное отображение структуры затрат за весь период (8 сегментов, conic-gradient).

**Реальность:** отображается только 3 сегмента (вместо 8 возможных). Визуальный баг градиента — сегменты съезжают или накладываются. Причина: или не все компоненты передаются с бэкенда, или фронтенд некорректно обрабатывает проценты (оффсет + stops).

### 4.3 Фильтры

**План:** общие фильтры (даты + товары) + локальные переопределения в каждом блоке.

**Реальность:** план выполнен и перевыполнен. Каскадное наследование, нотификация при override, single-mode для UE — всё работает.

**Единственный баг:** поиск в дропдауне товаров не работает (см. раздел 3).

### 4.4 Матрица BCG + План действий

**Текущее состояние:** бэкенд считает (`classify_product()`, `get_bcg_matrix()`, `get_actions()`), фронтенд запрашивает (5-й запрос в `loadDashboard()`), данные сохраняются в `dashboardData`, но **никогда не рендерятся**.

**Решение: удалить.** Пользователю нужна только аналитика — цифры, графики, структура затрат. Принимать решения (A/B тест, пополнить остатки, оптимизировать цену) — ответственность пользователя, не приложения.

**План действий:**
1. Удалить вызовы `/api/dashboard/matrix` и `/api/dashboard/actions` из `loadDashboard()` в `api.js`
2. Удалить `render-matrix.js` и `render-actions.js` из проекта
3. Можно оставить `bcg_category` как внутреннее поле товара (для сортировки/фильтрации), но не показывать пользователю
4. (Опционально) удалить `get_bcg_matrix()` и `get_actions()` из `main.py`

### 4.5 AI-анализ

**План:** нейросеть для анализа данных продаж.

**Реальность:** бэкенд работает (Claude Sonnet 4 через Anthropic SDK). Фронтенд показывает блок с кнопкой. Но:
- Требует `ANTHROPIC_API_KEY` на сервере
- В РФ/Китае нужен VPN для доступа к Claude
- Нет UI для ввода ключа

**План замены:** подключить бесплатную нейросеть (DeepSeek, YandexGPT или локальную через Ollama). Модель TBD.

### 4.6 Деплой (Railway)

**План:** деплой на Railway для доступа из интернета.

**Реальность:** `Procfile` + `railway.json` настроены, Nixpacks builder, порт через `$PORT`. Не тестировалось.

**Решение:** отложено. DATA_STORE остаётся in-memory.

### 4.7 Отсутствующие функции (подробно)

#### 4.7.1 Сравнение произвольных периодов

**Сейчас:** в каждой KPI-карточке есть автоматический prev_period (прошлая неделя). Сервер сам рассчитывает динамику от предыдущего периода той же длины.

**Чего нет:** пользователь не может выбрать ДВА независимых периода (например, январь vs март) и увидеть их бок о бок. Нет UI для выбора «Период А» и «Период Б» с дублированием всех метрик.

**Статус:** пока не реализуется. Запланировано на будущее.

#### 4.7.2 Ручной ввод себестоимости

**Сейчас:** `payout` (выручка минус комиссии WB) ≠ чистая прибыль. Закупочная цена, доставка до WB, упаковка не учитываются.

**Нужно:** поля для каждого товара (закупка, доставка, упаковка, прочие) → расчёт `чистая_прибыль = payout — себестоимость`.

**ВАЖНО:** перед реализацией нужно детально продумать:
- Как и где вводить данные (модальное окно, inline-редактирование, отдельная таблица)?
- Как хранить (localStorage, новый endpoint, DATA_STORE)?
- Как рассчитывать (фронтенд или бэкенд)?
- Как быть с разными единицами товара (штуки, кг, комплекты)?
- Что если себестоимость > payout (убыток)?
- Нужна ли история изменения себестоимости?

**Статус:** не реализовано. Требует ТЗ.

#### 4.7.3 Гео-аналитика

**Сейчас:** заглушка «Страница подготовлена как отдельный раздел без наполнения.»

**План:**
- Карта РФ с регионами
- Таблица «Регион → Выручка → Заказы → Процент»
- Фильтр по датам и товарам

#### 4.7.4 Кэширование на фронтенде

**Сейчас:** каждый вызов `loadDashboard()` / `loadUnitEconomics()` делает HTTP-запрос, даже если фильтры не менялись.

**Нужно:** при условии, что с первого запроса пришли все данные — сохранять ответ на фронтенде и не перезапрашивать при тех же фильтрах. Инвалидация кэша при смене данных (reset, upload).

#### 4.7.5 Страница отладки

Возможно стоит добавить отдельную страницу (или режим/консольный логгер) с отображением:
- Какие запросы уходят на сервер (URL, параметры)
- Какие приходят ответы (статус, тело, ошибки)
- Какие данные сейчас в state (dashboardData, products, sectionDates, productFilters)
- Какие ошибки выскакивают (конкретный endpoint, конкретная переменная)

Это поможет быстро выявлять: не передаёт ли какой-то endpoint данные, не падает ли конкретная переменная.

---

## Приложение A: Все роуты FastAPI

| Маршрут | Метод | Функция | Статус |
|---|---|---|---|
| `/` | GET | `serve_dashboard()` | ✅ |
| `/health` | GET | `health_check()` | ✅ |
| `/api/upload` | POST | `upload_file()` | ✅ |
| `/api/fetch-from-wb` | POST | `fetch_from_wb()` | ✅ |
| `/api/reset` | POST | `reset_data()` | ✅ |
| `/api/filter-options` | GET | `get_filter_options()` | ✅ |
| `/api/dashboard/summary` | GET | `get_dashboard_summary()` | ✅ |
| `/api/dashboard/hits` | GET | `get_hits()` | ✅ |
| `/api/dashboard/outsiders` | GET | `get_outsiders()` | ✅ |
| `/api/dashboard/matrix` | GET | `get_bcg_matrix()` | ✅ (будет удалён) |
| `/api/dashboard/actions` | GET | `get_actions()` | ✅ (будет удалён) |
| `/api/unit-economics` | POST | `get_unit_economics()` | ✅ |
| `/api/ai/analyze` | POST | `ai_analyze()` | ✅ (условно) |
| `/api/products` | GET | `get_products()` | ✅ |
| `/api/categories` | GET | `get_categories()` | ✅ |

---

## Приложение B: Git-история (11 коммитов)

```
e412887 docs: comprehensive technical documentation for AI handoff
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

## Приложение C: Версии окружения

- **OS:** Windows (win32)
- **Python:** 3.13.7
- **uvicorn:** 0.46.0
- **pandas:** 3.0.0 (в requirements.txt указана 2.1.3)
- **Сервер:** `http://127.0.0.1:8001`
- **Логи:** ранее `uvicorn-8001.out.log` / `uvicorn-8001.err.log` (удалены)
