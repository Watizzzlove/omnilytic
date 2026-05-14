"""
WB Sales Intelligence Dashboard - Backend API
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import pandas as pd
import json
from typing import Optional
import os
from datetime import datetime
import httpx
from anthropic import Anthropic
from pydantic import BaseModel
from wb_api_client import fetch_sales_funnel, map_api_to_internal

app = FastAPI(title="WB Sales Intelligence API", version="1.0.0")

# Путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальное хранилище данных (в production использовать БД)
DATA_STORE = {
    "raw_data": None,
    "processed_data": None,
    "upload_date": None,
    "period": None
}

# Маппинг колонок
COLUMN_MAPPING = {
    "Артикул продавца": "seller_article",
    "Артикул WB": "wb_article",
    "Название": "name",
    "Предмет": "category",
    "Бренд": "brand",
    "Удаленный товар": "is_deleted",
    "Рейтинг карточки": "card_rating",
    "Рейтинг по отзывам": "review_rating",
    "Показы": "impressions",
    "Показы (предыдущий период)": "impressions_prev",
    "CTR": "ctr",
    "CTR (предыдущий период)": "ctr_prev",
    "Переходы в карточку": "card_views",
    "Переходы в карточку (предыдущий период)": "card_views_prev",
    "Доля карточки в выручке": "revenue_share",
    "Доля карточки в выручке (предыдущий период)": "revenue_share_prev",
    "Положили в корзину": "add_to_cart",
    "Положили в корзину (предыдущий период)": "add_to_cart_prev",
    "Добавили в отложенные": "add_to_favorites",
    "Добавили в отложенные (предыдущий период)": "add_to_favorites_prev",
    "Заказали, шт": "orders_qty",
    "Заказали, шт (предыдущий период)": "orders_qty_prev",
    "Выкупили, шт": "purchased_qty",
    "Выкупы, шт (предыдущий период)": "purchased_qty_prev",
    "Отменили, шт": "cancelled_qty",
    "Отменили, шт (предыдущий период)": "cancelled_qty_prev",
    "Конверсия в корзину, %": "cart_conversion",
    "Конверсия в корзину, % (предыдущий период)": "cart_conversion_prev",
    "Конверсия в заказ, %": "order_conversion",
    "Конверсия в заказ, % (предыдущий период)": "order_conversion_prev",
    "Процент выкупа": "purchase_rate",
    "Процент выкупа (предыдущий период)": "purchase_rate_prev",
    "Заказали на сумму, ₽": "orders_value",
    "Заказали на сумму, ₽ (предыдущий период)": "orders_value_prev",
    "Динамика суммы заказов, ₽": "orders_dynamics",
    "Выкупили на сумму, ₽": "purchased_value",
    "Выкупили на сумму, ₽ (предыдущий период)": "purchased_value_prev",
    "Отменили на сумму, ₽": "cancelled_value",
    "Отменили на сумму, ₽ (предыдущий период)": "cancelled_value_prev",
    "Средняя цена, ₽": "avg_price",
    "Средняя цена, ₽ (предыдущий период)": "avg_price_prev",
    "Среднее количество заказов в день, шт": "avg_daily_orders",
    "Среднее количество заказов в день, шт (предыдущий период)": "avg_daily_orders_prev",
    "Остатки склад ВБ, шт": "stock_wb",
    "Остатки МП, шт": "stock_mp",
    "Сумма остатков на складах, ₽": "stock_value",
    "Среднее время доставки": "delivery_time",
    "Среднее время доставки (предыдущий период)": "delivery_time_prev",
    "Локальные заказы, %": "local_orders_pct",
    "Локальные заказы, % (предыдущий период)": "local_orders_pct_prev",
}


def safe_float(value, default=0.0):
    """Безопасное преобразование в float"""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Безопасное преобразование в int"""
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def calculate_dynamics(current, previous):
    """Расчет динамики в процентах"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)


def classify_product(row):
    """Классификация товара по матрице BCG"""
    orders_dynamics = calculate_dynamics(
        safe_int(row.get('orders_qty', 0)),
        safe_int(row.get('orders_qty_prev', 0))
    )
    orders_value = safe_int(row.get('orders_value', 0))

    # Пороговые значения
    high_dynamics = orders_dynamics > 10
    high_sales = orders_value > 10000  # Средний порог продаж

    if high_dynamics and high_sales:
        return "star"  # Звёзды
    elif high_dynamics and not high_sales:
        return "question"  # Вопросы
    elif not high_dynamics and high_sales:
        return "cash_cow"  # Дойные коровы
    else:
        return "dog"  # Собаки


def process_data(df):
    """Обработка загруженных данных"""
    # Переименовываем колонки
    df_renamed = df.rename(columns=COLUMN_MAPPING)

    # Добавляем расчетные поля
    records = df_renamed.to_dict('records')

    for record in records:
        # Динамика показателей
        record['impressions_dynamics'] = calculate_dynamics(
            safe_int(record.get('impressions', 0)),
            safe_int(record.get('impressions_prev', 0))
        )
        record['orders_dynamics_pct'] = calculate_dynamics(
            safe_int(record.get('orders_qty', 0)),
            safe_int(record.get('orders_qty_prev', 0))
        )
        record['revenue_dynamics_pct'] = calculate_dynamics(
            safe_int(record.get('orders_value', 0)),
            safe_int(record.get('orders_value_prev', 0))
        )

        # Классификация товара
        record['bcg_category'] = classify_product(record)

        # Общий остаток
        record['total_stock'] = safe_int(record.get('stock_wb', 0)) + safe_int(record.get('stock_mp', 0))

        # Упущенная выгода (если нет остатков, но были продажи)
        if record['total_stock'] == 0 and safe_int(record.get('orders_qty_prev', 0)) > 0:
            record['lost_revenue'] = safe_int(record.get('orders_value_prev', 0))
        else:
            record['lost_revenue'] = 0

    return records


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка Excel файла с данными"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Только Excel файлы (.xlsx, .xls)")

    try:
        # Читаем файл
        contents = await file.read()
        df = pd.read_excel(contents, sheet_name=0)

        # Обрабатываем данные
        processed = process_data(df)

        # Сохраняем в хранилище
        DATA_STORE["raw_data"] = df.to_dict('records')
        DATA_STORE["processed_data"] = processed
        DATA_STORE["upload_date"] = datetime.now().isoformat()
        DATA_STORE["filename"] = file.filename

        return {
            "success": True,
            "message": f"Загружено {len(processed)} товаров",
            "products_count": len(processed),
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Получение сводных KPI для дашборда с средневзвешенными показателями"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    # ===== ФИЛЬТРУЕМ ТОВАРЫ С ЗАКАЗАМИ (для расчета показателей) =====
    # Товары с заказами в текущем периоде
    data_with_orders = [r for r in data if safe_int(r.get('orders_qty', 0)) > 0]
    # Товары с заказами в предыдущем периоде
    data_with_orders_prev = [r for r in data if safe_int(r.get('orders_qty_prev', 0)) > 0]

    # ===== БАЗОВЫЕ СУММЫ (только по товарам с заказами) =====
    # Выручка
    total_orders_value = sum(safe_int(r.get('orders_value', 0)) for r in data_with_orders)
    total_orders_value_prev = sum(safe_int(r.get('orders_value_prev', 0)) for r in data_with_orders_prev)

    # Заказы (шт)
    total_orders_qty = sum(safe_int(r.get('orders_qty', 0)) for r in data_with_orders)
    total_orders_qty_prev = sum(safe_int(r.get('orders_qty_prev', 0)) for r in data_with_orders_prev)

    # Выкупы (шт) - только по товарам с заказами
    total_purchased_qty = sum(safe_int(r.get('purchased_qty', 0)) for r in data_with_orders)
    total_purchased_qty_prev = sum(safe_int(r.get('purchased_qty_prev', 0)) for r in data_with_orders_prev)

    # Выкупы (руб)
    total_purchased_value = sum(safe_int(r.get('purchased_value', 0)) for r in data_with_orders)
    total_purchased_value_prev = sum(safe_int(r.get('purchased_value_prev', 0)) for r in data_with_orders_prev)

    # Отмены - только по товарам с заказами
    total_cancelled_qty = sum(safe_int(r.get('cancelled_qty', 0)) for r in data_with_orders)
    total_cancelled_qty_prev = sum(safe_int(r.get('cancelled_qty_prev', 0)) for r in data_with_orders_prev)
    total_cancelled_value = sum(safe_int(r.get('cancelled_value', 0)) for r in data_with_orders)
    total_cancelled_value_prev = sum(safe_int(r.get('cancelled_value_prev', 0)) for r in data_with_orders_prev)

    # Воронка - текущий период (только по товарам с заказами)
    total_impressions = sum(safe_int(r.get('impressions', 0)) for r in data_with_orders)
    total_card_views = sum(safe_int(r.get('card_views', 0)) for r in data_with_orders)
    total_add_to_cart = sum(safe_int(r.get('add_to_cart', 0)) for r in data_with_orders)
    total_favorites = sum(safe_int(r.get('add_to_favorites', 0)) for r in data_with_orders)

    # Воронка - предыдущий период (только по товарам с заказами в пред. периоде)
    total_impressions_prev = sum(safe_int(r.get('impressions_prev', 0)) for r in data_with_orders_prev)
    total_card_views_prev = sum(safe_int(r.get('card_views_prev', 0)) for r in data_with_orders_prev)
    total_add_to_cart_prev = sum(safe_int(r.get('add_to_cart_prev', 0)) for r in data_with_orders_prev)
    total_favorites_prev = sum(safe_int(r.get('add_to_favorites_prev', 0)) for r in data_with_orders_prev)

    # Остатки - ПО ВСЕМ ТОВАРАМ (не фильтруем)
    total_stock_value = sum(safe_int(r.get('stock_value', 0)) for r in data)
    total_stock_qty = sum(safe_int(r.get('total_stock', 0)) for r in data)

    # Количество товаров с заказами
    products_with_orders_count = len(data_with_orders)
    products_with_orders_count_prev = len(data_with_orders_prev)

    # ===== СРЕДНЕВЗВЕШЕННЫЕ ПОКАЗАТЕЛИ =====
    # CTR = (переходы / показы) * 100 — средневзвешенный по показам
    avg_ctr = round((total_card_views / total_impressions * 100), 2) if total_impressions > 0 else 0
    avg_ctr_prev = round((total_card_views_prev / total_impressions_prev * 100), 2) if total_impressions_prev > 0 else 0

    # Конверсия в корзину = (корзина / переходы) * 100
    cart_conversion = round((total_add_to_cart / total_card_views * 100), 2) if total_card_views > 0 else 0
    cart_conversion_prev = round((total_add_to_cart_prev / total_card_views_prev * 100), 2) if total_card_views_prev > 0 else 0

    # Конверсия в заказ = (заказы / корзина) * 100
    order_conversion = round((total_orders_qty / total_add_to_cart * 100), 2) if total_add_to_cart > 0 else 0
    order_conversion_prev = round((total_orders_qty_prev / total_add_to_cart_prev * 100), 2) if total_add_to_cart_prev > 0 else 0

    # Процент выкупа - средневзвешенный по заказам из колонки файла
    # (т.к. выкуп происходит с задержкой, нельзя делить выкупы этой недели на заказы этой недели)
    weighted_purchase_rate = sum(safe_float(r.get('purchase_rate', 0)) * safe_int(r.get('orders_qty', 0)) for r in data_with_orders)
    purchase_rate = round(weighted_purchase_rate / total_orders_qty, 1) if total_orders_qty > 0 else 0

    weighted_purchase_rate_prev = sum(safe_float(r.get('purchase_rate_prev', 0)) * safe_int(r.get('orders_qty_prev', 0)) for r in data_with_orders_prev)
    purchase_rate_prev = round(weighted_purchase_rate_prev / total_orders_qty_prev, 1) if total_orders_qty_prev > 0 else 0

    # Процент отмен = (отмены шт / заказы шт) * 100
    cancel_rate = round((total_cancelled_qty / total_orders_qty * 100), 1) if total_orders_qty > 0 else 0
    cancel_rate_prev = round((total_cancelled_qty_prev / total_orders_qty_prev * 100), 1) if total_orders_qty_prev > 0 else 0

    # Средний чек = выручка / заказы
    avg_order_value = round(total_orders_value / total_orders_qty) if total_orders_qty > 0 else 0
    avg_order_value_prev = round(total_orders_value_prev / total_orders_qty_prev) if total_orders_qty_prev > 0 else 0

    # Средневзвешенная цена (по количеству заказов) - только по товарам с заказами
    weighted_price_sum = sum(safe_int(r.get('avg_price', 0)) * safe_int(r.get('orders_qty', 0)) for r in data_with_orders)
    weighted_price_sum_prev = sum(safe_int(r.get('avg_price_prev', 0)) * safe_int(r.get('orders_qty_prev', 0)) for r in data_with_orders_prev)
    avg_price_weighted = round(weighted_price_sum / total_orders_qty) if total_orders_qty > 0 else 0
    avg_price_weighted_prev = round(weighted_price_sum_prev / total_orders_qty_prev) if total_orders_qty_prev > 0 else 0

    # ===== ВОРОНКА С ДИНАМИКОЙ =====
    funnel = {
        "impressions": {
            "value": total_impressions,
            "prev": total_impressions_prev,
            "dynamics": calculate_dynamics(total_impressions, total_impressions_prev)
        },
        "card_views": {
            "value": total_card_views,
            "prev": total_card_views_prev,
            "dynamics": calculate_dynamics(total_card_views, total_card_views_prev)
        },
        "add_to_cart": {
            "value": total_add_to_cart,
            "prev": total_add_to_cart_prev,
            "dynamics": calculate_dynamics(total_add_to_cart, total_add_to_cart_prev)
        },
        "favorites": {
            "value": total_favorites,
            "prev": total_favorites_prev,
            "dynamics": calculate_dynamics(total_favorites, total_favorites_prev)
        },
        "orders": {
            "value": total_orders_qty,
            "prev": total_orders_qty_prev,
            "dynamics": calculate_dynamics(total_orders_qty, total_orders_qty_prev)
        },
        "purchased": {
            "value": total_purchased_qty,
            "prev": total_purchased_qty_prev,
            "dynamics": calculate_dynamics(total_purchased_qty, total_purchased_qty_prev)
        },
        "cancelled": {
            "value": total_cancelled_qty,
            "prev": total_cancelled_qty_prev,
            "dynamics": calculate_dynamics(total_cancelled_qty, total_cancelled_qty_prev)
        },
        # Конверсии с динамикой
        "conversions": {
            "ctr": {
                "value": avg_ctr,
                "prev": avg_ctr_prev,
                "dynamics": round(avg_ctr - avg_ctr_prev, 2)
            },
            "cart_rate": {
                "value": cart_conversion,
                "prev": cart_conversion_prev,
                "dynamics": round(cart_conversion - cart_conversion_prev, 2)
            },
            "order_rate": {
                "value": order_conversion,
                "prev": order_conversion_prev,
                "dynamics": round(order_conversion - order_conversion_prev, 2)
            },
            "purchase_rate": {
                "value": purchase_rate,
                "prev": purchase_rate_prev,
                "dynamics": round(purchase_rate - purchase_rate_prev, 1)
            },
            "cancel_rate": {
                "value": cancel_rate,
                "prev": cancel_rate_prev,
                "dynamics": round(cancel_rate - cancel_rate_prev, 1)
            }
        }
    }

    return {
        "kpi": {
            "revenue": {
                "value": total_orders_value,
                "prev": total_orders_value_prev,
                "dynamics": calculate_dynamics(total_orders_value, total_orders_value_prev),
                "diff": total_orders_value - total_orders_value_prev
            },
            "orders": {
                "value": total_orders_qty,
                "prev": total_orders_qty_prev,
                "dynamics": calculate_dynamics(total_orders_qty, total_orders_qty_prev),
                "diff": total_orders_qty - total_orders_qty_prev
            },
            "purchased_value": {
                "value": total_purchased_value,
                "prev": total_purchased_value_prev,
                "dynamics": calculate_dynamics(total_purchased_value, total_purchased_value_prev),
                "diff": total_purchased_value - total_purchased_value_prev
            },
            "purchased_qty": {
                "value": total_purchased_qty,
                "prev": total_purchased_qty_prev,
                "dynamics": calculate_dynamics(total_purchased_qty, total_purchased_qty_prev),
                "diff": total_purchased_qty - total_purchased_qty_prev
            },
            "purchase_rate": {
                "value": purchase_rate,
                "prev": purchase_rate_prev,
                "dynamics": round(purchase_rate - purchase_rate_prev, 1)
            },
            "cancel_rate": {
                "value": cancel_rate,
                "prev": cancel_rate_prev,
                "dynamics": round(cancel_rate - cancel_rate_prev, 1)
            },
            "cancelled_value": {
                "value": total_cancelled_value,
                "prev": total_cancelled_value_prev,
                "dynamics": calculate_dynamics(total_cancelled_value, total_cancelled_value_prev),
                "diff": total_cancelled_value - total_cancelled_value_prev
            },
            "avg_order_value": {
                "value": avg_order_value,
                "prev": avg_order_value_prev,
                "dynamics": calculate_dynamics(avg_order_value, avg_order_value_prev),
                "diff": avg_order_value - avg_order_value_prev
            },
            "avg_price": {
                "value": avg_price_weighted,
                "prev": avg_price_weighted_prev,
                "dynamics": calculate_dynamics(avg_price_weighted, avg_price_weighted_prev),
                "diff": avg_price_weighted - avg_price_weighted_prev
            },
            "ctr": {
                "value": avg_ctr,
                "prev": avg_ctr_prev,
                "dynamics": round(avg_ctr - avg_ctr_prev, 2)
            },
            "cart_conversion": {
                "value": cart_conversion,
                "prev": cart_conversion_prev,
                "dynamics": round(cart_conversion - cart_conversion_prev, 2)
            },
            "order_conversion": {
                "value": order_conversion,
                "prev": order_conversion_prev,
                "dynamics": round(order_conversion - order_conversion_prev, 2)
            },
            "stock": {
                "value": total_stock_value,
                "qty": total_stock_qty
            },
            "impressions": {
                "value": total_impressions,
                "prev": total_impressions_prev,
                "dynamics": calculate_dynamics(total_impressions, total_impressions_prev)
            }
        },
        "funnel": funnel,
        "products_count": len(data),
        "products_with_orders": products_with_orders_count,
        "products_with_orders_prev": products_with_orders_count_prev,
        "upload_date": DATA_STORE["upload_date"]
    }


@app.get("/api/dashboard/hits")
async def get_hits(limit: int = 10):
    """Топ товаров по выручке (хиты)"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    # Сортируем по выручке
    sorted_data = sorted(data, key=lambda x: safe_int(x.get('orders_value', 0)), reverse=True)

    hits = []
    for item in sorted_data[:limit]:
        hits.append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:50],
            "category": item.get('category'),
            "orders_value": safe_int(item.get('orders_value', 0)),
            "orders_qty": safe_int(item.get('orders_qty', 0)),
            "dynamics": item.get('revenue_dynamics_pct', 0),
            "purchase_rate": safe_int(item.get('purchase_rate', 0)),
            "stock": item.get('total_stock', 0)
        })

    return {"hits": hits}


