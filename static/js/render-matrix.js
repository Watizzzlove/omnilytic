(function () {
    const app = window.WBApp;

    const CATEGORY_META = {
        star: {
            icon: "↑",
            title: "Рост-лидеры",
            subtitle: "Растут и уже приносят заметную выручку",
            color: "#f59e0b",
        },
        question: {
            icon: "?",
            title: "Точки роста",
            subtitle: "Есть рост, но пока мало выручки",
            color: "#d44df0",
        },
        cash_cow: {
            icon: "₽",
            title: "Стабильный доход",
            subtitle: "Сильная выручка, но без заметного роста",
            color: "#22c55e",
        },
        dog: {
            icon: "↓",
            title: "Слабые позиции",
            subtitle: "Слабая динамика и низкая выручка",
            color: "#999999",
        },
    };

    function renderLegend(rules) {
        const growth = rules?.growth_threshold_pct ?? 10;
        const revenue = rules?.revenue_threshold ?? 10000;

        return `
            <div class="matrix-note">
                <div class="matrix-note-title">Логика матрицы</div>
                <div class="matrix-note-text">Рост выше ${growth}% считается высоким.</div>
                <div class="matrix-note-text">Выручка выше ${app.formatCurrency(revenue)} считается сильной.</div>
            </div>
        `;
    }

    function renderCard(categoryKey, data) {
        const meta = CATEGORY_META[categoryKey];
        const items = data?.items || [];

        return `
            <div class="bcg-card ${categoryKey}">
                <div class="bcg-header">
                    <span class="bcg-icon">${meta.icon}</span>
                    <div>
                        <div class="bcg-title" style="color: ${meta.color};">${meta.title}</div>
                        <div class="bcg-subtitle">${meta.subtitle}</div>
                    </div>
                </div>
                <div class="bcg-stats">
                    <div>
                        <div class="bcg-stat-value">${app.formatNumber(data?.count || 0)}</div>
                        <div class="bcg-stat-label">товаров</div>
                    </div>
                    <div>
                        <div class="bcg-stat-value">${app.formatCurrency(data?.revenue || 0)}</div>
                        <div class="bcg-stat-label">выручка</div>
                    </div>
                </div>
                ${items.length
                    ? items.slice(0, 5).map((item) => `
                        <div class="bcg-item">
                            <div class="bcg-item-main">
                                <div class="bcg-item-title">${app.cleanText(item.name)}</div>
                                <div class="bcg-item-code">${item.seller_article || item.wb_article || ""}</div>
                            </div>
                            <span class="badge ${item.dynamics >= 0 ? "badge-success" : "badge-danger"}">${app.formatDynamics(item.dynamics)}</span>
                        </div>
                    `).join("")
                    : '<div class="empty-inline">В этой зоне пока нет товаров</div>'}
            </div>
        `;
    }

    function renderMatrix() {
        const dashboardData = app.getDashboardData();
        if (!dashboardData) {
            return;
        }

        const { matrix, matrixRules } = dashboardData;
        const quadrants = ["star", "question", "cash_cow", "dog"];

        document.getElementById("matrixContent").innerHTML = `
            <div class="section-wrapper block-lilac">
                <div class="section-header">
                    <div class="section-title-group">
                        <span class="section-title">[x] Матрица решений</span>
                        <div class="section-desc">BCG-матрица: группировка товаров по динамике роста и выручке для поиска точек роста</div>
                    </div>
                </div>
                ${renderLegend(matrixRules)}

                <div class="matrix-actions">
                    <button class="ai-button" onclick="exportMatrixToExcel('star')">Выгрузить рост-лидеров</button>
                    <button class="ai-button" onclick="exportMatrixToExcel('question')">Выгрузить точки роста</button>
                    <button class="ai-button" onclick="exportMatrixToExcel('cash_cow')">Выгрузить стабильный доход</button>
                    <button class="ai-button" onclick="exportMatrixToExcel('dog')">Выгрузить слабые позиции</button>
                </div>

                <div class="bcg-grid">
                    ${quadrants.map((key) => renderCard(key, matrix?.[key] || { count: 0, revenue: 0, items: [] })).join("")}
                </div>
            </div>
        `;
    }

    Object.assign(app, {
        renderMatrix,
    });
})();
