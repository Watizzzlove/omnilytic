(function () {
    const API_BASE = window.location.protocol === "file:"
        ? "http://127.0.0.1:8001"
        : window.location.origin;

    const state = {
        currentPage: "command",
        dashboardData: null,
        products: [],
        unitEconomics: {
            ue_block1: null,
            ue_block2: null,
        },
    };

    const sectionDates = {
        general: { from: "", to: "" },
        kpi: { from: "", to: "" },
        funnel: { from: "", to: "" },
        tables: { from: "", to: "" },
        ue_block1: { from: "", to: "" },
        ue_block2: { from: "", to: "" },
    };

    const productFilters = {
        general: [],
        kpi: [],
        funnel: [],
        tables: [],
        ue_block1: [],
        ue_block2: [],
    };

    const sectionOverrides = {
        kpi: { date: false, product: false },
        funnel: { date: false, product: false },
        tables: { date: false, product: false },
        ue_block1: { date: false, product: false },
        ue_block2: { date: false, product: false },
    };

    const hasNumber = (value) => typeof value === "number" && Number.isFinite(value);

    const formatNumber = (value, fallback = "0") => (
        hasNumber(value) ? value.toLocaleString("ru-RU") : fallback
    );

    const formatCurrency = (value, fallback = "N/A") => {
        if (!hasNumber(value)) return fallback;
        return `${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })} ₽`;
    };

    const formatDiff = (value, fallback = "") => {
        if (!hasNumber(value)) return fallback;
        const sign = value > 0 ? "+" : "";
        return `${sign}${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
    };

    const formatDynamics = (value, suffix = "%", fallback = "—") => (
        hasNumber(value)
            ? `${value > 0 ? "+" : ""}${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 1 })}${suffix}`
            : fallback
    );

    const formatPct = (value, fallback = "N/A") => (
        hasNumber(value)
            ? `${value.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`
            : fallback
    );

    const dynClass = (value) => {
        if (!hasNumber(value)) return "";
        if (value > 0) return "positive";
        if (value < 0) return "negative";
        return "";
    };

    const cp1252Controls = {
        0x20AC: 0x80,
        0x201A: 0x82,
        0x0192: 0x83,
        0x201E: 0x84,
        0x2026: 0x85,
        0x2020: 0x86,
        0x2021: 0x87,
        0x02C6: 0x88,
        0x2030: 0x89,
        0x0160: 0x8A,
        0x2039: 0x8B,
        0x0152: 0x8C,
        0x017D: 0x8E,
        0x2018: 0x91,
        0x2019: 0x92,
        0x201C: 0x93,
        0x201D: 0x94,
        0x2022: 0x95,
        0x2013: 0x96,
        0x2014: 0x97,
        0x02DC: 0x98,
        0x2122: 0x99,
        0x0161: 0x9A,
        0x203A: 0x9B,
        0x0153: 0x9C,
        0x017E: 0x9E,
        0x0178: 0x9F,
    };

    const textDecoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;

    const cleanText = (value) => {
        if (typeof value !== "string" || !/[ГђГ‘ГѓГ‚]/.test(value) || !textDecoder) {
            return value;
        }

        const bytes = [];
        for (const char of value) {
            const code = char.charCodeAt(0);
            if (code <= 0xFF) bytes.push(code);
            else if (cp1252Controls[code]) bytes.push(cp1252Controls[code]);
            else return value;
        }

        try {
            return textDecoder.decode(new Uint8Array(bytes));
        } catch (error) {
            return value;
        }
    };

    const cloneDateRange = (value) => ({ from: value.from || "", to: value.to || "" });

    const propagateGeneralFilters = () => {
        const generalDates = cloneDateRange(sectionDates.general);
        const generalProducts = [...productFilters.general];

        Object.keys(sectionOverrides).forEach((sectionId) => {
            if (!sectionOverrides[sectionId].date) {
                sectionDates[sectionId] = cloneDateRange(generalDates);
            }
            if (!sectionOverrides[sectionId].product) {
                productFilters[sectionId] = [...generalProducts];
            }
        });
    };

    const getProductOption = (productId) => (
        state.products.find((item) => item.id === productId) || null
    );

    window.WBApp = window.WBApp || {};
    Object.assign(window.WBApp, {
        API_BASE,
        cleanText,
        dynClass,
        formatCurrency,
        formatDiff,
        formatDynamics,
        formatNumber,
        formatPct,
        getCurrentPage() {
            return state.currentPage;
        },
        setCurrentPage(pageId) {
            state.currentPage = pageId;
        },
        hasNumber,
        getDashboardData() {
            return state.dashboardData;
        },
        setDashboardData(data) {
            state.dashboardData = data;
            return state.dashboardData;
        },
        getProducts() {
            return state.products;
        },
        setProducts(products) {
            state.products = Array.isArray(products) ? products : [];
        },
        getProductOption,
        getDateFilters(sectionId) {
            return cloneDateRange(sectionDates[sectionId] || sectionDates.general);
        },
        setDateFilters(filters, sectionId, options = {}) {
            const target = sectionId && sectionDates[sectionId] ? sectionId : "general";
            if (filters.from !== undefined) sectionDates[target].from = filters.from;
            if (filters.to !== undefined) sectionDates[target].to = filters.to;
            if (target !== "general" && options.markOverride !== false) {
                sectionOverrides[target].date = true;
            }
            if (target === "general") {
                propagateGeneralFilters();
            }
        },
        resetDateOverride(sectionId) {
            if (!sectionOverrides[sectionId]) return;
            sectionOverrides[sectionId].date = false;
            sectionDates[sectionId] = cloneDateRange(sectionDates.general);
        },
        getProductFilters(sectionId) {
            if (sectionId && productFilters[sectionId]) return [...productFilters[sectionId]];
            return [];
        },
        setProductFilters(sectionId, selected, options = {}) {
            const target = sectionId && productFilters[sectionId] ? sectionId : "general";
            productFilters[target] = Array.isArray(selected) ? [...selected] : [];
            if (target !== "general" && options.markOverride !== false) {
                sectionOverrides[target].product = true;
            }
            if (target === "general") {
                propagateGeneralFilters();
            }
        },
        resetProductOverride(sectionId) {
            if (!sectionOverrides[sectionId]) return;
            sectionOverrides[sectionId].product = false;
            productFilters[sectionId] = [...productFilters.general];
        },
        getSectionOverrides(sectionId) {
            return sectionOverrides[sectionId] || { date: false, product: false };
        },
        getUnitEconomicsData(sectionId) {
            return state.unitEconomics[sectionId] || null;
        },
        setUnitEconomicsData(sectionId, payload) {
            state.unitEconomics[sectionId] = payload;
            return state.unitEconomics[sectionId];
        },
        resolveUnitProduct(sectionId) {
            const local = productFilters[sectionId] || [];
            if (local.length === 1) return local[0];
            const general = productFilters.general || [];
            if (general.length === 1) return general[0];
            return null;
        },
    });
})();
