(function () {
    const app = window.WBApp;

    function sumPotential(actions) {
        return ["critical", "important", "opportunities"].reduce(
            (total, type) => total + (actions[type] || []).reduce(
                (typeTotal, item) => typeTotal + (app.hasNumber(item.potential) ? item.potential : 0),
                0,
            ),
            0,
        );
    }

    function renderActionSection(type, items) {
        if (!items.length) {
            return "";
        }

        const labels = {
            critical: "Критично",
            important: "Важно",
            opportunities: "Возможности",
        };
        const colorKey = type === "critical" ? "red" : type === "important" ? "yellow" : "green";

        return `
            <div class="action-section">
                <div class="action-section-title accent-${colorKey}">${labels[type]}</div>
                ${items.map((item) => `
                    <div class="action-card ${type}">
                        <div class="action-title">${app.cleanText(item.title)}</div>
                        <div class="action-desc">${app.cleanText(item.description)}</div>
                        <div class="action-meta">
                            ${app.hasNumber(item.potential) ? `<span class="action-potential">Потенциал: ${app.formatCurrency(item.potential)}</span>` : ""}
                            <span>${item.items_count} товаров</span>
                        </div>
                    </div>
                `).join("")}
            </div>
        `;
    }

    function renderScenario(currentRevenue, totalPotential) {
        const withActions = currentRevenue + totalPotential;

        return `
            <div class="card scenario-card">
                <div class="card-title">Оценка потенциала рекомендаций</div>
                <div class="scenario-grid">
                    <div>
                        <div class="scenario-label">Текущая недельная выручка</div>
                        <div class="scenario-value">${app.formatCurrency(currentRevenue)}</div>
                        <div class="scenario-note">База без пересчета прогноза</div>
                    </div>
                    <div>
                        <div class="scenario-label">После действий</div>
                        <div class="scenario-value accent-green">${app.formatCurrency(withActions)}</div>
                        <div class="scenario-note">Текущая выручка + оцененный потенциал</div>
                    </div>
                    <div>
                        <div class="scenario-label">Дельта</div>
                        <div class="scenario-value accent-cyan">${app.formatCurrency(totalPotential)}</div>
                        <div class="scenario-note">Сумма оценок по рекомендациям</div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderActions() {
        const dashboardData = app.getDashboardData();
        if (!dashboardData) {
            return;
        }

        const { actions, summary } = dashboardData;
        const currentRevenue = summary?.kpi?.revenue?.value || 0;
        const totalPotential = sumPotential(actions);

        document.getElementById("actionsContent").innerHTML = `
            <div class="section-wrapper block-pink">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[-] Сводка рекомендаций</span>
                        <div class="section-desc">Общее количество проблем и возможностей по категориям приоритета</div>
                    </div>
                </div>
                <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
                    <div class="kpi-card">
                        <div class="kpi-label">Критично</div>
                        <div class="kpi-value accent-red">${actions.critical?.length || 0}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Важно</div>
                        <div class="kpi-value accent-yellow">${actions.important?.length || 0}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Возможности</div>
                        <div class="kpi-value accent-green">${actions.opportunities?.length || 0}</div>
                    </div>
                </div>
            </div>

            <div class="section-wrapper block-mint">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[-] План действий</span>
                        <div class="section-desc">Конкретные шаги: пополнение остатков, анализ падения продаж, A/B тесты цен и улучшение карточек</div>
                    </div>
                </div>
                <div class="matrix-actions">
                    <button class="ai-button" onclick="exportActionsToExcel('critical')">Выгрузить критичные</button>
                    <button class="ai-button" onclick="exportActionsToExcel('important')">Выгрузить важные</button>
                    <button class="ai-button" onclick="exportActionsToExcel('opportunities')">Выгрузить возможности</button>
                    <button class="ai-button" onclick="exportActionsToExcel('all')">Выгрузить все рекомендации</button>
                </div>

                <div class="grid-2">
                    <div class="card">
                        <div class="card-title">Срочные действия</div>
                        ${renderActionSection("critical", actions.critical || [])}
                        ${renderActionSection("important", actions.important || [])}
                        ${renderActionSection("opportunities", actions.opportunities || [])}
                        ${!(actions.critical?.length || actions.important?.length || actions.opportunities?.length) ? '<div class="empty-inline">Рекомендаций пока нет</div>' : ""}
                    </div>
                    <div>
                        ${renderScenario(currentRevenue, totalPotential)}
                    </div>
                </div>
            </div>
        `;
    }

    Object.assign(app, {
        renderActions,
    });
})();
