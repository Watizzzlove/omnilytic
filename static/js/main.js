(function () {
    const app = window.WBApp;

    function initTabs() {
        document.querySelectorAll(".tab").forEach((tab) => {
            tab.addEventListener("click", () => {
                document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
                document.querySelectorAll(".tab-content").forEach((content) => content.classList.remove("active"));
                tab.classList.add("active");
                document.getElementById(tab.dataset.tab).classList.add("active");
            });
        });
    }

    function initUploadZone() {
        const uploadZone = document.getElementById("uploadZone");
        const fileInput = document.getElementById("fileInput");

        uploadZone.addEventListener("dragover", (event) => {
            event.preventDefault();
            uploadZone.classList.add("dragover");
        });

        uploadZone.addEventListener("dragleave", () => {
            uploadZone.classList.remove("dragover");
        });

        uploadZone.addEventListener("drop", (event) => {
            event.preventDefault();
            uploadZone.classList.remove("dragover");
            if (event.dataTransfer.files[0]) {
                app.uploadFile(event.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener("change", (event) => {
            if (event.target.files[0]) {
                app.uploadFile(event.target.files[0]);
            }
        });
    }

    function initDateFilters() {
        const today = new Date();
        const weekAgo = new Date(today);
        weekAgo.setDate(today.getDate() - 7);
        const formatDate = (date) => date.toISOString().split("T")[0];

        const fromVal = formatDate(weekAgo);
        const toVal = formatDate(today);

        app.setDateFilters({ from: fromVal, to: toVal }, "general");
        app.propagateSectionDates("general");
    }

    function closeAllProductDropdowns() {
        document.querySelectorAll(".product-dropdown-panel.open").forEach(p => p.classList.remove("open"));
    }

    window.toggleProductDropdown = function (btn) {
        const panel = btn.parentElement.querySelector(".product-dropdown-panel");
        if (!panel) return;
        const isOpen = panel.classList.contains("open");
        closeAllProductDropdowns();
        if (!isOpen) panel.classList.add("open");
    };

    window.toggleProductItem = function (el) {
        el.classList.toggle("selected");
        const check = el.querySelector(".checkmark");
        if (check) check.textContent = el.classList.contains("selected") ? "✓" : "";
    };

    window.applyProductFilters = function (sectionId) {
        const container = document.querySelector(`.product-dropdown[data-section="${sectionId}"]`);
        if (!container) return;
        const items = container.querySelectorAll(".product-dropdown-item.selected");
        const selected = Array.from(items).map(item => item.dataset.id);

        if (sectionId === "general") {
            for (const id of ["kpi", "funnel", "tables", "general"]) {
                app.setProductFilters(id, selected);
            }
            closeAllProductDropdowns();
            updateDropdownButtons();
            const ids = selected.join(",");
            if (ids) {
                app.loadDashboard(ids);
            } else {
                app.loadDashboard();
            }
        } else if (sectionId === "tables") {
            app.setProductFilters(sectionId, selected);
            closeAllProductDropdowns();
            updateDropdownButtons();
            app.renderCommandCenter();
        } else {
            app.setProductFilters(sectionId, selected);
            closeAllProductDropdowns();
            updateDropdownButtons();
            app.loadSummaryForSection(sectionId);
        }
    };

    window.resetProductFilters = function (sectionId) {
        if (sectionId === "general") {
            for (const id of ["kpi", "funnel", "tables", "general"]) {
                app.setProductFilters(id, []);
            }
            closeAllProductDropdowns();
            updateDropdownButtons();
            app.loadDashboard();
        } else {
            app.setProductFilters(sectionId, []);
            closeAllProductDropdowns();
            const container = document.querySelector(`.product-dropdown[data-section="${sectionId}"]`);
            if (container) {
                container.querySelectorAll(".product-dropdown-item.selected").forEach(el => {
                    el.classList.remove("selected");
                    const check = el.querySelector(".checkmark");
                    if (check) check.textContent = "";
                });
            }
            updateDropdownButtons();
            app.renderCommandCenter();
        }
    };

    function updateDropdownButtons() {
        document.querySelectorAll(".product-dropdown").forEach(dd => {
            const sectionId = dd.dataset.section;
            const raw = app.getProductFilters(sectionId);
            const selected = Array.isArray(raw) ? raw : [];
            const hasFilters = selected.length > 0;
            const text = hasFilters ? `выбраны товары (${selected.length})` : "фильтр по товарам";
            const btn = dd.querySelector(".product-dropdown-btn");
            if (btn) {
                btn.textContent = text;
                if (hasFilters) btn.classList.add("active"); else btn.classList.remove("active");
            }
        });
    }

    window.applyDateFilter = function (sectionId) {
        const filter = document.querySelector(`.date-filter[data-section="${sectionId}"]`);
        if (!filter) return;
        const dateFrom = filter.querySelector(".df-from")?.value;
        const dateTo = filter.querySelector(".df-to")?.value;
        if (!dateFrom || !dateTo) return;

        const apiKey = document.getElementById("wbApiKey")?.value.trim();
        if (!apiKey) {
            const bar = document.getElementById("wbApiBar");
            if (bar) bar.scrollIntoView({ behavior: "smooth" });
            alert("Для смены дат нужен WB API ключ. Введите его в панели WB API сверху.");
            return;
        }

        app.setDateFilters({ from: dateFrom, to: dateTo }, sectionId);
        if (sectionId === "general") {
            app.propagateSectionDates("general");
        }
        app.fetchFromWbApi(sectionId);
    };

    document.addEventListener("click", function (e) {
        if (!e.target.closest(".product-dropdown")) {
            closeAllProductDropdowns();
        }
    });

    function initialize() {
        initTabs();
        initUploadZone();
        initDateFilters();
        app.initWbApi();
        app.checkHealth();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