@app.get("/api/dashboard/outsiders")
async def get_outsiders(limit: int = 10):
    """Аутсайдеры - товары с проблемами"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    outsiders = []

    # Товары с нулевыми заказами но были показы
    zero_orders = [r for r in data if safe_int(r.get('orders_qty', 0)) == 0 and safe_int(r.get('impressions', 0)) > 1000]
    for item in sorted(zero_orders, key=lambda x: safe_int(x.get('impressions', 0)), reverse=True)[:limit//3]:
        outsiders.append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:50],
            "issue": "Нет заказов",
            "detail": f"{safe_int(item.get('impressions', 0)):,} показов",
            "category": item.get('category'),
            "recommendation": "Проверить цену и контент карточки"
        })

    # Низкий CTR
    low_ctr = [r for r in data if safe_float(r.get('ctr', 0)) < 1 and safe_int(r.get('impressions', 0)) > 5000]
    for item in sorted(low_ctr, key=lambda x: safe_int(x.get('impressions', 0)), reverse=True)[:limit//3]:
        outsiders.append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:50],
            "issue": "Низкий CTR",
            "detail": f"CTR {safe_float(item.get('ctr', 0)):.1f}%",
            "category": item.get('category'),
            "recommendation": "Улучшить главное фото"
        })

    # Низкий процент выкупа
    low_purchase = [r for r in data if safe_int(r.get('purchase_rate', 0)) < 30 and safe_int(r.get('orders_qty', 0)) > 10]
    for item in sorted(low_purchase, key=lambda x: safe_int(x.get('orders_qty', 0)), reverse=True)[:limit//3]:
        outsiders.append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:50],
            "issue": "Низкий выкуп",
            "detail": f"Выкуп {safe_int(item.get('purchase_rate', 0))}%",
            "category": item.get('category'),
            "recommendation": "Проверить качество/описание"
        })

    return {"outsiders": outsiders[:limit]}


@app.get("/api/dashboard/matrix")
async def get_bcg_matrix():
    """BCG-матрица товаров"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    matrix = {
        "star": {"count": 0, "revenue": 0, "items": []},
        "question": {"count": 0, "revenue": 0, "items": []},
        "cash_cow": {"count": 0, "revenue": 0, "items": []},
        "dog": {"count": 0, "revenue": 0, "items": []}
    }

    for item in data:
        category = item.get('bcg_category', 'dog')
        revenue = safe_int(item.get('orders_value', 0))

        matrix[category]["count"] += 1
        matrix[category]["revenue"] += revenue

        # Добавляем все товары для возможности экспорта
        matrix[category]["items"].append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:40],
            "orders_value": revenue,
            "orders_qty": safe_int(item.get('orders_qty', 0)),
            "dynamics": item.get('revenue_dynamics_pct', 0),
            "stock": item.get('total_stock', 0)
        })

    # Сортируем товары в каждой категории по выручке
    for cat in matrix:
        matrix[cat]["items"] = sorted(matrix[cat]["items"], key=lambda x: x['orders_value'], reverse=True)

    return {"matrix": matrix}


