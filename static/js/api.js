(function () {
    const app = window.WBApp;

    function buildQuery(params) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value === undefined || value === null || value === "") return;
            search.set(key, value);
        });
        const query = search.toString();
        return query ? `?${query}` : "";
    }

    async function updateFileInfo(label) {
        const fileInfo = document.getElementById("fileInfo");
        const fileName = document.getElementById("fileName");
        if (!fileInfo || !fileName) return;
        fileInfo.style.display = "flex";
        try {
            const h = await fetch(`${app.API_BASE}/health`).then((r) => r.json());
            const period = h && h.period;
            if (period && period.from && period.to) {
                fileName.textContent = `${label} · ${period.from} — ${period.to}`;
                fileName.title = `Источник: ${h.source || "?"}. Для Excel даты фильтра игнорируются — период зафиксирован в файле.`;
            } else {
                fileName.textContent = label;
            }
        } catch (_) {
            fileName.textContent = label;
        }
    }

    async function resetData() {
        if (!window.confirm("Сбросить все загруженные данные? Это действие нельзя отменить.")) return;
        try {
            const response = await fetch(`${app.API_BASE}/api/reset`, { method: "POST" });
            const data = await response.json();
            if (response.ok) {
                console.log("[RESET] data cleared");
                app.setDashboardData(null);
                app.setProducts([]);
                app.setUnitEconomicsData("ue_block1", null);
                app.setUnitEconomicsData("ue_block2", null);
                const fileInfo = document.getElementById("fileInfo");
                if (fileInfo) fileInfo.style.display = "none";
                if (app.getCurrentPage() === "command") {
                    app.renderCommandCenter();
                } else if (app.getCurrentPage() === "unit") {
                    app.renderUnitEconomicsPage();
                }
                if (typeof app.renderHeaderFilters === "function") {
                    app.renderHeaderFilters();
                }
            } else {
                alert("Ошибка сброса: " + (data.detail || "неизвестно"));
            }
        } catch (error) {
            alert("Не удалось сбросить данные: " + error.message);
        }
    }

    function toggleWbApiPanel() {
        const bar = document.getElementById("wbApiBar");
        const btn = document.getElementById("wbApiToggle");
        if (!bar) return;
        const isVisible = bar.classList.contains("open");
        bar.classList.toggle("open", !isVisible);
        if (btn) btn.classList.toggle("active", !isVisible);
        if (!isVisible) bar.scrollIntoView({ behavior: "smooth" });
    }

    function setWbStatus(message, tone) {
        const statusEl = document.getElementById("wbApiStatus");
        if (!statusEl) return;
        statusEl.style.display = "block";
        statusEl.className = `wb-api-status ${tone || "info"}`;
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
            if (showMessage) setWbStatus("WB API отдаёт максимум 365 дней истории.", "error");
            return false;
        }
        if (toDate > today) {
            if (showMessage) setWbStatus("Дата окончания не может быть в будущем.", "error");
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

    function getWbApiKey() {
        return document.getElementById("wbApiKey")?.value.trim() || "";
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
                if (app.getCurrentPage() === "unit") {
                    await loadUnitEconomicsPage();
                }
                return;
            }
            alert(`Ошибка: ${app.cleanText(data.detail)}`);
        } catch (error) {
            alert("Ошибка подключения к серверу.");
        }
    }

    async function fetchFromWbApi() {
        const apiKey = getWbApiKey();
        const dates = app.getDateFilters("general");
        const button = document.getElementById("wbApiFetchBtn");

        if (!apiKey) {
            setWbStatus("Введите WB API ключ.", "error");
            return;
        }
        if (!dates.from || !dates.to) {
            setWbStatus("Укажите период.", "error");
            return;
        }
        if (!validateWbDates(dates.from, dates.to, true)) return;

        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Загружаем...';
        }
        setWbStatus("Загружаем данные из WB API...", "info");

        try {
            const response = await fetch(`${app.API_BASE}/api/fetch-from-wb`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    wb_api_key: apiKey,
                    date_from: dates.from,
                    date_to: dates.to,
                }),
            });
            const data = await response.json();

            if (!response.ok) {
                setWbStatus(`Ошибка: ${app.cleanText(data.detail)}`, "error");
                return;
            }

            localStorage.setItem("wb_api_key", apiKey);
            updateFileInfo(`${data.products_count} товаров (WB API)`);
            setWbStatus(`Данные загружены: ${data.products_count} товаров.`, "success");
            await loadDashboard();
            if (app.getCurrentPage() === "unit") {
                await loadUnitEconomicsPage();
            }
        } catch (error) {
            setWbStatus("Ошибка подключения к WB API.", "error");
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = "Загрузить";
            }
        }
    }

    async function loadFilterOptions() {
        try {
            const response = await fetch(`${app.API_BASE}/api/filter-options`);
            const data = await response.json();
            app.setProducts(data.products || []);
            if (typeof app.renderHeaderFilters === "function") {
                app.renderHeaderFilters();
            }
        } catch (error) {
            app.setProducts([]);
        }
    }

    async function loadSummaryForSection(sectionId) {
        const selected = app.getProductFilters(sectionId);
        const productIds = selected.length ? selected.join(",") : "";
        const dates = app.getDateFilters(sectionId);
        console.log(
            "[SECTION] loadSummaryForSection(" + sectionId + ") productIds=" + JSON.stringify(productIds) +
            " dates=" + JSON.stringify(dates),
        );

        try {
            const response = await fetch(
                `${app.API_BASE}/api/dashboard/summary${buildQuery({
                    t: Date.now(),
                    product_ids: productIds,
                    date_from: dates.from,
                    date_to: dates.to,
                })}`,
            );
            if (!response.ok) {
                console.warn("[SECTION] backend returned " + response.status + " for " + sectionId);
                return;
            }
            const filtered = await response.json();
            console.log(
                "[SECTION] response for " + sectionId +
                ": products_count=" + filtered.products_count +
                " revenue=" + (filtered.kpi && filtered.kpi.revenue && filtered.kpi.revenue.value) +
                " data_with_orders=" + (filtered.data_with_orders_count ?? "-"),
            );
            if (!filtered.products_count) {
                console.warn("[SECTION] empty response for " + sectionId + " - keeping previous data");
                return;
            }
            const data = app.getDashboardData();
            if (data && data.summary) {
                if (sectionId === "kpi") data.summary.kpi = filtered.kpi;
                if (sectionId === "funnel") data.summary.funnel = filtered.funnel;
            }
            app.renderCommandCenter();
        } catch (error) {
            console.error("Section summary error:", error);
        }
    }

    async function loadDashboard(productIds) {
        const generalDates = app.getDateFilters("general");
        const productQuery = buildQuery({
            product_ids: productIds || "",
        });
        const summaryQuery = buildQuery({
            t: Date.now(),
            product_ids: productIds || "",
            date_from: generalDates.from,
            date_to: generalDates.to,
        });
        console.log(
            "[DASH] loadDashboard productIds=" + JSON.stringify(productIds) +
            " dates=" + JSON.stringify(generalDates),
        );
        try {
            const [summaryResponse, hitsResponse, outsidersResponse, matrixResponse, actionsResponse] = await Promise.all([
                fetch(`${app.API_BASE}/api/dashboard/summary${summaryQuery}`),
                fetch(`${app.API_BASE}/api/dashboard/hits${buildQuery({ limit: 10, ...productQuery, date_from: generalDates.from, date_to: generalDates.to })}`),
                fetch(`${app.API_BASE}/api/dashboard/outsiders${buildQuery({ limit: 10, ...productQuery, date_from: generalDates.from, date_to: generalDates.to })}`),
                fetch(`${app.API_BASE}/api/dashboard/matrix${productQuery}`),
                fetch(`${app.API_BASE}/api/dashboard/actions${productQuery}`),
            ]);

            if (!summaryResponse.ok || !hitsResponse.ok || !outsidersResponse.ok || !matrixResponse.ok || !actionsResponse.ok) {
                const bad = [summaryResponse, hitsResponse, outsidersResponse, matrixResponse, actionsResponse].find((r) => !r.ok);
                console.warn(
                    "[DASH] backend returned " + (bad ? bad.status : "unknown") +
                    " for " + (bad ? bad.url : "") + " - keeping previous data",
                );
                return;
            }

            const [summary, hits, outsiders, matrix, actions] = await Promise.all([
                summaryResponse.json(),
                hitsResponse.json(),
                outsidersResponse.json(),
                matrixResponse.json(),
                actionsResponse.json(),
            ]);

            console.log(
                "[DASH] summary.products_count=" + (summary.products_count ?? "-") +
                " hits=" + (hits.hits ? hits.hits.length : 0) +
                " outsiders=" + (outsiders.outsiders ? outsiders.outsiders.length : 0) +
                " data_with_orders=" + (summary.data_with_orders_count ?? "-"),
            );

            app.setDashboardData({
                summary,
                hits: hits.hits,
                outsiders: outsiders.outsiders,
                matrix: matrix.matrix,
                matrixRules: matrix.rules || null,
                actions: actions.actions,
            });

            await loadFilterOptions();
            const availableIds = new Set(app.getProducts().map((p) => p.id));
            const currentSelection = app.getProductFilters("general");
            if (availableIds.size && currentSelection.length) {
                const stale = currentSelection.filter((id) => !availableIds.has(id));
                if (stale.length) {
                    console.warn("[DASH] product filter has stale IDs, resetting:", stale);
                    app.setProductFilters("general", []);
                }
            }
            app.renderCommandCenter();
        } catch (error) {
            console.error("[DASH] load error:", error);
        }
    }

    async function loadUnitEconomics(sectionId) {
        const apiKey = getWbApiKey();
        const dates = app.getDateFilters(sectionId);
        const productId = app.resolveUnitProduct(sectionId);

        if (!apiKey) {
            app.setUnitEconomicsData(sectionId, { state: "needs_token" });
            app.renderUnitEconomicsPage();
            return;
        }
        if (!productId) {
            app.setUnitEconomicsData(sectionId, { state: "needs_product" });
            app.renderUnitEconomicsPage();
            return;
        }
        if (!dates.from || !dates.to) {
            app.setUnitEconomicsData(sectionId, { error: "Для блока не задан период." });
            app.renderUnitEconomicsPage();
            return;
        }

        try {
            const response = await fetch(`${app.API_BASE}/api/unit-economics`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    wb_api_key: apiKey,
                    date_from: dates.from,
                    date_to: dates.to,
                    product_id: productId,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                app.setUnitEconomicsData(sectionId, { error: app.cleanText(data.detail) });
            } else {
                app.setUnitEconomicsData(sectionId, data);
            }
        } catch (error) {
            app.setUnitEconomicsData(sectionId, { error: "Ошибка загрузки юнит-экономики." });
        }

        app.renderUnitEconomicsPage();
    }

    async function loadUnitEconomicsPage() {
        app.renderUnitEconomicsPage();
        await Promise.all([
            loadUnitEconomics("ue_block1"),
            loadUnitEconomics("ue_block2"),
        ]);
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
                content.textContent = `Ошибка: ${app.cleanText(data.detail)}`;
            }
        } catch (error) {
            content.textContent = "Ошибка подключения к API.";
        } finally {
            button.disabled = false;
            button.innerHTML = "Получить анализ";
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
        getWbApiKey,
        initWbApi,
        loadDashboard,
        loadSummaryForSection,
        loadUnitEconomics,
        loadUnitEconomicsPage,
        resetData,
        toggleWbApiPanel,
        uploadFile,
    });

    window.toggleWbApiPanel = toggleWbApiPanel;
    window.fetchFromWbApi = fetchFromWbApi;
    window.getAIAnalysis = getAIAnalysis;
    window.resetData = resetData;
})();
