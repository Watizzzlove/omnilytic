"""
WB API Client - fetches analytics data from Wildberries Seller API
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional


WB_ANALYTICS_BASE = "https://seller-analytics-api.wildberries.ru"

# Rate limit: 3 req/min for Personal token
RATE_LIMIT_DELAY = 21  # seconds between paginated requests
PAGE_SIZE = 1000


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
    if not past_from or not past_to:
        sel_start = datetime.strptime(date_from, "%Y-%m-%d")
        sel_end = datetime.strptime(date_to, "%Y-%m-%d")
        delta = sel_end - sel_start
        past_end = sel_start - timedelta(days=1)
        past_start = past_end - delta
        past_from = past_start.strftime("%Y-%m-%d")
        past_to = past_end.strftime("%Y-%m-%d")

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
            # Impressions - API doesn't have separate impressions field,
            # use openCount (card views) as the closest metric
            "impressions": 0,
            "impressions_prev": 0,
            # CTR - from conversions
            "ctr": selected.get("conversions", {}).get("addToCartPercent", 0),
            "ctr_prev": past.get("conversions", {}).get("addToCartPercent", 0),
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
