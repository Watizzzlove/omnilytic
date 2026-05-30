# Changelog

## v1.2.0 — Figma-редизайн + per-section фильтры
- Полный редизайн под Figma-стилистику: monochrome (black/white) + oversized pastel color-block секции (lime, lilac, cream, pink, mint, navy)
- Все CTA — pill-кнопки (border-radius: 50px)
- Inter (body) + JetBrains Mono (KPI, лейблы, бейджи)
- Zero shadows — цветовые блоки вместо elevation
- Hairline borders (1px #e6e6e6) на карточках и инпутах
- Per-section фильтры товаров: каждая секция (general, kpi, funnel, tables) хранит свой набор выбранных товаров
- Per-section фильтры дат: каждая секция хранит свою дату независимо
- Общий фильтр (general) — сверху над всеми разделами, применяется ко всем
- Если изменить дату в KPI — меняются данные только в KPI; воронка, хиты и зоны внимания показывают свои даты
- WB API панель: toggle display:flex/none, только ключ + кнопка Загрузить (даты перенесены в общий фильтр)
- Исправление скорости: cache-busting (?t=...) только при наличии product_ids
- Исправление: пропущенный catch(error) в loadDashboard (был SyntaxError)
- Бэкенд: фильтрация по product_ids во всех 5 эндпоинтах (summary, hits, outsiders, matrix, actions)
- Удалён `populateGeneralProductFilter` — общий фильтр рендерится через renderCommandCenter

## v1.1.0 — WB API интеграция + модульный фронтенд
- Интеграция WB API: создан `backend/wb_api_client.py`, эндпоинт `POST /api/fetch-from-wb`
- Два источника данных: Sales Funnel и Search Report (показы/CTR)
- Валидация периодов: максимум 365 дней истории
- API-ключ сохраняется в localStorage
- Разделение монолитного `dashboard.html` на модульные JS-файлы:
  `state.js`, `api.js`, `main.js`, `render-command.js`, `render-matrix.js`, `render-actions.js`
- Кастомный product-filter dropdown с мультивыбором (чекбоксы, подсветка, сбросить/выбрать)
- Фильтры дат — глобальные (одна дата на все секции)
- Кремовый фон (#fdfcfc), JetBrains Mono, плоский дизайн без теней/градиентов
- ASCII-маркеры в заголовках секций: [+], [x], [-], [~]
- Радиус скругления (4px) только на интерактивных элементах
- Сетки: kpi-grid (4 карточки) + kpi-grid-5 (5 карточек)
- Воронка продаж: 3 шага (добавления → заказы → выкупы)
- Конверсии: 3 метрики (в корзину, в заказ, выкуп)
- BCG-матрица (Матрица решений) с 4 квадрантами
- План действий: критичные, важные, возможности
- AI-анализ через Claude API (зарезервировано, неработоспособно без VPN)
- Деплой через Railway (Procfile + railway.json)
- Очистка зависимостей: удалены shadcn, node_modules, package.json
- Проект не требует npm/Node.js

## v1.0.0 — Исходная версия
- Первый коммит (`06672d1 Initial commit`)
- Загрузка данных только через Excel
- Нет WB API, нет фильтров
- Монолитный `dashboard.html` (CSS и JS встроены в HTML)
- Бэкенд: FastAPI
- Вкладки: Командный центр, Матрица решений, План действий
- AI-анализ: наработка с Anthropic Claude
- Тёмная тема, несуразный дизайн
