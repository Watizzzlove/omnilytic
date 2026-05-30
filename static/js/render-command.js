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

    function renderProductDropdown(sectionId) {
        const data = app.getDashboardData();
        const raw = app.getProductFilters(sectionId);
        const selected = Array.isArray(raw) ? raw : [];
        const hasFilters = selected.length > 0;
        const btnText = hasFilters ? `выбраны товары (${selected.length})` : "фильтр по товарам";

        let itemsHtml = "";
        if (data) {
            const seen = new Set();
            const all = [];
            [...(data.hits || []), ...(data.outsiders || [])].forEach(item => {
                const id = item.seller_article || item.wb_article;
                if (id && !seen.has(id)) { seen.add(id); all.push({ id, name: item.name }); }
            });
            itemsHtml = all.map(p => {
                const sel = selected.includes(p.id) ? " selected" : "";
                const check = sel ? "✓" : "";
                return `<div class="product-dropdown-item${sel}" data-id="${p.id}" onclick="toggleProductItem(this)">
                    <span class="checkmark">${check}</span>
                    <span class="item-label">${app.cleanText(p.name).slice(0, 45)}</span>
                </div>`;
            }).join("");
        }

        return `
            <div class="product-dropdown" data-section="${sectionId}">
                <button class="product-dropdown-btn${hasFilters ? " active" : ""}" onclick="toggleProductDropdown(this)">
                    ${btnText}
                </button>
                <div class="product-dropdown-panel">
                    ${itemsHtml || '<div class="product-dropdown-item" style="cursor:default;color:var(--mute)">нет товаров</div>'}
                    <div class="product-dropdown-actions">
                        <button onclick="resetProductFilters('${sectionId}')">сбросить</button>
                        <button class="dropdown-apply" onclick="applyProductFilters('${sectionId}')">выбрать</button>
                    </div>
                </div>
            </div>
        `;
    }

    function renderDateFilter(sectionId) {
        const saved = app.getDateFilters(sectionId);
        const today = new Date();
        const maxHistory = new Date(today);
        maxHistory.setDate(today.getDate() - 365);
        const fmt = (d) => d.toISOString().split("T")[0];
        const fromVal = saved.from || "";
        const toVal = saved.to || "";
        const minVal = fmt(maxHistory);
        const maxVal = fmt(today);
        return `
            <div class="date-filter" data-section="${sectionId}">
                <div class="df-row">
                    <label>с <input type="date" class="df-from" value="${fromVal}" min="${minVal}" max="${maxVal}"></label>
                    <label>по <input type="date" class="df-to" value="${toVal}" min="${minVal}" max="${maxVal}"></label>
                    <button class="df-btn" onclick="applyDateFilter('${sectionId}')">[ok]</button>
                </div>
                <div class="df-row">${renderProductDropdown(sectionId)}</div>
            </div>
        `;
    }

    function renderFunnel(funnel) {
        const steps = [
            { key: "add_to_cart", label: "Добавления в корзину", color: "#1f1d3d" },
            { key: "orders", label: "Заказы", color: "#000000" },
            { key: "purchased", label: "Выкупы", color: "#1ea64a" },
        ];
        const max = Math.max(...steps.map(s => app.hasNumber(funnel?.[s.key]?.value) ? funnel[s.key].value : 0), 1);

        return steps.map(step => {
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
            { label: "Конверсия в заказ (корзина -> заказ)", data: conversions.order_rate },
            { label: "Выкуп (заказ -> выкуп)", data: conversions.purchase_rate },
        ];
        return items.map(item => {
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
                <div class="conversion-bar"><div class="conversion-fill" style="width:${Math.min(value, 100)}%;background:${conversionColor(value)}"></div></div>
                <div class="conversion-meta"><span>пред: ${prev.toFixed(1)}%</span></div>
            </div>`;
        }).join("");
    }

    function renderHitsTable(hits, sectionId) {
        if (!hits?.length) return '<p class="muted">нет данных</p>';
        const selected = app.getProductFilters(sectionId);
        const filtered = selected?.length ? hits.filter(h => selected.includes(h.seller_article || h.wb_article)) : hits;
        return `<table><thead><tr><th>#</th><th>артикул / товар</th><th>выручка</th><th>динамика</th><th>остаток</th></tr></thead>
            <tbody>${filtered.map((h, i) => `<tr>
                <td class="muted">${i + 1}</td>
                <td><div class="table-code">${h.seller_article || h.wb_article || "-"}</div><div class="table-title">${app.cleanText(h.name)}</div></td>
                <td class="table-strong">${app.formatCurrency(h.orders_value)}</td>
                <td><span class="badge ${h.dynamics >= 0 ? "badge-success" : "badge-danger"}">${app.formatDynamics(h.dynamics)}</span></td>
                <td>${h.stock === 0 ? '<span class="badge badge-danger">OOS</span>' : h.stock < 50 ? `<span class="badge badge-warning">${h.stock}</span>` : h.stock}</td>
            </tr>`).join("")}</tbody></table>`;
    }

    function renderOutsidersTable(outsiders) {
        if (!outsiders?.length) return '<p class="muted">проблемных товаров не найдено</p>';
        const badgeClass = { "Нет заказов": "badge-danger", "Низкий CTR": "badge-warning", "Низкий выкуп": "badge-warning" };
        return `<table><thead><tr><th>артикул / товар</th><th>проблема</th><th>рекомендация</th></tr></thead>
            <tbody>${outsiders.map(item => `<tr>
                <td><div class="table-code">${item.seller_article || item.wb_article || "-"}</div><div class="table-title">${app.cleanText(item.name)}</div><div class="table-note">${app.cleanText(item.detail)}</div></td>
                <td><span class="badge ${badgeClass[app.cleanText(item.issue)] || "badge-info"}">${app.cleanText(item.issue)}</span></td>
                <td>${app.cleanText(item.recommendation)}</td>
            </tr>`).join("")}</tbody></table>`;
    }

    function renderCommandCenter() {
        const data = app.getDashboardData();
        if (!data) return;
        const { summary, hits, outsiders } = data;
        const kpi = summary.kpi;
        const funnel = summary.funnel;

        document.getElementById("commandContent").innerHTML = `
            <div class="section-wrapper block-lime">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[ ] Общий фильтр</span>
                        <div class="section-desc">Выберите период и товары — данные обновятся во всех разделах</div>
                    </div>
                    ${renderDateFilter("general")}
                </div>
            </div>

            <div class="section-wrapper block-lime">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[+] KPI</span>
                        <div class="section-desc">Основные метрики продаж: выручка, заказы, выкупы, средний чек и процент отмен</div>
                    </div>
                    ${renderDateFilter("kpi")}
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
                        <span class="section-title">[x] Воронка и конверсии</span>
                        <div class="section-desc">Как пользователи проходят путь от добавления в корзину до выкупа, и конверсия на каждом этапе</div>
                    </div>
                    ${renderDateFilter("funnel")}
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
                        <div class="ai-subtitle">на базе текущих данных</div>
                    </div>
                </div>
                <div class="ai-content" id="aiContent">Нажмите кнопку, чтобы получить AI-анализ.</div>
                <button class="ai-button" id="aiButton" onclick="getAIAnalysis()">[~] Получить анализ</button>
            </div>

            <div class="section-wrapper block-cream">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[+] Хиты и зоны внимания</span>
                        <div class="section-desc">Товары-лидеры по выручке и позиции, требующие внимания — отсутствие заказов, низкий CTR или выкуп</div>
                    </div>
                    ${renderDateFilter("tables")}
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

    Object.assign(app, { renderCommandCenter });
})();
