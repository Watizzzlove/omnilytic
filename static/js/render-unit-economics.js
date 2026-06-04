(function () {
    const app = window.WBApp;

    function formatScaleLabel(point) {
        return `${app.formatCurrency(point.value)} (${app.formatPct(point.pct, "0%")})`;
    }

    function renderScale(scale) {
        return `
            <div class="ue-scale ${scale.is_summary ? "summary" : ""}">
                <div class="ue-scale-title">${app.cleanText(scale.label)}</div>
                <div class="ue-scale-bar">
                    <div class="ue-scale-segment start" style="width:${(scale.start.width * 100).toFixed(2)}%">
                        <span>${formatScaleLabel(scale.start)}</span>
                    </div>
                    <div class="ue-scale-segment end" style="width:${(scale.end.width * 100).toFixed(2)}%">
                        <span>${formatScaleLabel(scale.end)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    function renderUnitPie(pie) {
        const segments = pie?.segments || [];
        if (!segments.length) {
            return `
                <div class="ue-empty">
                    <div class="empty-state-title">Нет данных для диаграммы</div>
                    <p>Выберите период и товар, по которым есть финансовые операции.</p>
                </div>
            `;
        }

        let offset = 0;
        const stops = segments.map((segment) => {
            const start = offset;
            offset += segment.pct;
            return `${segment.color} ${start}% ${offset}%`;
        }).join(", ");

        return `
            <div class="ue-pie-block">
                <div class="ue-pie-summary">
                    <div class="ue-pie-total">${app.formatCurrency(pie.total_revenue)}</div>
                    <div class="ue-pie-products">
                        ${(pie.product_breakdown || []).map((item) => `
                            <span>${app.cleanText(item.label)} — ${app.formatCurrency(item.value)}</span>
                        `).join("")}
                    </div>
                </div>
                <div class="ue-pie-chart" style="background: conic-gradient(${stops});"></div>
                <div class="ue-legend">
                    ${segments.map((segment) => `
                        <div class="ue-legend-item">
                            <span class="ue-legend-swatch" style="background:${segment.color}"></span>
                            <span>${app.cleanText(segment.label)}</span>
                            <strong>${app.formatCurrency(segment.value)} (${app.formatPct(segment.pct)})</strong>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function renderTariffValue(value, kind) {
        if (!app.hasNumber(value)) return "—";
        return kind === "pct" ? app.formatPct(value) : app.formatCurrency(value);
    }

    function renderTariffChange(value, kind) {
        if (!app.hasNumber(value)) return "—";
        return kind === "pct"
            ? `${value > 0 ? "+" : ""}${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })} п.п.`
            : `${value > 0 ? "+" : ""}${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`;
    }

    function renderTariffsTable(payload) {
        const rows = payload?.tariffs?.rows || [];
        if (!rows.length) {
            return '<div class="ue-empty"><div class="empty-state-title">Нет тарифов</div><p>Для выбранного товара и периода нет данных.</p></div>';
        }

        return `
            <div class="ue-table-wrap">
                ${payload?.tariffs?.standard_note ? `<div class="ue-note">${app.cleanText(payload.tariffs.standard_note)}</div>` : ""}
                <table class="ue-table">
                    <thead>
                        <tr>
                            <th rowspan="2">Тариф</th>
                            <th colspan="2">На начало периода</th>
                            <th colspan="2">На конец периода</th>
                            <th colspan="2">Изменение</th>
                        </tr>
                        <tr>
                            <th>Стандарт</th>
                            <th>Факт</th>
                            <th>Стандарт</th>
                            <th>Факт</th>
                            <th>Стандарт</th>
                            <th>Факт</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map((row) => `
                            <tr>
                                <td>${app.cleanText(row.label)}</td>
                                <td>${renderTariffValue(row.start.standard, row.kind)}</td>
                                <td>${renderTariffValue(row.start.actual, row.kind)}</td>
                                <td>${renderTariffValue(row.end.standard, row.kind)}</td>
                                <td>${renderTariffValue(row.end.actual, row.kind)}</td>
                                <td>${renderTariffChange(row.change.standard, row.kind)}</td>
                                <td>${renderTariffChange(row.change.actual, row.kind)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    function renderUnitPlaceholder(title, text) {
        return `
            <div class="ue-empty">
                <div class="empty-state-title">${title}</div>
                <p>${text}</p>
            </div>
        `;
    }

    function renderUnitBlockContent(sectionId, payload) {
        if (!payload) {
            return renderUnitPlaceholder("Данные ещё не загружены", "Примените фильтры блока, и я соберу юнит-экономику по выбранному товару.");
        }
        if (payload.error) {
            return renderUnitPlaceholder("Не удалось загрузить блок", payload.error);
        }
        if (payload.state === "needs_token") {
            return renderUnitPlaceholder("Нужен WB API токен", "Откройте верхнюю панель «Загрузить API-токен», вставьте токен и повторите загрузку.");
        }
        if (payload.state === "needs_product") {
            return renderUnitPlaceholder("Выберите один товар", "Для юнит-экономики нужен ровно один товар в фильтре блока или в общем фильтре сверху.");
        }

        if (sectionId === "ue_block1") {
            return `
                <div class="ue-layout">
                    <div class="ue-scales">
                        <div class="ue-overview">
                            <div class="ue-overview-item">
                                <span>Начало периода</span>
                                <strong>${app.formatCurrency(payload.start_date.retail_price)}</strong>
                            </div>
                            <div class="ue-overview-item">
                                <span>Конец периода</span>
                                <strong>${app.formatCurrency(payload.end_date.retail_price)}</strong>
                            </div>
                        </div>
                        ${payload.scales.map(renderScale).join("")}
                    </div>
                    <div class="ue-chart-card">
                        ${renderUnitPie(payload.pie)}
                    </div>
                </div>
            `;
        }

        return renderTariffsTable(payload);
    }

    function renderUnitEconomicsPage() {
        const block1 = app.getUnitEconomicsData("ue_block1");
        const block2 = app.getUnitEconomicsData("ue_block2");

        document.getElementById("unitEconomicsContent").innerHTML = `
            <div class="section-wrapper block-cream">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">Юнит-экономика</span>
                        <div class="section-desc">Локальные фильтры блока работают только для него. Внутри блока выбирается только один товар.</div>
                    </div>
                    ${app.renderDateFilter("ue_block1", { compact: true, single: true, placeholder: "Выберите один товар" })}
                </div>
                ${renderUnitBlockContent("ue_block1", block1)}
            </div>

            <div class="section-wrapper block-lilac">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">Изменение тарифов</span>
                        <div class="section-desc">Стандартные значения показываются только там, где их можно надёжно получить. В остальных колонках ставятся прочерки.</div>
                    </div>
                    ${app.renderDateFilter("ue_block2", { compact: true, single: true, placeholder: "Выберите один товар" })}
                </div>
                ${renderUnitBlockContent("ue_block2", block2)}
            </div>
        `;
    }

    Object.assign(app, {
        renderUnitEconomicsPage,
    });
})();
