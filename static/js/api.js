(function () {
    const app = window.WBApp;

    function updateFileInfo(label) {
        const fileInfo = document.getElementById("fileInfo");
        const fileName = document.getElementById("fileName");
        if (!fileInfo || !fileName) return;
        fileInfo.style.display = "flex";
        fileName.textContent = label;
    }

    function toggleWbApiPanel() {
        const bar = document.getElementById("wbApiBar");
        const btn = document.getElementById("wbApiToggle");
        if (!bar) return;
        const isVisible = bar.style.display === "flex";
        bar.style.display = isVisible ? "none" : "flex";
        if (btn) btn.classList.toggle("active", !isVisible);
        if (!isVisible) bar.scrollIntoView({ behavior: "smooth" });
    }

    function setWbStatus(message, tone) {
        const statusEl = document.getElementById("wbApiStatus");
        if (!statusEl) return;
        statusEl.style.display = "block";
        statusEl.className = "wb-api-status " + (tone || "info");
        statusEl.textContent = message;
    }

    function validateWbDates(dateFrom, dateTo, showMessage) {
        if (!dateFrom || !dateTo) return false;

        const fromDate = new Date(dateFrom);
        const toDate = new Date(dateTo);
        const today = new Date();
        const maxHistory = new Date(today);
        maxHistory.setDate(today.getDate() - 365);

        if (fromDate > toDate) {
            if (showMessage) setWbStatus("Дата начала не может быть позже даты окончания.", "error");
            return false;
        }
        if (fromDate < maxHistory) {
            if (showMessage) setWbStatus("Максимум 365 дней истории.", "error");
            return false;
        }
        if (toDate > today) {
            if (showMessage) setWbStatus("Дата не может быть в будущем.", "error");
            return false;
        }
        return true;
    }

    function initWbApi() {
        const savedKey = localStorage.getItem("wb_api_key");
        if (savedKey) {
            const input = document.getElementById("wbApiKey");
            if (input) input.value = savedKey;
        }
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${app.API_BASE}/api/upload`, {
                method: "POST",
                body: formData,
            });
            const data = await response.json();

            if (response.ok) {
                updateFileInfo(`${data.products_count} товаров`);
                await loadDashboard();
                return;
            }
            alert("Ошибка: " + app.cleanText(data.detail));
        } catch (error) {
            alert("Ошибка подключения к серверу");
        }
    }

    async function fetchFromWbApi(sectionId) {
        const apiKeyEl = document.getElementById("wbApiKey");
        const apiKey = apiKeyEl ? apiKeyEl.value.trim() : "";
        const saved = app.getDateFilters(sectionId);
        const dateFrom = saved.from;
        const dateTo = saved.to;
        const button = document.getElementById("wbApiFetchBtn");
        const saveKey = false;

        if (!apiKey) { setWbStatus("Введите WB API ключ.", "error"); return; }
        if (!dateFrom || !dateTo) { setWbStatus("Укажите период.", "error"); return; }
        if (!validateWbDates(dateFrom, dateTo, true)) return;

        if (button) { button.disabled = true; button.innerHTML = '<span class="spinner"></span> Загрузка...'; }
        setWbStatus("Загружаем данные из WB API...", "info");

        try {
            const response = await fetch(`${app.API_BASE}/api/fetch-from-wb`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ wb_api_key: apiKey, date_from: dateFrom, date_to: dateTo }),
            });
            const data = await response.json();

            if (response.ok) {
                app.setDateFilters({ from: dateFrom, to: dateTo }, sectionId);
                updateFileInfo(`${data.products_count} товаров (WB API)`);
                localStorage.setItem("wb_api_key", apiKey);
                await loadDashboard();
                return;
            }
            setWbStatus("Ошибка: " + app.cleanText(data.detail), "error");
        } catch (error) {
            setWbStatus("Ошибка подключения.", "error");
        } finally {
            if (button) { button.disabled = false; button.innerHTML = "Загрузить"; }
        }
    }

    async function loadSummaryForSection(sectionId) {
        const raw = app.getProductFilters(sectionId);
        const selected = Array.isArray(raw) ? raw : [];
        if (!selected.length) {
            app.renderCommandCenter();
            return;
        }
        const pid = `product_ids=${encodeURIComponent(selected.join(","))}`;
        try {
            const resp = await fetch(`${app.API_BASE}/api/dashboard/summary?t=${Date.now()}&${pid}`);
            if (!resp.ok) return;
            const filtered = await resp.json();
            const data = app.getDashboardData();
            if (data && data.summary) {
                if (sectionId === "kpi") data.summary.kpi = filtered.kpi;
                else if (sectionId === "funnel") data.summary.funnel = filtered.funnel;
            }
            app.renderCommandCenter();
        } catch (e) {
            console.error("Section filter error:", e);
        }
    }

    async function loadDashboard(productIds) {
        const pid = productIds ? `&product_ids=${encodeURIComponent(productIds)}` : "";
        const cache = productIds ? `&t=${Date.now()}` : "";
        try {
            const [summaryResponse, hitsResponse, outsidersResponse, matrixResponse, actionsResponse] = await Promise.all([
                fetch(`${app.API_BASE}/api/dashboard/summary${pid}${cache}`),
                fetch(`${app.API_BASE}/api/dashboard/hits?limit=10${pid}`),
                fetch(`${app.API_BASE}/api/dashboard/outsiders?limit=10${pid}`),
                fetch(`${app.API_BASE}/api/dashboard/matrix${pid}`),
                fetch(`${app.API_BASE}/api/dashboard/actions${pid}`),
            ]);

            if (!summaryResponse.ok || !hitsResponse.ok || !outsidersResponse.ok || !matrixResponse.ok || !actionsResponse.ok) {
                throw new Error("Не удалось загрузить данные дашборда");
            }

            const [summary, hits, outsiders, matrix, actions] = await Promise.all([
                summaryResponse.json(),
                hitsResponse.json(),
                outsidersResponse.json(),
                matrixResponse.json(),
                actionsResponse.json(),
            ]);

            app.setDashboardData({
                summary,
                hits: hits.hits,
                outsiders: outsiders.outsiders,
                matrix: matrix.matrix,
                matrixRules: matrix.rules || null,
                actions: actions.actions,
            });

            app.renderCommandCenter();
            app.renderMatrix();
            app.renderActions();

            const saved = app.getDateFilters();
            if (saved.from) {
                app.setDateFilters({ from: saved.from, to: saved.to });
            }

        } catch (error) {
            console.error("Load error:", error);
        }
    }

    async function getAIAnalysis() {
        const button = document.getElementById("aiButton");
        const content = document.getElementById("aiContent");
        if (!button || !content) return;

        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> Анализируем...';
        content.textContent = "Анализируем данные...";

        try {
            const response = await fetch(`${app.API_BASE}/api/ai/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ focus: "general" }),
            });
            const data = await response.json();

            if (response.ok) {
                content.textContent = data.analysis;
            } else {
                content.textContent = "Ошибка: " + app.cleanText(data.detail);
            }
        } catch (error) {
            content.textContent = "Ошибка подключения к API";
        } finally {
            button.disabled = false;
            button.innerHTML = "[~] Получить анализ";
        }
    }

    async function checkHealth() {
        try {
            const response = await fetch(`${app.API_BASE}/health`);
            const data = await response.json();
            if (data.data_loaded) {
                await loadDashboard();
            }
        } catch (error) {
            console.error("Health check failed:", error);
        }
    }

    Object.assign(app, {
        checkHealth,
        fetchFromWbApi,
        getAIAnalysis,
        initWbApi,
        loadDashboard,
        loadSummaryForSection,
        toggleWbApiPanel,
        uploadFile,
    });

    window.toggleWbApiPanel = toggleWbApiPanel;
    window.fetchFromWbApi = fetchFromWbApi;
    window.getAIAnalysis = getAIAnalysis;
})();
