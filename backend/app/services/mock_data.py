from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Engine

from app.db.models import Base, FactDeliveryOrder

CHANNELS = [
    ("线上直营", 1.15),
    ("门店自然到访", 1.0),
    ("经销商合作", 0.92),
    ("企业客户", 0.86),
]

CITY_LAYOUT = {
    "华东大区": {
        "华东一区": {
            "上海": ["上海虹桥门店", "上海浦东门店"],
            "杭州": ["杭州西湖门店", "杭州滨江门店"],
        },
        "华东二区": {
            "苏州": ["苏州工业园门店", "苏州高新区门店"],
            "南京": ["南京河西门店", "南京江北门店"],
        },
    },
    "华南大区": {
        "华南一区": {
            "广州": ["广州天河门店", "广州番禺门店"],
            "深圳": ["深圳南山门店", "深圳龙岗门店"],
        }
    },
    "华北大区": {
        "华北一区": {
            "北京": ["北京望京门店", "北京亦庄门店"],
            "天津": ["天津和平门店", "天津滨海门店"],
        }
    },
}

MONTH_FACTORS = {
    1: 0.92,
    2: 0.88,
    3: 1.01,
    4: 1.06,
    5: 1.08,
    6: 1.1,
    7: 1.16,
    8: 1.13,
    9: 0.99,
    10: 1.05,
    11: 1.16,
    12: 1.24,
}

CITY_FACTORS = {
    "上海": 1.28,
    "北京": 1.23,
    "深圳": 1.18,
    "广州": 1.1,
    "杭州": 1.05,
    "南京": 0.95,
    "苏州": 0.9,
    "天津": 0.82,
}

BUSINESS_PROFILES = {
    "sale": {"share": 0.42, "amount": (210000, 38000), "margin_rate": 0.14},
    "rental": {"share": 0.24, "amount": (42000, 9500), "margin_rate": 0.24},
    "used_car": {"share": 0.18, "amount": (98000, 24000), "margin_rate": 0.1},
    "renewal": {"share": 0.16, "amount": (28000, 6500), "margin_rate": 0.19},
}

CUSTOMER_TYPES = ["individual", "corporate"]


def _build_store_catalog() -> list[dict]:
    stores: list[dict] = []
    store_index = 1
    for region_group, regions in CITY_LAYOUT.items():
        for region, cities in regions.items():
            for city, store_names in cities.items():
                for store_name in store_names:
                    stores.append(
                        {
                            "region_group": region_group,
                            "region": region,
                            "city": city,
                            "store_id": f"STORE-{store_index:03d}",
                            "store_name": store_name,
                            "store_factor": 0.86 + (store_index % 5) * 0.08,
                            "people": [
                                {
                                    "sales_person_id": f"SP-{store_index:03d}-{member:02d}",
                                    "sales_person_name": f"{city}{store_index}号顾问{member}",
                                }
                                for member in range(1, 5)
                            ],
                        }
                    )
                    store_index += 1
    return stores


STORE_CATALOG = _build_store_catalog()


def _weighted_business_type(rng: random.Random, is_weekend: bool) -> str:
    items = []
    for business_type, profile in BUSINESS_PROFILES.items():
        weight = profile["share"]
        if is_weekend and business_type == "rental":
            weight *= 1.18
        if not is_weekend and business_type == "sale":
            weight *= 1.08
        items.append((business_type, weight))

    total = sum(weight for _, weight in items)
    target = rng.random() * total
    cursor = 0.0
    for business_type, weight in items:
        cursor += weight
        if cursor >= target:
            return business_type
    return "sale"


def generate_mock_orders(start_date: date, end_date: date, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    orders: list[dict] = []
    current = start_date
    order_sequence = 1

    total_days = max((end_date - start_date).days, 1)

    while current <= end_date:
        is_weekend = current.weekday() >= 5
        year_progress = (current - start_date).days / total_days
        growth_factor = 0.92 + year_progress * 0.28
        weekend_factor = 1.12 if is_weekend else 0.97
        seasonality = MONTH_FACTORS[current.month]

        for store in STORE_CATALOG:
            city_factor = CITY_FACTORS[store["city"]]
            expected_orders = 2.6 * store["store_factor"] * city_factor * growth_factor * seasonality * weekend_factor
            noise = rng.uniform(0.78, 1.26)
            daily_orders = max(0, int(round(expected_orders * noise)))

            for _ in range(daily_orders):
                business_type = _weighted_business_type(rng, is_weekend)
                profile = BUSINESS_PROFILES[business_type]
                channel_name, channel_factor = rng.choices(
                    [item[0] for item in CHANNELS],
                    weights=[item[1] for item in CHANNELS],
                    k=1,
                )[0], None
                for item in CHANNELS:
                    if item[0] == channel_name:
                        channel_factor = item[1]
                        break

                salesperson = rng.choice(store["people"])
                order_status = "completed" if rng.random() > 0.08 else "cancelled"
                mean_amount, amount_sigma = profile["amount"]
                sales_amount_value = max(
                    8000.0,
                    rng.gauss(mean_amount * (channel_factor or 1.0), amount_sigma),
                )
                gross_profit_value = sales_amount_value * profile["margin_rate"] * rng.uniform(0.82, 1.22)
                if order_status == "cancelled":
                    sales_amount_value *= 0.08
                    gross_profit_value *= 0.04

                delivery_hour = rng.randint(9, 20)
                delivery_minute = rng.randint(0, 59)
                delivery_time = datetime.combine(current, time(hour=delivery_hour, minute=delivery_minute))
                created_at = delivery_time - timedelta(days=rng.randint(0, 5), hours=rng.randint(0, 18))
                updated_at = delivery_time + timedelta(hours=rng.randint(0, 10))

                orders.append(
                    {
                        "order_id": f"ORD-{current.strftime('%Y%m%d')}-{order_sequence:07d}",
                        "statistics_date": current,
                        "delivery_time": delivery_time,
                        "channel": channel_name,
                        "region_group": store["region_group"],
                        "region": store["region"],
                        "city": store["city"],
                        "store_id": store["store_id"],
                        "store_name": store["store_name"],
                        "sales_person_id": salesperson["sales_person_id"],
                        "sales_person_name": salesperson["sales_person_name"],
                        "business_type": business_type,
                        "order_status": order_status,
                        "sales_amount": Decimal(str(round(sales_amount_value, 2))),
                        "gross_profit": Decimal(str(round(gross_profit_value, 2))),
                        "customer_id": f"CUST-{rng.randint(100000, 999999)}",
                        "customer_type": rng.choices(CUSTOMER_TYPES, weights=[0.76, 0.24], k=1)[0],
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }
                )
                order_sequence += 1

        current += timedelta(days=1)

    return orders


def seed_database_if_needed(engine: Engine, today: date) -> int:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        existing_count = connection.execute(select(func.count()).select_from(FactDeliveryOrder)).scalar_one()
        if existing_count:
            return int(existing_count)

    start_date = today - timedelta(days=790)
    orders = generate_mock_orders(start_date=start_date, end_date=today)
    table = FactDeliveryOrder.__table__
    batch_size = 1000
    with engine.begin() as connection:
        for offset in range(0, len(orders), batch_size):
            connection.execute(insert(table), orders[offset : offset + batch_size])
    return len(orders)

