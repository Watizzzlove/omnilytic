(function () {
    const API_BASE = (
        window.location.protocol === "file:"
        || window.location.hostname === "localhost"
        || window.location.hostname === "127.0.0.1"
    )
        ? "http://localhost:8001"
        : window.location.origin;

    const state = {
        dashboardData: null,
    };

    const dateFilters = { from: "", to: "" };
    const sectionDates = { general: { from: "", to: "" }, kpi: { from: "", to: "" }, funnel: { from: "", to: "" }, tables: { from: "", to: "" } };
    const productFilters = { general: [], kpi: [], funnel: [], tables: [] };

    const hasNumber = (value) => typeof value === "number" && Number.isFinite(value);

    const formatNumber = (value, fallback = "0") => (
        hasNumber(value) ? value.toLocaleString("ru-RU") : fallback
    );

    const formatCurrency = (value, fallback = "N/A") => {
        if (!hasNumber(value)) {
            return fallback;
        }
        if (Math.abs(value) >= 1000000) {
            return `${(value / 1000000).toFixed(1)} млн ₽`;
        }
        if (Math.abs(value) >= 1000) {
            return `${Math.round(value / 1000)} тыс ₽`;
        }
        return `${formatNumber(value)} ₽`;
    };

    const formatDiff = (value, fallback = "") => {
        if (!hasNumber(value)) {
            return fallback;
        }
        const sign = value > 0 ? "+" : "";
        if (Math.abs(value) >= 1000000) {
            return `${sign}${(value / 1000000).toFixed(1)} млн`;
        }
        if (Math.abs(value) >= 1000) {
            return `${sign}${Math.round(value / 1000)} тыс`;
        }
        return `${sign}${formatNumber(value)}`;
    };

    const formatDynamics = (value, suffix = "%", fallback = "—") => (
        hasNumber(value) ? `${value > 0 ? "+" : ""}${value.toFixed(1)}${suffix}` : fallback
    );

    const formatPct = (value, fallback = "N/A") => (
        hasNumber(value) ? `${value.toFixed(1)}%` : fallback
    );

    const dynClass = (value) => {
        if (!hasNumber(value)) {
            return "";
        }
        if (value > 0) {
            return "positive";
        }
        if (value < 0) {
            return "negative";
        }
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
        if (typeof value !== "string" || !/[ÐÑÃÂ]/.test(value) || !textDecoder) {
            return value;
        }

        const bytes = [];
        for (const char of value) {
            const code = char.charCodeAt(0);
            if (code <= 0xFF) {
                bytes.push(code);
            } else if (cp1252Controls[code]) {
                bytes.push(cp1252Controls[code]);
            } else {
                return value;
            }
        }

        try {
            return textDecoder.decode(new Uint8Array(bytes));
        } catch (error) {
            return value;
        }
    };

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
        hasNumber,
        getDashboardData() {
            return state.dashboardData;
        },
        setDashboardData(data) {
            state.dashboardData = data;
            return state.dashboardData;
        },
        getDateFilters(sectionId) {
            if (sectionId && sectionDates[sectionId]) return sectionDates[sectionId];
            return dateFilters;
        },
        setDateFilters(f, sectionId) {
            if (sectionId && sectionDates[sectionId]) {
                if (f.from !== undefined) sectionDates[sectionId].from = f.from;
                if (f.to !== undefined) sectionDates[sectionId].to = f.to;
            }
            if (f.from !== undefined) dateFilters.from = f.from;
            if (f.to !== undefined) dateFilters.to = f.to;
        },
        propagateSectionDates(sectionId) {
            if (!sectionId || !sectionDates[sectionId]) return;
            const d = sectionDates[sectionId];
            for (const id of ["general", "kpi", "funnel", "tables"]) {
                sectionDates[id].from = d.from;
                sectionDates[id].to = d.to;
            }
            dateFilters.from = d.from;
            dateFilters.to = d.to;
        },
        getProductFilters(sectionId) {
            if (sectionId && productFilters[sectionId]) return productFilters[sectionId];
            if (sectionId) return [];
            return productFilters;
        },
        setProductFilters(sectionId, selected) {
            if (sectionId && selected !== undefined) productFilters[sectionId] = selected;
        },
    });
})();
