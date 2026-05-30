(function () {
    const app = window.WBApp;

    function downloadCSV(data, filename) {
        const bom = "\uFEFF";
        const csv = bom + data.map((row) => row.map((cell) => {
            const value = String(cell);
            if (value.includes(",") || value.includes('"') || value.includes("\n")) {
                return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        }).join(";")).join("\n");

        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    }

    function exportMatrixToExcel(category) {
        const dashboardData = app.getDashboardData();
        const data = dashboardData?.matrix?.[category];
        if (!data || !data.items?.length) {
            alert("Нет данных для выгрузки");
            return;
        }

        const categoryNames = {
            star: "Рост-лидеры",
            question: "Точки_роста",
            cash_cow: "Стабильный_доход",
            dog: "Слабые_позиции",
        };
        const headers = ["Артикул продавца", "Артикул WB", "Название", "Выручка", "Динамика %", "Заказы", "Остаток"];
        const rows = data.items.map((item) => [
            item.seller_article || "",
            item.wb_article || "",
            item.name || "",
            item.orders_value || 0,
            item.dynamics || 0,
            item.orders_qty || 0,
            item.stock || 0,
        ]);

        downloadCSV(
            [headers, ...rows],
            `Matrix_${categoryNames[category]}_${new Date().toISOString().split("T")[0]}.csv`,
        );
    }

    function exportActionsToExcel(type) {
        const dashboardData = app.getDashboardData();
        const actions = dashboardData?.actions;
        let items = [];

        if (!actions) {
            alert("Нет данных для выгрузки");
            return;
        }

        if (type === "all") {
            ["critical", "important", "opportunities"].forEach((currentType) => {
                const actionList = actions[currentType] || [];
                actionList.forEach((action) => {
                    if (action.items) {
                        action.items.forEach((item) => {
                            items.push({ ...item, action_type: currentType, action_title: action.title });
                        });
                    }
                });
            });
        } else {
            const actionList = actions[type] || [];
            actionList.forEach((action) => {
                if (action.items) {
                    action.items.forEach((item) => {
                        items.push({ ...item, action_type: type, action_title: action.title });
                    });
                }
            });
        }

        if (!items.length) {
            alert("Нет данных для выгрузки");
            return;
        }

        const headers = ["Тип", "Рекомендация", "Артикул продавца", "Артикул WB", "Название", "Выручка", "Динамика %"];
        const rows = items.map((item) => [
            item.action_type || "",
            item.action_title || "",
            item.seller_article || "",
            item.wb_article || "",
            item.name || "",
            item.orders_value || 0,
            item.dynamics || 0,
        ]);

        const typeNames = {
            critical: "Критичные",
            important: "Важные",
            opportunities: "Возможности",
            all: "Все",
        };
        downloadCSV(
            [headers, ...rows],
            `План_действий_${typeNames[type]}_${new Date().toISOString().split("T")[0]}.csv`,
        );
    }

    Object.assign(app, {
        exportActionsToExcel,
        exportMatrixToExcel,
    });

    window.exportMatrixToExcel = exportMatrixToExcel;
    window.exportActionsToExcel = exportActionsToExcel;
})();
