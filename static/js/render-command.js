(function () {
    const app = window.WBApp;

    function formatMetricValue(data, type) {
        if (!data?.available && data?.value == null) return "N/A";
        if (type === "currency") return app.formatCurrency(data?.value, "N/A");
        if (type === "pct") return app.formatPct(data?.value, "N/A");
        return app.formatNumber(data?.value, "N/A");
    }

    function formatPrevValue(data, type) {
        if (!data?.available && data?.prev == null) return "недоступно";
        if (type === "currency") return app.formatCurrency(data?.prev, "N/A");
        if (type === "pct") return app.formatPct(data?.prev, "N/A");
        return app.formatNumber(data?.prev, "N/A");
    }

    function renderMetricStatus(data, type) {
        const dynamicsSuffix = type === "pct" ? " п.п." : "%";
        const dynamics = app.hasNumber(data?.dynamics)
            ? `<span>${app.formatDynamics(data.dynamics, dynamicsSuffix)}</span>`
            : "";
        const diffValue = app.hasNumber(data?.diff) && data.diff !== 0
            ? (type === "currency" ? `${app.formatDiff(data.diff)} ₽` : app.formatDiff(data.diff))
            : "";
        const diff = diffValue
            ? `<span class="kpi-diff ${app.dynClass(data.diff)}">${diffValue}</span>`
            : "";

        if (dynamics || diff) return `${dynamics} ${diff}`;
        if (!data?.available && data?.reason) return '<span class="metric-unavailable">Недоступно</span>';
        return '<span class="metric-neutral">-</span>';
    }

    function renderKPI(label, data, type) {
        return `
            <div class="kpi-card">
                <div class="kpi-label">${label}</div>
                <div class="kpi-value ${app.dynClass(data?.dynamics ?? data?.diff)}">${formatMetricValue(data, type)}</div>
                <div class="kpi-dynamics ${app.dynClass(data?.dynamics ?? data?.diff)}">
                    ${renderMetricStatus(data, type)}
                </div>
                <div class="kpi-prev">пред: ${formatPrevValue(data, type)}</div>
                ${data?.reason ? `<div class="metric-reason">${app.cleanText(data.reason)}</div>` : ""}
            </div>
        `;
    }

    function getDropdownLabel(sectionId, options = {}) {
        const selected = app.getProductFilters(sectionId);
        const single = Boolean(options.single);

        if (!selected.length) {
            return options.placeholder || "Все товары";
        }

        if (single) {
            const option = app.getProductOption(selected[0]);
            return option?.label || selected[0];
        }

        return `Выбрано товаров: ${selected.length}`;
    }

    function renderProductDropdown(sectionId, options = {}) {
        const products = app.getProducts();
        const selected = app.getProductFilters(sectionId);
        const selectedSet = new Set(selected);
        const isSingle = Boolean(options.single);

        const allProductsOption = !isSingle ? `
            <button
                type="button"
                class="product-dropdown-item product-dropdown-item-all${selected.length === 0 ? " selected" : ""}"
                data-id="__all__"
                data-search="все товары"
                onclick="toggleProductItem(this)"
            >
                <span class="checkmark">${selected.length === 0 ? "✓" : ""}</span>
                <span class="item-meta">
                    <span class="item-label">Все товары</span>
                    <span class="item-subtitle">Показать весь список товаров без дополнительных ограничений</span>
                </span>
            </button>
        ` : "";

        const itemsHtml = products.length
            ? products.map((product) => {
                const isSelected = selectedSet.has(product.id);
                const searchText = [
                    product.label,
                    product.name,
                    product.seller_article,
                    product.wb_article,
                ].join(" ").toLowerCase();

                return `
                    <button
                        type="button"
                        class="product-dropdown-item${isSelected ? " selected" : ""}"
                        data-id="${product.id}"
                        data-search="${searchText}"
                        onclick="toggleProductItem(this)"
                    >
                        <span class="checkmark">${isSelected ? "✓" : ""}</span>
                        <span class="item-meta">
                            <span class="item-label">${app.cleanText(product.name || product.label)}</span>
                            <span class="item-subtitle">${app.cleanText(product.seller_article || product.wb_article || "")}</span>
                        </span>
                    </button>
                `;
            }).join("")
            : '<div class="product-dropdown-empty">Нет товаров</div>';

        return `
            <div class="product-dropdown" data-section="${sectionId}" data-single="${isSingle ? "true" : "false"}">
                <button type="button" class="product-dropdown-btn${selected.length ? " active" : ""}" onclick="toggleProductDropdown(this)">
                    ${app.cleanText(getDropdownLabel(sectionId, options))}
                </button>
                <div class="product-dropdown-panel">
                    <div class="product-dropdown-search">
                        <input
                            type="text"
                            placeholder="Поиск по артикулу или названию"
                            oninput="filterProductDropdown(this)"
                        >
                    </div>
                    <div class="product-dropdown-list">
                        ${allProductsOption}
                        ${itemsHtml}
                    </div>
                    <div class="product-dropdown-actions">
                        <button type="button" onclick="resetProductFilters('${sectionId}')">Сбросить</button>
                        <button type="button" class="dropdown-apply" onclick="applyProductFilters('${sectionId}')">Применить</button>
                    </div>
                </div>
            </div>
        `;
    }

    function renderDateFilter(sectionId, options = {}) {
        const saved = app.getDateFilters(sectionId);
        const overrides = app.getSectionOverrides(sectionId);
        const today = new Date();
        const maxHistory = new Date(today);
        maxHistory.setDate(today.getDate() - 365);
        const formatDate = (date) => date.toISOString().split("T")[0];
        const minVal = formatDate(maxHistory);
        const maxVal = formatDate(today);

        return `
            <div class="filter-stack ${options.compact ? "compact" : ""}" data-section="${sectionId}">
                <div class="filter-row">
                    <label>с <input type="date" class="df-from" value="${saved.from || ""}" min="${minVal}" max="${maxVal}"></label>
                    <label>по <input type="date" class="df-to" value="${saved.to || ""}" min="${minVal}" max="${maxVal}"></label>
                    <button type="button" class="df-btn" onclick="applyDateFilter('${sectionId}')">Применить</button>
                    ${sectionId !== "general" ? `<button type="button" class="df-reset" onclick="resetDateFilter('${sectionId}')">Сбросить</button>` : ""}
                </div>
                <div class="filter-row">
                    ${renderProductDropdown(sectionId, options)}
                </div>
                ${sectionId !== "general" && (overrides.date || overrides.product) ? '<div class="filter-note">Локальный фильтр переопределяет общий только для этого блока.</div>' : ""}
            </div>
        `;
    }

    function renderFunnel(funnel) {
        const steps = [
            { key: "add_to_cart", label: "Добавления в корзину", color: "#1f1d3d" },
            { key: "orders", label: "Заказы", color: "#000000" },
            { key: "purchased", label: "Выкупы", color: "#1ea64a" },
        ];
        const max = Math.max(...steps.map((step) => app.hasNumber(funnel?.[step.key]?.value) ? funnel[step.key].value : 0), 1);

        return steps.map((step) => {
            const data = funnel?.[step.key] || {};
            if (!data.available && data.value == null) {
                return `<div class="funnel-step unavailable">
                    <div class="funnel-bar is-muted"><span>${step.label}</span><span>недоступно</span></div>
                    <div class="funnel-meta"><span class="metric-reason">${app.cleanText(data.reason) || "нет данных"}</span></div>
                </div>`;
            }
            const value = app.hasNumber(data.value) ? data.value : 0;
            const prev = app.hasNumber(data.prev) ? data.prev : 0;
            const width = Math.max((value / max) * 100, 10);
            return `<div class="funnel-step">
                <div class="funnel-bar" style="width:${width}%;background:${step.color};">
                    <span>${step.label}</span><span>${app.formatNumber(value)}</span>
                </div>
                <div class="funnel-meta">
                    <span class="funnel-dynamics ${app.dynClass(data.dynamics)}">${app.formatDynamics(data.dynamics)}</span>
                    <span class="funnel-prev">было ${app.formatNumber(prev)}</span>
                </div>
            </div>`;
        }).join("");
    }

    function conversionColor(value) {
        if (!app.hasNumber(value)) return "var(--mute)";
        if (value >= 30) return "#1a7a36";
        if (value >= 10) return "#92400e";
        return "#b91c1c";
    }

    function renderConversions(conversions) {
        const items = [
            { label: "Конверсия в корзину", data: conversions.cart_rate },
            { label: "Конверсия в заказ", data: conversions.order_rate },
            { label: "Выкуп", data: conversions.purchase_rate },
        ];
        return items.map((item) => {
            const data = item.data || {};
            if (!data.available && data.value == null) {
                return `<div class="conversion-item unavailable">
                    <div class="conversion-header"><span>${item.label}</span><span class="metric-unavailable">N/A</span></div>
                    <div class="metric-reason">${app.cleanText(data.reason) || "нет данных"}</div>
                </div>`;
            }
            const value = app.hasNumber(data.value) ? data.value : 0;
            const prev = app.hasNumber(data.prev) ? data.prev : 0;
            return `<div class="conversion-item">
                <div class="conversion-header">
                    <span>${item.label}</span>
                    <div>
                        <span class="conversion-value" style="color:${conversionColor(value)}">${value.toFixed(1)}%</span>
                        <span class="kpi-diff ${app.dynClass(data.dynamics)}">${app.formatDynamics(data.dynamics, " п.п.")}</span>
                    </div>
                </div>
                <div class="conversion-bar"><div class="conversion-fill" style="width:${Math.min(Math.abs(value), 100)}%;background:${conversionColor(value)}"></div></div>
                <div class="conversion-meta"><span>пред: ${prev.toFixed(1)}%</span></div>
            </div>`;
        }).join("");
    }

    function renderHitsTable(hits, sectionId) {
        if (!hits?.length) return '<p class="muted">Нет данных</p>';
        const selected = app.getProductFilters(sectionId);
        const filtered = selected.length ? hits.filter((item) => selected.includes(item.seller_article || item.wb_article)) : hits;

        return `<table><thead><tr><th>#</th><th>Артикул / товар</th><th>Выручка</th><th>Динамика</th><th>Остаток</th></tr></thead>
            <tbody>${filtered.map((item, index) => `<tr>
                <td class="muted">${index + 1}</td>
                <td><div class="table-code">${item.seller_article || item.wb_article || "-"}</div><div class="table-title">${app.cleanText(item.name)}</div></td>
                <td class="table-strong">${app.formatCurrency(item.orders_value)}</td>
                <td><span class="badge ${item.dynamics >= 0 ? "badge-success" : "badge-danger"}">${app.formatDynamics(item.dynamics)}</span></td>
                <td>${item.stock === 0 ? '<span class="badge badge-danger">OOS</span>' : item.stock < 50 ? `<span class="badge badge-warning">${item.stock}</span>` : item.stock}</td>
            </tr>`).join("")}</tbody></table>`;
    }

    function renderOutsidersTable(outsiders) {
        if (!outsiders?.length) return '<p class="muted">Проблемных товаров не найдено</p>';
        const badgeClass = { "Нет заказов": "badge-danger", "Низкий CTR": "badge-warning", "Низкий выкуп": "badge-warning" };
        return `<table><thead><tr><th>Артикул / товар</th><th>Проблема</th><th>Рекомендация</th></tr></thead>
            <tbody>${outsiders.map((item) => `<tr>
                <td><div class="table-code">${item.seller_article || item.wb_article || "-"}</div><div class="table-title">${app.cleanText(item.name)}</div><div class="table-note">${app.cleanText(item.detail)}</div></td>
                <td><span class="badge ${badgeClass[app.cleanText(item.issue)] || "badge-info"}">${app.cleanText(item.issue)}</span></td>
                <td>${app.cleanText(item.recommendation)}</td>
            </tr>`).join("")}</tbody></table>`;
    }

    function renderCommandCenter() {
        const data = app.getDashboardData();
        if (!data) return;
        const { summary, hits, outsiders } = data;
        if (!summary || !summary.kpi || !summary.funnel) {
            document.getElementById("commandContent").innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">${data.products_count ? "0" : "OM"}</div>
                    <div class="empty-state-title">${data.products_count ? "Нет данных по выбранным товарам" : "Загрузите данные"}</div>
                    <p>${data.products_count
                        ? "Выбранные товары не содержат заказов за указанный период. Попробуйте сбросить фильтр или выбрать другой период."
                        : "Загрузите Excel или подтяните данные через WB API, чтобы заполнить командный центр."}</p>
                </div>
            `;
            return;
        }
        const kpi = summary.kpi;
        const funnel = summary.funnel;

        document.getElementById("commandContent").innerHTML = `
            <div class="section-wrapper block-lime">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">Командный центр</span>
                        <div class="section-desc">Общие фильтры страницы вынесены в верхний хедер. Ниже можно локально уточнять отдельные блоки без влияния на остальные.</div>
                    </div>
                </div>
                <div class="header-hint">Используйте верхний фильтр по периоду и товарам как базовый контекст для всей страницы.</div>
            </div>

            <div class="section-wrapper block-lime">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">KPI</span>
                        <div class="section-desc">Основные метрики продаж: выручка, заказы, выкупы, средний чек и процент отмен.</div>
                    </div>
                    ${renderDateFilter("kpi", { compact: true })}
                </div>
                <div class="kpi-grid">
                    ${renderKPI("Выручка (заказы)", kpi.revenue, "currency")}
                    ${renderKPI("Заказы", kpi.orders)}
                    ${renderKPI("Выкупы", kpi.purchased_value, "currency")}
                    ${renderKPI("Процент выкупа", kpi.purchase_rate, "pct")}
                </div>

                <div class="kpi-grid-5">
                    ${renderKPI("Конверсия в корзину", kpi.cart_conversion, "pct")}
                    ${renderKPI("Конв. в заказ", kpi.order_conversion, "pct")}
                    ${renderKPI("Средний чек", kpi.avg_order_value, "currency")}
                    ${renderKPI("Отмены", kpi.cancelled_value, "currency")}
                    ${renderKPI("Процент отмен", kpi.cancel_rate, "pct")}
                </div>
            </div>

            <div class="section-wrapper block-lilac">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">Воронка и конверсии</span>
                        <div class="section-desc">Путь от карточки к заказу и выкупу с локальным уточнением по периоду и товарам.</div>
                    </div>
                    ${renderDateFilter("funnel", { compact: true })}
                </div>
                <div class="grid-2">
                    <div class="card">
                        <div class="card-title">Воронка продаж</div>
                        ${renderFunnel(funnel)}
                    </div>
                    <div class="card">
                        <div class="card-title">Конверсии</div>
                        ${renderConversions(funnel.conversions)}
                    </div>
                </div>
            </div>

            <div class="ai-block">
                <div class="ai-header">
                    <div class="ai-icon">AI</div>
                    <div>
                        <div class="ai-title">AI-анализ недели</div>
                        <div class="ai-subtitle">На базе текущих данных</div>
                    </div>
                </div>
                <div class="ai-content" id="aiContent">Нажмите кнопку, чтобы получить AI-анализ.</div>
                <button class="ai-button" id="aiButton" onclick="getAIAnalysis()">Получить анализ</button>
            </div>

            <div class="section-wrapper block-cream">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">Хиты и зоны внимания</span>
                        <div class="section-desc">Товары-лидеры по выручке и позиции, которые требуют внимания.</div>
                    </div>
                    ${renderDateFilter("tables", { compact: true })}
                </div>
                <div class="grid-2">
                    <div class="card">
                        <div class="card-title">Хиты продаж</div>
                        ${renderHitsTable(hits, "tables")}
                    </div>
                    <div class="card">
                        <div class="card-title">Зоны внимания</div>
                        ${renderOutsidersTable(outsiders)}
                    </div>
                </div>
            </div>
        `;
    }

    Object.assign(app, {
        renderCommandCenter,
        renderDateFilter,
        renderProductDropdown,
    });
})();
