(function () {
    const app = window.WBApp;

    function renderHeaderFilters() {
        const container = document.getElementById("headerFilters");
        if (!container || typeof app.renderDateFilter !== "function") return;
        container.innerHTML = app.renderDateFilter("general", {
            compact: true,
            placeholder: "Все товары",
        });
    }

    function closeAllProductDropdowns() {
        document.querySelectorAll(".product-dropdown-panel.open").forEach((panel) => panel.classList.remove("open"));
    }

    function switchPage(pageId) {
        app.setCurrentPage(pageId);
        document.querySelectorAll(".page-nav-link").forEach((button) => {
            button.classList.toggle("active", button.dataset.page === pageId);
        });
        document.querySelectorAll(".page-section").forEach((section) => {
            section.classList.toggle("active", section.id === `${pageId}Page`);
        });

        if (pageId === "command") {
            app.renderCommandCenter();
        } else if (pageId === "unit") {
            app.loadUnitEconomicsPage();
        } else if (pageId === "geo") {
            const geo = document.getElementById("geoAnalyticsContent");
            if (geo) {
                geo.innerHTML = `
                    <div class="section-wrapper block-cream">
                        <div class="section-header">
                            <div class="section-title-group">
                                <span class="section-title">Гео-аналитика</span>
                                <div class="section-desc">Раздел уже добавлен в навигацию и готов под следующее наполнение.</div>
                            </div>
                        </div>
                        <div class="empty-state">
                            <div class="empty-state-icon">MAP</div>
                            <div class="empty-state-title">Пока пусто</div>
                            <p>Страница подготовлена как отдельный раздел без наполнения.</p>
                        </div>
                    </div>
                `;
            }
        }
    }

    function initNavigation() {
        document.querySelectorAll(".page-nav-link").forEach((button) => {
            button.addEventListener("click", () => switchPage(button.dataset.page));
        });
    }

    function initDateFilters() {
        const today = new Date();
        const weekAgo = new Date(today);
        weekAgo.setDate(today.getDate() - 7);
        const formatDate = (date) => date.toISOString().split("T")[0];

        app.setDateFilters(
            { from: formatDate(weekAgo), to: formatDate(today) },
            "general",
        );
    }

    function updateDropdownButtons() {
        document.querySelectorAll(".product-dropdown").forEach((dropdown) => {
            const sectionId = dropdown.dataset.section;
            const selected = app.getProductFilters(sectionId);
            const single = dropdown.dataset.single === "true";
            const button = dropdown.querySelector(".product-dropdown-btn");
            if (!button) return;

            let label = "Все товары";
            if (selected.length) {
                if (single) {
                    const option = app.getProductOption(selected[0]);
                    label = option?.label || selected[0];
                } else {
                    label = `Выбрано товаров: ${selected.length}`;
                }
            } else if (single) {
                label = "Выберите один товар";
            }

            button.textContent = label;
            button.classList.toggle("active", selected.length > 0);
        });
    }

    window.toggleProductDropdown = function (button) {
        const panel = button.parentElement.querySelector(".product-dropdown-panel");
        if (!panel) return;
        const isOpen = panel.classList.contains("open");
        closeAllProductDropdowns();
        if (!isOpen) panel.classList.add("open");
    };

    window.filterProductDropdown = function (input) {
        const panel = input.closest(".product-dropdown-panel");
        if (!panel) return;
        const query = input.value.trim().toLowerCase();
        panel.querySelectorAll(".product-dropdown-item").forEach((item) => {
            const haystack = item.dataset.search || "";
            const shouldHide = Boolean(query) && !haystack.includes(query);
            // Инлайновый display перебивает CSS-правило .product-dropdown-item { display: flex },
            // из-за которого атрибут hidden не работал.
            item.style.display = shouldHide ? "none" : "";
        });
    };

    window.toggleProductItem = function (element) {
        const dropdown = element.closest(".product-dropdown");
        if (!dropdown) return;
        const isSingle = dropdown.dataset.single === "true";
        const itemId = element.dataset.id;

        if (itemId === "__all__") {
            const shouldSelect = !element.classList.contains("selected");
            dropdown.querySelectorAll(".product-dropdown-item").forEach((item) => {
                item.classList.remove("selected");
                const check = item.querySelector(".checkmark");
                if (check) check.textContent = "";
            });
            if (shouldSelect) {
                element.classList.add("selected");
                const check = element.querySelector(".checkmark");
                if (check) check.textContent = "✓";
            }
            return;
        }

        if (isSingle) {
            dropdown.querySelectorAll(".product-dropdown-item.selected").forEach((item) => {
                if (item !== element) {
                    item.classList.remove("selected");
                    const check = item.querySelector(".checkmark");
                    if (check) check.textContent = "";
                }
            });
        }

        const allOption = dropdown.querySelector('.product-dropdown-item[data-id="__all__"]');
        if (allOption) {
            allOption.classList.remove("selected");
            const allCheck = allOption.querySelector(".checkmark");
            if (allCheck) allCheck.textContent = "";
        }

        element.classList.toggle("selected");
        const check = element.querySelector(".checkmark");
        if (check) check.textContent = element.classList.contains("selected") ? "✓" : "";
    };

    function refreshCurrentPage() {
        const page = app.getCurrentPage();
        if (page === "command") {
            const ids = app.getProductFilters("general").join(",");
            app.loadDashboard(ids || undefined);
        } else if (page === "unit") {
            app.loadUnitEconomicsPage();
        } else {
            switchPage(page);
        }
    }

    window.applyProductFilters = function (sectionId) {
        const container = document.querySelector(`.product-dropdown[data-section="${sectionId}"]`);
        if (!container) return;
        const selected = Array.from(container.querySelectorAll(".product-dropdown-item.selected"))
            .map((item) => item.dataset.id);
        const normalized = selected.includes("__all__") ? [] : selected;
        console.log("[APPLY] product filter " + sectionId + " -> " + JSON.stringify(normalized));

        if (sectionId === "general") {
            app.setProductFilters(sectionId, normalized);
        } else {
            app.setProductFilters(sectionId, normalized, { markOverride: true });
        }

        closeAllProductDropdowns();
        updateDropdownButtons();

        if (sectionId === "tables") {
            refreshCurrentPage();
        } else if (sectionId === "kpi" || sectionId === "funnel") {
            app.loadSummaryForSection(sectionId);
        } else if (sectionId === "ue_block1" || sectionId === "ue_block2") {
            app.loadUnitEconomics(sectionId);
        } else {
            refreshCurrentPage();
        }
    };

    window.resetProductFilters = function (sectionId) {
        const container = document.querySelector(`.product-dropdown[data-section="${sectionId}"]`);
        if (sectionId === "general") {
            app.setProductFilters("general", []);
        } else {
            app.resetProductOverride(sectionId);
        }

        if (container) {
            const current = app.getProductFilters(sectionId);
            container.querySelectorAll(".product-dropdown-item").forEach((item) => {
                const shouldSelect = item.dataset.id === "__all__"
                    ? current.length === 0 && container.dataset.single !== "true"
                    : current.includes(item.dataset.id);
                item.classList.toggle("selected", shouldSelect);
                const check = item.querySelector(".checkmark");
                if (check) check.textContent = shouldSelect ? "✓" : "";
                item.style.display = "";
            });
            const searchInput = container.querySelector(".product-dropdown-search input");
            if (searchInput) searchInput.value = "";
        }

        closeAllProductDropdowns();
        updateDropdownButtons();

        if (sectionId === "kpi" || sectionId === "funnel") {
            app.loadSummaryForSection(sectionId);
        } else if (sectionId === "ue_block1" || sectionId === "ue_block2") {
            app.loadUnitEconomics(sectionId);
        } else {
            refreshCurrentPage();
        }
    };

    window.applyDateFilter = function (sectionId) {
        const scope = document.querySelector(`.filter-stack[data-section="${sectionId}"]`);
        if (!scope) return;

        const dateFrom = scope.querySelector(".df-from")?.value;
        const dateTo = scope.querySelector(".df-to")?.value;
        if (!dateFrom || !dateTo) {
            console.warn("[APPLY] date filter " + sectionId + " missing dates - skipped");
            return;
        }
        console.log("[APPLY] date filter " + sectionId + " from=" + dateFrom + " to=" + dateTo);

        app.setDateFilters(
            { from: dateFrom, to: dateTo },
            sectionId,
            { markOverride: sectionId !== "general" },
        );

        if (sectionId === "kpi" || sectionId === "funnel") {
            app.loadSummaryForSection(sectionId);
        } else if (sectionId === "ue_block1" || sectionId === "ue_block2") {
            app.loadUnitEconomics(sectionId);
        } else {
            refreshCurrentPage();
        }
    };

    window.resetDateFilter = function (sectionId) {
        if (sectionId === "general") return;
        app.resetDateOverride(sectionId);
        app.renderCommandCenter();
        if (app.getCurrentPage() === "unit") {
            app.renderUnitEconomicsPage();
            app.loadUnitEconomics(sectionId);
        }
    };

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".product-dropdown")) {
            closeAllProductDropdowns();
        }
    });

    function initialize() {
        initNavigation();
        initDateFilters();
        renderHeaderFilters();
        updateDropdownButtons();
        app.renderHeaderFilters = renderHeaderFilters;
        app.initWbApi();
        app.checkHealth();
        switchPage("command");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
