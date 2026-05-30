"""
WB API Client for Omnilytic - fetches analytics data from Wildberries Seller API
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional


WB_ANALYTICS_BASE = "https://seller-analytics-api.wildberries.ru"

# Rate limit: 3 req/min for Personal token
RATE_LIMIT_DELAY = 21  # seconds between paginated requests
PAGE_SIZE = 1000


# WB API allows data for the last 365 days maximum
MAX_HISTORY_DAYS = 365


def _safe_int(value, default=0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _previous_from_dynamics(current, dynamics) -> int:
    current_value = _safe_float(current)
    dynamics_value = _safe_float(dynamics)
    multiplier = 1 + dynamics_value / 100

    if multiplier <= 0:
        return 0 if current_value == 0 else _safe_int(current_value)

    return max(0, round(current_value / multiplier))


def resolve_periods(
    date_from: str,
    date_to: str,
    past_from: Optional[str] = None,
    past_to: Optional[str] = None,
) -> dict[str, str]:
    sel_start = datetime.strptime(date_from, "%Y-%m-%d")
    sel_end = datetime.strptime(date_to, "%Y-%m-%d")
    today = datetime.now()

    if sel_end < sel_start:
        raise ValueError("Дата окончания не может быть раньше даты начала.")

    if (today - sel_start).days > MAX_HISTORY_DAYS:
        raise ValueError(
            f"Начальная дата не может быть старше {MAX_HISTORY_DAYS} дней. "
            f"Выберите дату после "
            f"{(today - timedelta(days=MAX_HISTORY_DAYS)).strftime('%d.%m.%Y')}"
        )

    if not past_from or not past_to:
        delta = sel_end - sel_start
        prev_end = sel_start - timedelta(days=1)
        prev_start = prev_end - delta

        earliest_allowed = today - timedelta(days=MAX_HISTORY_DAYS)
        if prev_start < earliest_allowed:
            prev_start = earliest_allowed

        past_from = prev_start.strftime("%Y-%m-%d")
        past_to = prev_end.strftime("%Y-%m-%d")

    return {
        "current_from": date_from,
        "current_to": date_to,
        "past_from": past_from,
        "past_to": past_to,
    }


def _build_search_report_payload(
    current_from: str,
    current_to: str,
    past_from: str,
    past_to: str,
) -> dict:
    return {
        "currentPeriod": {"start": current_from, "end": current_to},
        "pastPeriod": {"start": past_from, "end": past_to},
        "nmIds": [],
        "subjectIds": [],
        "brandNames": [],
        "tagIds": [],
        "positionCluster": "all",
        "orderBy": {
            "field": "avgPosition",
            "mode": "asc",
        },
        "includeSubstitutedSKUs": True,
        "includeSearchTexts": True,
        "limit": 1,
        "offset": 0,
    }


async def fetch_sales_funnel(
    api_key: str,
    date_from: str,
    date_to: str,
    past_from: Optional[str] = None,
    past_to: Optional[str] = None,
) -> list[dict]:
    """
    Fetch all products from WB Sales Funnel API with pagination.
    Returns list of raw API product objects.
    """
    periods = resolve_periods(date_from, date_to, past_from, past_to)
    past_from = periods["past_from"]
    past_to = periods["past_to"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    all_products = []
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            payload = {
                "selectedPeriod": {"start": date_from, "end": date_to},
                "pastPeriod": {"start": past_from, "end": past_to},
                "nmIds": [],
                "brandNames": [],
                "subjectIds": [],
                "tagIds": [],
                "skipDeletedNm": False,
                "limit": PAGE_SIZE,
                "offset": offset,
            }

            resp = await client.post(
                f"{WB_ANALYTICS_BASE}/api/analytics/v3/sales-funnel/products",
                headers=headers,
                json=payload,
            )

            if resp.status_code == 429:
                await asyncio.sleep(RATE_LIMIT_DELAY)
                continue

            resp.raise_for_status()
            data = resp.json()

            products = data.get("data", {}).get("products", [])
            if not products:
                break

            all_products.extend(products)

            if len(products) < PAGE_SIZE:
                break

            offset += PAGE_SIZE
            await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_products


async def fetch_search_report_overview(
    api_key: str,
    date_from: str,
    date_to: str,
    past_from: Optional[str] = None,
    past_to: Optional[str] = None,
) -> dict[str, int]:
    periods = resolve_periods(date_from, date_to, past_from, past_to)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = _build_search_report_payload(
        periods["current_from"],
        periods["current_to"],
        periods["past_from"],
        periods["past_to"],
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            resp = await client.post(
                f"{WB_ANALYTICS_BASE}/api/v2/search-report/report",
                headers=headers,
                json=payload,
            )

            if resp.status_code == 429:
                await asyncio.sleep(RATE_LIMIT_DELAY)
                continue

            resp.raise_for_status()
            data = resp.json()
            break

    visibility_info = data.get("data", {}).get("visibilityInfo", {})
    visibility = visibility_info.get("visibility", {})
    open_card = visibility_info.get("openCard", {})
    visibility_current = _safe_int(visibility.get("current"))
    open_card_current = _safe_int(open_card.get("current"))

    return {
        "visibility": visibility_current,
        "visibility_prev": _previous_from_dynamics(
            visibility_current,
            visibility.get("dynamics"),
        ),
        "visibility_dynamics": _safe_float(visibility.get("dynamics")),
        "open_card": open_card_current,
        "open_card_prev": _previous_from_dynamics(
            open_card_current,
            open_card.get("dynamics"),
        ),
        "open_card_dynamics": _safe_float(open_card.get("dynamics")),
    }


def map_api_to_internal(api_products: list[dict]) -> list[dict]:
    """
    Map WB API Sales Funnel response to the internal format
    used by process_data() / DATA_STORE.
    The output matches the structure produced by Excel upload + process_data().
    """
    records = []

    for item in api_products:
        product = item["product"]
        selected = item["statistic"]["selected"]
        past = item["statistic"]["past"]

        delivery = selected.get("timeToReady", {})
        delivery_hours = (
            delivery.get("days", 0) * 24
            + delivery.get("hours", 0)
            + delivery.get("mins", 0) / 60
        )
        delivery_prev = past.get("timeToReady", {})
        delivery_hours_prev = (
            delivery_prev.get("days", 0) * 24
            + delivery_prev.get("hours", 0)
            + delivery_prev.get("mins", 0) / 60
        )

        record = {
            # Product info
            "seller_article": product.get("vendorCode", ""),
            "wb_article": product.get("nmId", 0),
            "name": product.get("title", ""),
            "category": product.get("subjectName", ""),
            "brand": product.get("brandName", ""),
            "is_deleted": False,
            "card_rating": product.get("productRating", 0),
            "review_rating": product.get("feedbackRating", 0),
            # Search Report API is required for visibility and real CTR.
            "impressions": None,
            "impressions_prev": None,
            "ctr": None,
            "ctr_prev": None,
            # Card views (openCount in API)
            "card_views": selected.get("openCount", 0),
            "card_views_prev": past.get("openCount", 0),
            # Revenue share
            "revenue_share": selected.get("shareOrderPercent", 0),
            "revenue_share_prev": past.get("shareOrderPercent", 0),
            # Add to cart
            "add_to_cart": selected.get("cartCount", 0),
            "add_to_cart_prev": past.get("cartCount", 0),
            # Favorites
            "add_to_favorites": selected.get("addToWishlist", 0),
            "add_to_favorites_prev": past.get("addToWishlist", 0),
            # Orders
            "orders_qty": selected.get("orderCount", 0),
            "orders_qty_prev": past.get("orderCount", 0),
            # Purchased
            "purchased_qty": selected.get("buyoutCount", 0),
            "purchased_qty_prev": past.get("buyoutCount", 0),
            # Cancelled
            "cancelled_qty": selected.get("cancelCount", 0),
            "cancelled_qty_prev": past.get("cancelCount", 0),
            # Cart conversion
            "cart_conversion": selected.get("conversions", {}).get(
                "addToCartPercent", 0
            ),
            "cart_conversion_prev": past.get("conversions", {}).get(
                "addToCartPercent", 0
            ),
            # Order conversion
            "order_conversion": selected.get("conversions", {}).get(
                "cartToOrderPercent", 0
            ),
            "order_conversion_prev": past.get("conversions", {}).get(
                "cartToOrderPercent", 0
            ),
            # Purchase rate
            "purchase_rate": selected.get("conversions", {}).get("buyoutPercent", 0),
            "purchase_rate_prev": past.get("conversions", {}).get("buyoutPercent", 0),
            # Order values
            "orders_value": selected.get("orderSum", 0),
            "orders_value_prev": past.get("orderSum", 0),
            "orders_dynamics": selected.get("orderSum", 0) - past.get("orderSum", 0),
            # Purchased values
            "purchased_value": selected.get("buyoutSum", 0),
            "purchased_value_prev": past.get("buyoutSum", 0),
            # Cancelled values
            "cancelled_value": selected.get("cancelSum", 0),
            "cancelled_value_prev": past.get("cancelSum", 0),
            # Average price
            "avg_price": selected.get("avgPrice", 0),
            "avg_price_prev": past.get("avgPrice", 0),
            # Average daily orders
            "avg_daily_orders": selected.get("avgOrdersCountPerDay", 0),
            "avg_daily_orders_prev": past.get("avgOrdersCountPerDay", 0),
            # Stocks - from product.stocks
            "stock_wb": product.get("stocks", {}).get("wb", 0),
            "stock_mp": product.get("stocks", {}).get("mp", 0),
            "stock_value": product.get("stocks", {}).get("balanceSum", 0),
            # Delivery time
            "delivery_time": round(delivery_hours, 1),
            "delivery_time_prev": round(delivery_hours_prev, 1),
            # Local orders
            "local_orders_pct": selected.get("localizationPercent", 0),
            "local_orders_pct_prev": past.get("localizationPercent", 0),
        }

        records.append(record)

    return records