@app.get("/api/dashboard/actions")
async def get_actions():
    """Рекомендуемые действия"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    actions = {
        "critical": [],
        "important": [],
        "opportunities": []
    }

    def format_items(items_list):
        """Форматирование списка товаров для экспорта"""
        return [{
            "seller_article": r.get('seller_article'),
            "wb_article": r.get('wb_article'),
            "name": r.get('name', '')[:50],
            "orders_value": safe_int(r.get('orders_value', 0)),
            "dynamics": r.get('revenue_dynamics_pct', 0)
        } for r in items_list]

    # КРИТИЧНО: Out of stock с продажами в прошлом периоде
    oos_items = [r for r in data if r.get('total_stock', 0) == 0 and safe_int(r.get('orders_value_prev', 0)) > 5000]
    if oos_items:
        total_lost = sum(safe_int(r.get('orders_value_prev', 0)) for r in oos_items)
        actions["critical"].append({
            "title": f"Пополнить {len(oos_items)} SKU на складе",
            "description": f"Товары с нулевым остатком, продавались на {total_lost:,}₽/нед",
            "potential": total_lost,
            "items_count": len(oos_items),
            "items": format_items(oos_items)
        })

    # КРИТИЧНО: Сильное падение продаж
    falling = [r for r in data if r.get('revenue_dynamics_pct', 0) < -30 and safe_int(r.get('orders_value_prev', 0)) > 10000]
    if falling:
        actions["critical"].append({
            "title": f"Проанализировать падение {len(falling)} товаров",
            "description": "Падение выручки более 30% неделя к неделе",
            "potential": sum(safe_int(r.get('orders_value_prev', 0)) - safe_int(r.get('orders_value', 0)) for r in falling),
            "items_count": len(falling),
            "items": format_items(falling)
        })

    # ВАЖНО: Низкий рейтинг карточки
    low_rating = [r for r in data if safe_float(r.get('card_rating', 10)) < 5 and safe_int(r.get('impressions', 0)) > 1000]
    if low_rating:
        actions["important"].append({
            "title": f"Улучшить {len(low_rating)} карточек с низким рейтингом",
            "description": "Рейтинг карточки ниже 5, влияет на показы",
            "items_count": len(low_rating),
            "items": format_items(low_rating)
        })

    # ВАЖНО: Высокий CTR, но низкая конверсия
    high_ctr_low_conv = [r for r in data if safe_float(r.get('ctr', 0)) > 5 and safe_float(r.get('order_conversion', 0)) < 2]
    if high_ctr_low_conv:
        actions["important"].append({
            "title": f"Оптимизировать цену для {len(high_ctr_low_conv)} товаров",
            "description": "Хороший CTR, но низкая конверсия - проблема в цене/описании",
            "items_count": len(high_ctr_low_conv),
            "items": format_items(high_ctr_low_conv)
        })

    # ВОЗМОЖНОСТИ: Звёзды с низкими остатками
    stars_low_stock = [r for r in data if r.get('bcg_category') == 'star' and r.get('total_stock', 0) < 50]
    if stars_low_stock:
        actions["opportunities"].append({
            "title": f"Увеличить остатки {len(stars_low_stock)} звёзд",
            "description": "Хиты продаж с остатком менее 50шт - риск OOS",
            "items_count": len(stars_low_stock),
            "items": format_items(stars_low_stock)
        })

    # ВОЗМОЖНОСТИ: Вопросы для тестирования
    questions = [r for r in data if r.get('bcg_category') == 'question']
    if questions:
        actions["opportunities"].append({
            "title": f"A/B тест цен для {len(questions)} товаров-вопросов",
            "description": "Растущие товары с потенциалом роста продаж",
            "items_count": len(questions),
            "items": format_items(questions)
        })

    return {"actions": actions}


class WBApiFetchRequest(BaseModel):
    wb_api_key: str
    date_from: str
    date_to: str
    past_from: Optional[str] = None
    past_to: Optional[str] = None


class AIAnalysisRequest(BaseModel):
    api_key: Optional[str] = None
    focus: Optional[str] = "general"  # general, hits, outsiders, matrix, actions


# API key from environment variable
DEFAULT_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@app.post("/api/fetch-from-wb")
async def fetch_from_wb(request: WBApiFetchRequest):
    """Загрузка данных из WB API (Sales Funnel)"""
    try:
        api_products = await fetch_sales_funnel(
            api_key=request.wb_api_key,
            date_from=request.date_from,
            date_to=request.date_to,
            past_from=request.past_from,
            past_to=request.past_to,
        )

        if not api_products:
            raise HTTPException(
                status_code=404,
                detail="Нет данных за указанный период"
            )

        mapped = map_api_to_internal(api_products)

        processed = []
        for record in mapped:
            record['impressions_dynamics'] = calculate_dynamics(
                record.get('card_views', 0),
                record.get('card_views_prev', 0)
            )
            record['orders_dynamics_pct'] = calculate_dynamics(
                record.get('orders_qty', 0),
                record.get('orders_qty_prev', 0)
            )
            record['revenue_dynamics_pct'] = calculate_dynamics(
                record.get('orders_value', 0),
                record.get('orders_value_prev', 0)
            )
            record['bcg_category'] = classify_product(record)
            record['total_stock'] = (
                safe_int(record.get('stock_wb', 0))
                + safe_int(record.get('stock_mp', 0))
            )
            if (record['total_stock'] == 0
                    and safe_int(record.get('orders_qty_prev', 0)) > 0):
                record['lost_revenue'] = safe_int(
                    record.get('orders_value_prev', 0)
                )
            else:
                record['lost_revenue'] = 0
            processed.append(record)

        DATA_STORE["raw_data"] = mapped
        DATA_STORE["processed_data"] = processed
        DATA_STORE["upload_date"] = datetime.now().isoformat()
        DATA_STORE["filename"] = (
            f"WB API: {request.date_from} — {request.date_to}"
        )
        DATA_STORE["period"] = {
            "from": request.date_from,
            "to": request.date_to
        }

        return {
            "success": True,
            "message": f"Загружено {len(processed)} товаров из WB API",
            "products_count": len(processed),
            "source": "wb_api",
            "period": {
                "from": request.date_from,
                "to": request.date_to
            }
        }
    except httpx.HTTPStatusError as e:
        detail = f"Ошибка WB API: {e.response.status_code}"
        try:
            err_body = e.response.json()
            detail = f"Ошибка WB API: {err_body.get('detail', str(e))}"
        except Exception:
            pass
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка загрузки из WB API: {str(e)}"
        )


@app.post("/api/ai/analyze")
async def ai_analyze(request: AIAnalysisRequest):
    """ИИ-анализ данных через Claude API"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    try:
        api_key = request.api_key or DEFAULT_API_KEY
        client = Anthropic(api_key=api_key)

        # Подготавливаем данные для анализа
        data = DATA_STORE["processed_data"]

        # Сводка данных
        summary = {
            "total_products": len(data),
            "total_revenue": sum(safe_int(r.get('orders_value', 0)) for r in data),
            "total_revenue_prev": sum(safe_int(r.get('orders_value_prev', 0)) for r in data),
            "total_orders": sum(safe_int(r.get('orders_qty', 0)) for r in data),
            "avg_purchase_rate": round(sum(safe_int(r.get('purchase_rate', 0)) for r in data) / len(data), 1),
            "categories": {},
            "bcg_distribution": {"star": 0, "question": 0, "cash_cow": 0, "dog": 0},
            "problems": {
                "zero_stock": len([r for r in data if r.get('total_stock', 0) == 0]),
                "low_ctr": len([r for r in data if safe_float(r.get('ctr', 0)) < 1]),
                "falling_sales": len([r for r in data if r.get('revenue_dynamics_pct', 0) < -20])
            }
        }

        # Категории
        for r in data:
            cat = r.get('category', 'Другое')
            if cat not in summary["categories"]:
                summary["categories"][cat] = {"count": 0, "revenue": 0}
            summary["categories"][cat]["count"] += 1
            summary["categories"][cat]["revenue"] += safe_int(r.get('orders_value', 0))

        # BCG
        for r in data:
            bcg = r.get('bcg_category', 'dog')
            summary["bcg_distribution"][bcg] += 1

        # Топ-10 по выручке
        top_10 = sorted(data, key=lambda x: safe_int(x.get('orders_value', 0)), reverse=True)[:10]
        summary["top_10"] = [{"name": r.get('name', '')[:50], "revenue": safe_int(r.get('orders_value', 0)), "dynamics": r.get('revenue_dynamics_pct', 0)} for r in top_10]

        prompt = f"""Ты - эксперт по аналитике продаж на Wildberries. Проанализируй данные за неделю и дай конкретные рекомендации для роста продаж.

ДАННЫЕ:
{json.dumps(summary, ensure_ascii=False, indent=2)}

ЗАДАЧА:
1. Кратко опиши текущую ситуацию (2-3 предложения)
2. Выдели 3 главные проблемы с конкретными цифрами
3. Дай 5 конкретных рекомендаций для роста продаж (с приоритетом)
4. Оцени потенциал роста при выполнении рекомендаций

Отвечай по-русски, структурированно, с конкретными цифрами. Без воды и общих фраз."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "analysis": message.content[0].text,
            "data_summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка ИИ-анализа: {str(e)}")


@app.get("/api/products")
async def get_products(
    page: int = 1,
    limit: int = 50,
    sort_by: str = "orders_value",
    sort_order: str = "desc",
    category: Optional[str] = None,
    bcg: Optional[str] = None
):
    """Получение списка товаров с фильтрацией"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]

    # Фильтрация
    if category:
        data = [r for r in data if r.get('category') == category]
    if bcg:
        data = [r for r in data if r.get('bcg_category') == bcg]

    # Сортировка
    reverse = sort_order == "desc"
    data = sorted(data, key=lambda x: safe_float(x.get(sort_by, 0)), reverse=reverse)

    # Пагинация
    total = len(data)
    start = (page - 1) * limit
    end = start + limit

    return {
        "products": data[start:end],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@app.get("/api/categories")
async def get_categories():
    """Список категорий"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = DATA_STORE["processed_data"]
    categories = {}

    for r in data:
        cat = r.get('category', 'Другое')
        if cat not in categories:
            categories[cat] = {"count": 0, "revenue": 0}
        categories[cat]["count"] += 1
        categories[cat]["revenue"] += safe_int(r.get('orders_value', 0))

    return {"categories": categories}


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "ok", "data_loaded": DATA_STORE["processed_data"] is not None}


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Отдаём dashboard.html как главную страницу"""
    dashboard_path = BASE_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path, media_type="text/html")
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
