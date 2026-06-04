"""
Omnilytic - Backend API
"""
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("omnilytic")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import io
import pandas as pd
import json
from typing import Optional
import os
import sys
from datetime import datetime
import httpx
from anthropic import Anthropic
from pydantic import BaseModel
from wb_api_client import (
    fetch_commission_tariffs,
    fetch_sales_funnel,
    fetch_sales_report_details_by_period,
    fetch_search_report_overview,
    map_api_to_internal,
    resolve_periods,
)

app = FastAPI(title="Omnilytic API", version="1.0.0")

# Путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Глобальное хранилище данных (в production использовать БД)
DATA_STORE = {
    "raw_data": None,
    "processed_data": None,
    "upload_date": None,
    "period": None,
    "filename": None,
    "source": None,
    "search_report_metrics": None,
    "metrics_availability": None,
    "metrics_origin": None,
    "unit_cache": {},
    "commission_cache": {},
    "dashboard_cache": {},
    "wb_api_key": None,
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


def relative_dynamics_or_none(current, previous):
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def percent_point_change(current, previous):
    return round(current - previous, 1)


def build_absolute_metric(value, prev, available=True, reason=None, origin=None):
    metric = {
        "value": value if available else None,
        "prev": prev if available else None,
        "dynamics": relative_dynamics_or_none(value, prev) if available else None,
        "diff": (value - prev) if available else None,
        "available": available,
        "reason": reason,
    }
    if origin:
        metric["origin"] = origin
    return metric


def build_percentage_metric(value, prev, available=True, reason=None, origin=None):
    metric = {
        "value": value if available else None,
        "prev": prev if available else None,
        "dynamics": percent_point_change(value, prev) if available else None,
        "available": available,
        "reason": reason,
    }
    if origin:
        metric["origin"] = origin
    return metric


def build_metrics_meta_for_excel():
    availability = {
        "impressions": {"available": True, "reason": None},
        "ctr": {"available": True, "reason": None},
        "cart_conversion": {"available": True, "reason": None},
        "order_conversion": {"available": True, "reason": None},
        "purchase_rate": {"available": True, "reason": None},
        "cancel_rate": {"available": True, "reason": None},
    }
    origin = {
        "impressions": "excel",
        "ctr": "excel",
        "card_views": "excel",
        "cart_conversion": "excel",
        "order_conversion": "excel",
        "purchase_rate": "excel",
        "cancel_rate": "excel",
        "revenue": "excel",
        "orders": "excel",
        "purchased_value": "excel",
        "cancelled_value": "excel",
        "avg_order_value": "excel",
    }
    return availability, origin


def format_search_report_error(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return "Search Report API недоступен для этого токена или тарифа Jam."
        if status == 429:
            return "Search Report API временно ограничил запросы. Попробуйте позже."
        try:
            body = exc.response.json()
            detail = body.get("detail") or body.get("message")
            if detail:
                return f"Search Report API: {detail}"
        except Exception:
            pass
        return f"Search Report API вернул ошибку {status}."
    return f"Search Report API недоступен: {str(exc)}"


def build_metrics_meta_for_wb(search_report_metrics=None, search_report_reason=None):
    search_available = bool(search_report_metrics)
    fallback_reason = None if search_available else (
        search_report_reason
        or "Показы и CTR требуют Search Report API (тариф Jam). Отображаются данные из Sales Funnel."
    )
    availability = {
        "impressions": {"available": True, "reason": fallback_reason},
        "ctr": {"available": True, "reason": fallback_reason},
        "cart_conversion": {"available": True, "reason": None},
        "order_conversion": {"available": True, "reason": None},
        "purchase_rate": {"available": True, "reason": None},
        "cancel_rate": {"available": True, "reason": None},
    }
    origin = {
        "impressions": "search_report" if search_available else "sales_funnel",
        "ctr": "search_report" if search_available else "sales_funnel",
        "card_views": "sales_funnel",
        "cart_conversion": "sales_funnel",
        "order_conversion": "sales_funnel",
        "purchase_rate": "sales_funnel",
        "cancel_rate": "sales_funnel",
        "revenue": "sales_funnel",
        "orders": "sales_funnel",
        "purchased_value": "sales_funnel",
        "cancelled_value": "sales_funnel",
        "avg_order_value": "sales_funnel",
    }
    return availability, origin


UNIT_SCALE_META = [
    {"key": "retail_price", "label": "Итоговая цена", "color": "#111111", "is_summary": True},
    {"key": "commission", "label": "Комиссия WB", "color": "#1f1d3d"},
    {"key": "logistics", "label": "Логистика", "color": "#d98c10"},
    {"key": "storage", "label": "Хранение", "color": "#8c6a3c"},
    {"key": "acquiring", "label": "Эквайринг", "color": "#0b7285"},
    {"key": "penalties", "label": "Штрафы", "color": "#d8373a"},
    {"key": "acceptance", "label": "Приемка", "color": "#7c4dff"},
    {"key": "deductions", "label": "Удержания", "color": "#9c36b5"},
    {"key": "additional_payments", "label": "Доплаты", "color": "#ff7b00"},
    {"key": "seller_payout", "label": "К перечислению продавцу", "color": "#1ea64a"},
]

TARIFF_ROW_META = [
    {"key": "commission", "label": "Комиссия за продажу", "kind": "pct"},
    {"key": "logistics", "label": "Логистика", "kind": "rub"},
    {"key": "storage", "label": "Хранение", "kind": "rub"},
    {"key": "acquiring", "label": "Эквайринг", "kind": "pct"},
    {"key": "penalties", "label": "Штрафы", "kind": "rub"},
    {"key": "acceptance", "label": "Приемка", "kind": "rub"},
    {"key": "deductions", "label": "Удержания", "kind": "rub"},
    {"key": "additional_payments", "label": "Доплаты", "kind": "rub"},
]


def clean_date_like(value):
    if not value:
        return ""
    text = str(value)
    return text[:10]


def format_product_label(product):
    seller_article = str(product.get("seller_article") or "").strip()
    wb_article = str(product.get("wb_article") or "").strip()
    name = str(product.get("name") or "").strip()
    parts = [part for part in [seller_article, wb_article, name] if part]
    return " / ".join(parts[:2]) if len(parts) > 1 else (parts[0] if parts else "Товар")


def find_product_record(product_id: str):
    for item in DATA_STORE.get("processed_data") or []:
        seller_article = str(item.get("seller_article") or "")
        wb_article = str(item.get("wb_article") or "")
        if product_id in {seller_article, wb_article}:
            return item
    return None


def get_filter_products():
    products = []
    seen = set()
    for item in DATA_STORE.get("processed_data") or []:
        seller_article = str(item.get("seller_article") or "").strip()
        wb_article = str(item.get("wb_article") or "").strip()
        option_id = seller_article or wb_article
        if not option_id or option_id in seen:
            continue
        seen.add(option_id)
        products.append({
            "id": option_id,
            "seller_article": seller_article,
            "wb_article": wb_article,
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "label": format_product_label(item),
        })

    products.sort(key=lambda row: (str(row.get("name") or "").lower(), row["id"]))
    return products


def group_report_rows_by_rr_date(rows):
    grouped = {}
    for row in rows:
        rr_date = clean_date_like(row.get("rrDate") or row.get("saleDt") or row.get("dateFrom"))
        if not rr_date:
            continue
        grouped.setdefault(rr_date, []).append(row)
    return grouped


def match_report_row_to_product(row, product_id: str):
    product_id = str(product_id or "")
    return product_id in {
        str(row.get("vendorCode") or ""),
        str(row.get("nmId") or ""),
    }


def compute_unit_components(rows: list[dict]) -> dict:
    retail_price = sum(safe_float(row.get("retailPriceWithDisc")) for row in rows)
    commission = sum(safe_float(row.get("ppvzSalesCommission")) for row in rows)
    logistics = sum(safe_float(row.get("rebillLogisticCost")) for row in rows)
    storage = sum(safe_float(row.get("paidStorage")) for row in rows)
    acquiring = sum(safe_float(row.get("acquiringFee")) for row in rows)
    penalties = sum(safe_float(row.get("penalty")) for row in rows)
    acceptance = sum(safe_float(row.get("paidAcceptance")) for row in rows)
    deductions = sum(safe_float(row.get("deduction")) for row in rows)
    additional_payments = sum(safe_float(row.get("additionalPayment")) for row in rows)

    seller_payout = (
        retail_price
        - commission
        - logistics
        - storage
        - acquiring
        - penalties
        - acceptance
        - deductions
        - additional_payments
    )

    return {
        "retail_price": round(retail_price, 2),
        "commission": round(commission, 2),
        "logistics": round(logistics, 2),
        "storage": round(storage, 2),
        "acquiring": round(acquiring, 2),
        "penalties": round(penalties, 2),
        "acceptance": round(acceptance, 2),
        "deductions": round(deductions, 2),
        "additional_payments": round(additional_payments, 2),
        "seller_payout": round(seller_payout, 2),
    }


def build_scale_item(meta: dict, start_components: dict, end_components: dict):
    start_value = safe_float(start_components.get(meta["key"], 0))
    end_value = safe_float(end_components.get(meta["key"], 0))
    start_revenue = safe_float(start_components.get("retail_price", 0))
    end_revenue = safe_float(end_components.get("retail_price", 0))

    start_pct = round((start_value / start_revenue) * 100, 2) if start_revenue else 0.0
    end_pct = round((end_value / end_revenue) * 100, 2) if end_revenue else 0.0
    total_pct = abs(start_pct) + abs(end_pct)

    return {
        "key": meta["key"],
        "label": meta["label"],
        "color": meta["color"],
        "is_summary": meta.get("is_summary", False),
        "start": {
            "value": round(start_value, 2),
            "pct": start_pct,
            "width": round(abs(start_pct) / total_pct, 4) if total_pct else 0.0,
        },
        "end": {
            "value": round(end_value, 2),
            "pct": end_pct,
            "width": round(abs(end_pct) / total_pct, 4) if total_pct else 0.0,
        },
    }


def build_tariff_actual_row(key: str, kind: str, components: dict):
    revenue = safe_float(components.get("retail_price", 0))
    value = safe_float(components.get(key, 0))
    if kind == "pct":
        if revenue <= 0:
            return None
        return round((value / revenue) * 100, 2)
    return round(value, 2)


def build_tariff_change(kind: str, start_value, end_value):
    if start_value is None or end_value is None:
        return None
    if kind == "pct":
        return round(end_value - start_value, 2)
    if start_value == 0:
        return None
    return round(((end_value - start_value) / start_value) * 100, 2)


def resolve_standard_commission_rate(commission_payload: dict, subject_name: str, delivery_method: str):
    report = (commission_payload or {}).get("report") or []
    delivery_method_upper = str(delivery_method or "").upper()
    subject_name = str(subject_name or "").strip().lower()

    matched = None
    for row in report:
        if str(row.get("subjectName") or "").strip().lower() == subject_name:
            matched = row
            break

    if not matched:
        return None

    if "FBS" in delivery_method_upper or "DBS" in delivery_method_upper:
        return safe_float(matched.get("kgvpSupplier"), None)
    return safe_float(matched.get("kgvpMarketplace"), None)


async def get_commission_tariffs_cached(api_key: str):
    cache_key = api_key.strip()
    if not cache_key:
        return None

    cached = DATA_STORE["commission_cache"].get(cache_key)
    if cached is not None:
        return cached

    payload = await fetch_commission_tariffs(api_key=api_key, locale="ru")
    DATA_STORE["commission_cache"][cache_key] = payload
    return payload


async def get_unit_economics_payload(api_key: str, date_from: str, date_to: str, product_id: str):
    cache_key = "|".join([api_key.strip(), date_from, date_to, product_id])
    cached = DATA_STORE["unit_cache"].get(cache_key)
    if cached is not None:
        return cached

    fields = [
        "rrdId",
        "nmId",
        "vendorCode",
        "title",
        "subjectName",
        "rrDate",
        "saleDt",
        "deliveryMethod",
        "srvDbs",
        "retailPriceWithDisc",
        "ppvzSalesCommission",
        "acquiringFee",
        "rebillLogisticCost",
        "paidStorage",
        "penalty",
        "deduction",
        "additionalPayment",
        "paidAcceptance",
    ]
    rows = await fetch_sales_report_details_by_period(
        api_key=api_key,
        date_from=date_from,
        date_to=date_to,
        period="daily",
        fields=fields,
    )
    matched_rows = [row for row in rows if match_report_row_to_product(row, product_id)]
    if not matched_rows:
        log.warning(
            "UE: no financial data for product_id=%r dates=%s..%s (rows received: %d)",
            product_id, date_from, date_to, len(rows),
        )
        source_hint = ""
        if DATA_STORE.get("source") == "excel":
            source_hint = (
                " Загружены Excel-данные — командный центр считается по локальному файлу, "
                "а юнит-экономика всегда запрашивает WB API напрямую. "
                "Артикулы из Excel могут не совпадать с реальными vendorCode в WB."
            )
        raise HTTPException(
            status_code=404,
            detail=(
                f"Нет финансовых данных по товару {product_id} за период "
                f"{date_from} — {date_to}. Проверьте, что артикул совпадает с WB "
                f"(vendorCode/nmId) и в выбранном периоде есть продажи/выкупы."
                f"{source_hint}"
            ),
        )
    grouped_rows = group_report_rows_by_rr_date(matched_rows)

    start_rows = grouped_rows.get(date_from, [])
    end_rows = grouped_rows.get(date_to, [])

    start_components = compute_unit_components(start_rows)
    end_components = compute_unit_components(end_rows)
    period_components = compute_unit_components(matched_rows)

    product_record = find_product_record(product_id) or {}
    first_row = matched_rows[0] if matched_rows else {}
    product_name = first_row.get("title") or product_record.get("name") or "Товар"
    subject_name = first_row.get("subjectName") or product_record.get("category") or ""
    delivery_method = first_row.get("deliveryMethod") or ""

    scales = [
        build_scale_item(meta, start_components, end_components)
        for meta in UNIT_SCALE_META
    ]

    pie_segments = []
    period_revenue = safe_float(period_components.get("retail_price", 0))
    for meta in UNIT_SCALE_META:
        if meta.get("is_summary"):
            continue
        value = safe_float(period_components.get(meta["key"], 0))
        if value <= 0:
            continue
        pct = round((value / period_revenue) * 100, 2) if period_revenue else 0.0
        pie_segments.append({
            "key": meta["key"],
            "label": meta["label"],
            "value": round(value, 2),
            "pct": pct,
            "color": meta["color"],
        })

    commission_payload = None
    commission_error = None
    try:
        commission_payload = await get_commission_tariffs_cached(api_key)
    except Exception:
        commission_error = "Стандартные комиссии сейчас недоступны."

    standard_commission = resolve_standard_commission_rate(
        commission_payload or {},
        subject_name=subject_name,
        delivery_method=delivery_method,
    )

    tariff_rows = []
    for meta in TARIFF_ROW_META:
        standard_start = standard_commission if meta["key"] == "commission" else None
        standard_end = standard_commission if meta["key"] == "commission" else None
        actual_start = build_tariff_actual_row(meta["key"], meta["kind"], start_components)
        actual_end = build_tariff_actual_row(meta["key"], meta["kind"], end_components)
        tariff_rows.append({
            "key": meta["key"],
            "label": meta["label"],
            "kind": meta["kind"],
            "start": {
                "standard": standard_start,
                "actual": actual_start,
            },
            "end": {
                "standard": standard_end,
                "actual": actual_end,
            },
            "change": {
                "standard": build_tariff_change(meta["kind"], standard_start, standard_end),
                "actual": build_tariff_change(meta["kind"], actual_start, actual_end),
            },
        })

    payload = {
        "product": {
            "id": product_id,
            "name": product_name,
            "subject_name": subject_name,
            "seller_article": product_record.get("seller_article") or first_row.get("vendorCode"),
            "wb_article": product_record.get("wb_article") or first_row.get("nmId"),
            "label": format_product_label(product_record or {
                "seller_article": first_row.get("vendorCode"),
                "wb_article": first_row.get("nmId"),
                "name": product_name,
            }),
        },
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "product_id": product_id,
        },
        "start_date": {
            "date": date_from,
            "retail_price": start_components.get("retail_price", 0),
        },
        "end_date": {
            "date": date_to,
            "retail_price": end_components.get("retail_price", 0),
        },
        "scales": scales,
        "pie": {
            "total_revenue": round(period_revenue, 2),
            "product_breakdown": [
                {
                    "label": product_name,
                    "value": round(period_revenue, 2),
                }
            ],
            "segments": pie_segments,
        },
        "tariffs": {
            "rows": tariff_rows,
            "standard_note": commission_error,
        },
    }
    DATA_STORE["unit_cache"][cache_key] = payload
    return payload


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


def enrich_processed_records(records):
    """Р”РѕР±Р°РІР»СЏРµС‚ РІС‹С‡РёСЃР»СЏРµРјС‹Рµ РїРѕР»СЏ Рє РЅРѕСЂРјР°Р»РёР·РѕРІР°РЅРЅС‹Рј Р·Р°РїРёСЃСЏРј."""
    return process_data(pd.DataFrame.from_records(records).rename(columns={}))


async def build_wb_dashboard_snapshot(api_key: str, date_from: str, date_to: str):
    cache_key = "|".join([api_key.strip(), date_from, date_to])
    cached = DATA_STORE["dashboard_cache"].get(cache_key)
    if cached:
        return cached

    periods = resolve_periods(date_from, date_to)
    api_products = await fetch_sales_funnel(
        api_key=api_key,
        date_from=periods["current_from"],
        date_to=periods["current_to"],
        past_from=periods["past_from"],
        past_to=periods["past_to"],
    )
    mapped = map_api_to_internal(api_products)
    search_report_metrics = None
    search_report_reason = None

    try:
        current_search = await fetch_search_report_overview(
            api_key=api_key,
            date_from=periods["current_from"],
            date_to=periods["current_to"],
            past_from=periods["past_from"],
            past_to=periods["past_to"],
        )
        search_report_metrics = {
            "current": current_search,
            "previous": {
                "visibility": current_search.get("visibility_prev", 0),
                "open_card": current_search.get("open_card_prev", 0),
            },
        }
    except Exception as exc:
        search_report_reason = format_search_report_error(exc)

    metrics_availability, metrics_origin = build_metrics_meta_for_wb(
        search_report_metrics,
        search_report_reason,
    )
    snapshot = {
        "raw_data": mapped,
        "processed_data": enrich_processed_records(mapped),
        "upload_date": datetime.now().isoformat(),
        "period": {
            "from": periods["current_from"],
            "to": periods["current_to"],
            "prev_from": periods["past_from"],
            "prev_to": periods["past_to"],
        },
        "source": "wb_api",
        "search_report_metrics": search_report_metrics,
        "metrics_availability": metrics_availability,
        "metrics_origin": metrics_origin,
    }
    DATA_STORE["dashboard_cache"][cache_key] = snapshot
    DATA_STORE["raw_data"] = mapped
    DATA_STORE["processed_data"] = enrich_processed_records(mapped)
    DATA_STORE["period"] = snapshot["period"]
    DATA_STORE["upload_date"] = snapshot["upload_date"]
    DATA_STORE["search_report_metrics"] = search_report_metrics
    DATA_STORE["metrics_availability"] = metrics_availability
    DATA_STORE["metrics_origin"] = metrics_origin
    log.info(
        "WB-SNAPSHOT: rebuilt for %s — %s (%d products), DATA_STORE updated",
        periods["current_from"], periods["current_to"], len(mapped),
    )
    return snapshot


async def get_dashboard_snapshot(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    log.info(
        "SNAPSHOT: date_from=%r date_to=%r source=%r processed_count=%d",
        date_from, date_to, DATA_STORE.get("source"),
        len(DATA_STORE.get("processed_data") or []),
    )
    if date_from and date_to:
        if DATA_STORE.get("source") == "wb_api" and DATA_STORE.get("wb_api_key"):
            return await build_wb_dashboard_snapshot(
                DATA_STORE["wb_api_key"],
                date_from,
                date_to,
            )

    return {
        "raw_data": DATA_STORE.get("raw_data"),
        "processed_data": DATA_STORE.get("processed_data"),
        "upload_date": DATA_STORE.get("upload_date"),
        "period": DATA_STORE.get("period"),
        "source": DATA_STORE.get("source") or "excel",
        "search_report_metrics": DATA_STORE.get("search_report_metrics") or {},
        "metrics_availability": DATA_STORE.get("metrics_availability") or {},
        "metrics_origin": DATA_STORE.get("metrics_origin") or {},
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка Excel файла с данными"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Только Excel файлы (.xlsx, .xls)")

    try:
        # Читаем файл
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name=0)

        # Обрабатываем данные
        processed = process_data(df)

        # Сохраняем в хранилище
        DATA_STORE["raw_data"] = df.to_dict('records')
        DATA_STORE["processed_data"] = processed
        DATA_STORE["upload_date"] = datetime.now().isoformat()
        DATA_STORE["unit_cache"] = {}
        DATA_STORE["dashboard_cache"] = {}
        DATA_STORE["filename"] = file.filename
        DATA_STORE["period"] = None
        DATA_STORE["source"] = "excel"
        DATA_STORE["wb_api_key"] = None
        DATA_STORE["search_report_metrics"] = None
        (
            DATA_STORE["metrics_availability"],
            DATA_STORE["metrics_origin"],
        ) = build_metrics_meta_for_excel()

        return {
            "success": True,
            "message": f"Загружено {len(processed)} товаров",
            "products_count": len(processed),
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


def filter_products(data, product_ids_str):
    if not product_ids_str:
        return data
    ids = [x.strip() for x in product_ids_str.split(",") if x.strip()]
    if not ids:
        return data
    return [r for r in data if str(r.get('seller_article', '')) in ids or str(r.get('wb_article', '')) in ids]


@app.get("/api/dashboard/summary")
async def get_dashboard_summary(
    product_ids: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Получение сводных KPI для дашборда с средневзвешенными показателями"""
    log.info(
        "SUMMARY: product_ids=%r date_from=%r date_to=%r source=%r",
        product_ids, date_from, date_to, DATA_STORE.get("source"),
    )
    snapshot = await get_dashboard_snapshot(date_from, date_to)
    if not snapshot.get("processed_data"):
        raise HTTPException(
            status_code=404,
            detail="Нет данных. Сначала загрузите Excel или подтяните данные через WB API.",
        )

    data = filter_products(snapshot["processed_data"], product_ids)

    source = snapshot.get("source") or "excel"
    metrics_availability = snapshot.get("metrics_availability") or {}
    metrics_origin = snapshot.get("metrics_origin") or {}
    search_report_metrics = snapshot.get("search_report_metrics") or {}

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
    total_card_views = sum(safe_int(r.get('card_views', 0)) for r in data_with_orders)
    total_add_to_cart = sum(safe_int(r.get('add_to_cart', 0)) for r in data_with_orders)
    total_favorites = sum(safe_int(r.get('add_to_favorites', 0)) for r in data_with_orders)

    # Воронка - предыдущий период (только по товарам с заказами в пред. периоде)
    total_card_views_prev = sum(safe_int(r.get('card_views_prev', 0)) for r in data_with_orders_prev)
    total_add_to_cart_prev = sum(safe_int(r.get('add_to_cart_prev', 0)) for r in data_with_orders_prev)
    total_favorites_prev = sum(safe_int(r.get('add_to_favorites_prev', 0)) for r in data_with_orders_prev)

    impressions_meta = metrics_availability.get("impressions", {})
    ctr_meta = metrics_availability.get("ctr", {})

    if source == "wb_api" and search_report_metrics:
        total_impressions = safe_int(
            search_report_metrics.get("current", {}).get("visibility", 0)
        )
        total_impressions_prev = safe_int(
            search_report_metrics.get("previous", {}).get("visibility", 0)
        )
        ctr_open_card = safe_int(
            search_report_metrics.get("current", {}).get("open_card", 0)
        )
        ctr_open_card_prev = safe_int(
            search_report_metrics.get("previous", {}).get("open_card", 0)
        )
    elif source == "wb_api":
        total_impressions = total_card_views
        total_impressions_prev = total_card_views_prev
        ctr_open_card = 0
        ctr_open_card_prev = 0
    else:
        total_impressions = sum(
            safe_int(r.get('impressions', 0)) for r in data_with_orders
        )
        total_impressions_prev = sum(
            safe_int(r.get('impressions_prev', 0)) for r in data_with_orders_prev
        )
        ctr_open_card = total_card_views
        ctr_open_card_prev = total_card_views_prev

    # Остатки - ПО ВСЕМ ТОВАРАМ (не фильтруем)
    total_stock_value = sum(safe_int(r.get('stock_value', 0)) for r in data)
    total_stock_qty = sum(safe_int(r.get('total_stock', 0)) for r in data)

    # Количество товаров с заказами
    products_with_orders_count = len(data_with_orders)
    products_with_orders_count_prev = len(data_with_orders_prev)

    # ===== СРЕДНЕВЗВЕШЕННЫЕ ПОКАЗАТЕЛИ =====
    # CTR = (переходы / показы) * 100 — средневзвешенный по показам
    avg_ctr = round((ctr_open_card / total_impressions * 100), 2) if total_impressions > 0 else 0
    avg_ctr_prev = round((ctr_open_card_prev / total_impressions_prev * 100), 2) if total_impressions_prev > 0 else 0

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
        "impressions": build_absolute_metric(
            total_impressions,
            total_impressions_prev,
            available=impressions_meta.get("available", True),
            reason=impressions_meta.get("reason"),
            origin=metrics_origin.get("impressions"),
        ),
        "card_views": build_absolute_metric(
            total_card_views,
            total_card_views_prev,
            origin=metrics_origin.get("card_views"),
        ),
        "add_to_cart": build_absolute_metric(
            total_add_to_cart,
            total_add_to_cart_prev,
            origin=metrics_origin.get("cart_conversion"),
        ),
        "favorites": build_absolute_metric(
            total_favorites,
            total_favorites_prev,
        ),
        "orders": build_absolute_metric(
            total_orders_qty,
            total_orders_qty_prev,
            origin=metrics_origin.get("orders"),
        ),
        "purchased": build_absolute_metric(
            total_purchased_qty,
            total_purchased_qty_prev,
        ),
        "cancelled": build_absolute_metric(
            total_cancelled_qty,
            total_cancelled_qty_prev,
        ),
        # Конверсии с динамикой
        "conversions": {
            "ctr": build_percentage_metric(
                avg_ctr,
                avg_ctr_prev,
                available=ctr_meta.get("available", True),
                reason=ctr_meta.get("reason"),
                origin=metrics_origin.get("ctr"),
            ),
            "cart_rate": build_percentage_metric(
                cart_conversion,
                cart_conversion_prev,
                origin=metrics_origin.get("cart_conversion"),
            ),
            "order_rate": build_percentage_metric(
                order_conversion,
                order_conversion_prev,
                origin=metrics_origin.get("order_conversion"),
            ),
            "purchase_rate": build_percentage_metric(
                purchase_rate,
                purchase_rate_prev,
                origin=metrics_origin.get("purchase_rate"),
            ),
            "cancel_rate": build_percentage_metric(
                cancel_rate,
                cancel_rate_prev,
                origin=metrics_origin.get("cancel_rate"),
            )
        }
    }

    return {
        "source": source,
        "metrics_availability": metrics_availability,
        "metrics_origin": metrics_origin,
        "kpi": {
            "revenue": build_absolute_metric(
                total_orders_value,
                total_orders_value_prev,
                origin=metrics_origin.get("revenue"),
            ),
            "orders": build_absolute_metric(
                total_orders_qty,
                total_orders_qty_prev,
                origin=metrics_origin.get("orders"),
            ),
            "purchased_value": build_absolute_metric(
                total_purchased_value,
                total_purchased_value_prev,
                origin=metrics_origin.get("purchased_value"),
            ),
            "purchased_qty": build_absolute_metric(
                total_purchased_qty,
                total_purchased_qty_prev,
            ),
            "purchase_rate": build_percentage_metric(
                purchase_rate,
                purchase_rate_prev,
                origin=metrics_origin.get("purchase_rate"),
            ),
            "cancel_rate": build_percentage_metric(
                cancel_rate,
                cancel_rate_prev,
                origin=metrics_origin.get("cancel_rate"),
            ),
            "cancelled_value": build_absolute_metric(
                total_cancelled_value,
                total_cancelled_value_prev,
                origin=metrics_origin.get("cancelled_value"),
            ),
            "avg_order_value": build_absolute_metric(
                avg_order_value,
                avg_order_value_prev,
                origin=metrics_origin.get("avg_order_value"),
            ),
            "avg_price": build_absolute_metric(
                avg_price_weighted,
                avg_price_weighted_prev,
            ),
            "card_views": build_absolute_metric(
                total_card_views,
                total_card_views_prev,
                origin=metrics_origin.get("card_views"),
            ),
            "cart_conversion": build_percentage_metric(
                cart_conversion,
                cart_conversion_prev,
                origin=metrics_origin.get("cart_conversion"),
            ),
            "order_conversion": build_percentage_metric(
                order_conversion,
                order_conversion_prev,
                origin=metrics_origin.get("order_conversion"),
            ),
            "stock": {
                "value": total_stock_value,
                "qty": total_stock_qty
            },
        },
        "funnel": funnel,
        "products_count": len(data),
        "data_with_orders_count": len(data_with_orders),
        "products_with_orders": products_with_orders_count,
        "products_with_orders_prev": products_with_orders_count_prev,
        "upload_date": snapshot.get("upload_date")
    }


@app.get("/api/dashboard/hits")
async def get_hits(
    limit: int = 10,
    product_ids: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Топ товаров по выручке (хиты)"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = filter_products(DATA_STORE["processed_data"], product_ids)

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
async def get_outsiders(limit: int = 10, product_ids: Optional[str] = None):
    """Аутсайдеры - товары с проблемами"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = filter_products(DATA_STORE["processed_data"], product_ids)
    source = DATA_STORE.get("source") or "excel"

    outsiders = []
    traffic_field = "card_views" if source == "wb_api" else "impressions"
    traffic_label = "переходов" if traffic_field == "card_views" else "показов"

    # Товары с нулевыми заказами но были показы
    zero_orders = [r for r in data if safe_int(r.get('orders_qty', 0)) == 0 and safe_int(r.get(traffic_field, 0)) > 1000]
    for item in sorted(zero_orders, key=lambda x: safe_int(x.get(traffic_field, 0)), reverse=True)[:limit//3]:
        traffic_value = safe_int(item.get(traffic_field, 0))
        outsiders.append({
            "seller_article": item.get('seller_article'),
            "wb_article": item.get('wb_article'),
            "name": item.get('name', '')[:50],
            "issue": "Нет заказов",
            "detail": f"{safe_int(item.get('impressions', 0)):,} показов",
            "category": item.get('category'),
            "recommendation": "Проверить цену и контент карточки"
        })
        outsiders[-1]["issue"] = "Нет заказов"
        outsiders[-1]["detail"] = (
            f"{traffic_value:,} "
            f"{'переходов в карточку' if traffic_field == 'card_views' else 'показов'}"
        )
        outsiders[-1]["recommendation"] = "Проверьте цену, описание и содержание карточки"

    # Низкий CTR
    low_ctr = [] if source == "wb_api" else [r for r in data if safe_float(r.get('ctr', 0)) < 1 and safe_int(r.get('impressions', 0)) > 5000]
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
        outsiders[-1]["issue"] = "Низкий CTR"
        outsiders[-1]["recommendation"] = "Улучшите главное фото и первые элементы карточки"

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
        outsiders[-1]["issue"] = "Низкий выкуп"
        outsiders[-1]["detail"] = f"Выкуп {safe_int(item.get('purchase_rate', 0))}%"
        outsiders[-1]["recommendation"] = "Проверьте качество товара, упаковку и описание ожиданий"

    return {"outsiders": outsiders[:limit]}


@app.get("/api/dashboard/matrix")
async def get_bcg_matrix(product_ids: Optional[str] = None):
    """BCG-матрица товаров"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = filter_products(DATA_STORE["processed_data"], product_ids)

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

    return {
        "matrix": matrix,
        "rules": {
            "growth_threshold_pct": 10,
            "revenue_threshold": 10000,
        },
    }


@app.get("/api/dashboard/actions")
async def get_actions(product_ids: Optional[str] = None):
    """Рекомендуемые действия"""
    if DATA_STORE["processed_data"] is None:
        raise HTTPException(status_code=404, detail="Данные не загружены")

    data = filter_products(DATA_STORE["processed_data"], product_ids)
    source = DATA_STORE.get("source") or "excel"
    traffic_field = "card_views" if source == "wb_api" else "impressions"

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
    low_rating = [r for r in data if safe_float(r.get('card_rating', 10)) < 5 and safe_int(r.get(traffic_field, 0)) > 1000]
    if low_rating:
        actions["important"].append({
            "title": f"Улучшить {len(low_rating)} карточек с низким рейтингом",
            "description": "Рейтинг карточки ниже 5, влияет на показы",
            "items_count": len(low_rating),
            "items": format_items(low_rating)
        })

    # ВАЖНО: Высокий CTR, но низкая конверсия
    high_ctr_low_conv = [] if source == "wb_api" else [r for r in data if safe_float(r.get('ctr', 0)) > 5 and safe_float(r.get('order_conversion', 0)) < 2]
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


@app.get("/api/filter-options")
async def get_filter_options():
    if DATA_STORE["processed_data"] is None:
        return {"products": []}
    return {"products": get_filter_products()}


class WBApiFetchRequest(BaseModel):
    wb_api_key: str
    date_from: str
    date_to: str
    past_from: Optional[str] = None
    past_to: Optional[str] = None


class UnitEconomicsRequest(BaseModel):
    wb_api_key: str
    date_from: str
    date_to: str
    product_id: str


class AIAnalysisRequest(BaseModel):
    api_key: Optional[str] = None
    focus: Optional[str] = "general"  # general, hits, outsiders, matrix, actions


@app.post("/api/unit-economics")
async def get_unit_economics(request: UnitEconomicsRequest):
    product_id = str(request.product_id or "").strip()
    if not product_id:
        raise HTTPException(status_code=400, detail="Не выбран товар.")

    try:
        payload = await get_unit_economics_payload(
            api_key=request.wb_api_key,
            date_from=request.date_from,
            date_to=request.date_to,
            product_id=product_id,
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        log.warning("UE HTTP %s for %s: %s", exc.response.status_code, product_id, exc.request.url)
        if exc.response.status_code == 401:
            raise HTTPException(status_code=401, detail="WB API отклонил токен. Проверьте правильность ключа.")
        if exc.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Превышен лимит запросов к WB API. Повторите через минуту.")
        raise HTTPException(
            status_code=502,
            detail=f"WB API вернул {exc.response.status_code}. Возможно, сервер Wildberries недоступен.",
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        log.warning("UE network error for %s: %s", product_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Не удалось подключиться к WB API. Сервер Wildberries недоступен — попробуйте позже.",
        )


# API key from environment variable
DEFAULT_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@app.post("/api/fetch-from-wb")
async def fetch_from_wb(request: WBApiFetchRequest):
    """Загрузка данных из WB API (Sales Funnel)"""
    try:
        periods = resolve_periods(
            request.date_from,
            request.date_to,
            request.past_from,
            request.past_to,
        )

        api_products = await fetch_sales_funnel(
            api_key=request.wb_api_key,
            date_from=periods["current_from"],
            date_to=periods["current_to"],
            past_from=periods["past_from"],
            past_to=periods["past_to"],
        )

        if not api_products:
            raise HTTPException(
                status_code=404,
                detail="Нет данных за указанный период"
            )

        mapped = map_api_to_internal(api_products)
        search_report_metrics = None
        search_report_reason = None

        try:
            current_search = await fetch_search_report_overview(
                api_key=request.wb_api_key,
                date_from=periods["current_from"],
                date_to=periods["current_to"],
                past_from=periods["past_from"],
                past_to=periods["past_to"],
            )
            search_report_metrics = {
                "current": current_search,
                "previous": {
                    "visibility": current_search.get("visibility_prev", 0),
                    "open_card": current_search.get("open_card_prev", 0),
                },
            }
        except Exception as exc:
            search_report_reason = format_search_report_error(exc)

        processed = []
        for record in mapped:
            record['impressions_dynamics'] = None
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
        DATA_STORE["unit_cache"] = {}
        DATA_STORE["source"] = "wb_api"
        DATA_STORE["wb_api_key"] = request.wb_api_key
        DATA_STORE["search_report_metrics"] = search_report_metrics
        (
            DATA_STORE["metrics_availability"],
            DATA_STORE["metrics_origin"],
        ) = build_metrics_meta_for_wb(search_report_metrics, search_report_reason)
        DATA_STORE["filename"] = (
            f"WB API: {request.date_from} — {request.date_to}"
        )
        DATA_STORE["period"] = {
            "from": periods["current_from"],
            "to": periods["current_to"],
            "prev_from": periods["past_from"],
            "prev_to": periods["past_to"]
        }
        DATA_STORE["dashboard_cache"] = {}
        log.info(
            "WB-FETCH: %d products (period %s — %s)",
            len(processed), periods["current_from"], periods["current_to"],
        )

        return {
            "success": True,
            "message": f"Загружено {len(processed)} товаров из WB API",
            "products_count": len(processed),
            "source": "wb_api",
            "period": {
                "from": periods["current_from"],
                "to": periods["current_to"]
            },
            "search_report_available": bool(search_report_metrics),
            "search_report_reason": search_report_reason
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as e:
        detail = f"Ошибка WB API: {e.response.status_code}"
        try:
            err_body = e.response.json()
            raw_detail = err_body.get('detail', str(e))
            if 'excess limit on days' in str(raw_detail):
                detail = (
                    "Период слишком длинный. WB API поддерживает "
                    "максимум 365 дней. Выберите период покороче."
                )
            else:
                detail = f"Ошибка WB API: {raw_detail}"
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

        prompt = f"""Ты - эксперт по аналитике продаж на маркетплейсах. Проанализируй данные за неделю и дай конкретные рекомендации для роста продаж.

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
    period = DATA_STORE.get("period") or {}
    return {
        "status": "ok",
        "data_loaded": DATA_STORE["processed_data"] is not None,
        "source": DATA_STORE.get("source"),
        "products_count": len(DATA_STORE.get("processed_data") or []),
        "filename": DATA_STORE.get("filename"),
        "period": period if period else None,
    }


@app.post("/api/reset")
async def reset_data():
    """Полный сброс DATA_STORE. Полезно после тестов или чтобы начать с нуля."""
    DATA_STORE["raw_data"] = None
    DATA_STORE["processed_data"] = None
    DATA_STORE["upload_date"] = None
    DATA_STORE["unit_cache"] = {}
    DATA_STORE["commission_cache"] = {}
    DATA_STORE["dashboard_cache"] = {}
    DATA_STORE["source"] = None
    DATA_STORE["wb_api_key"] = None
    DATA_STORE["search_report_metrics"] = None
    DATA_STORE["metrics_availability"] = None
    DATA_STORE["metrics_origin"] = None
    DATA_STORE["filename"] = None
    DATA_STORE["period"] = None
    log.info("RESET: DATA_STORE cleared")
    return {"success": True, "message": "Все данные сброшены. Загрузите Excel или подтяните данные через WB API."}


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
