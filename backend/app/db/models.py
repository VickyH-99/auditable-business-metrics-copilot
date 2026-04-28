from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FactDeliveryOrder(Base):
    __tablename__ = "fact_delivery_orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    statistics_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    region_group: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    store_id: Mapped[str] = mapped_column(String(50), nullable=False)
    store_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sales_person_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sales_person_name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_type: Mapped[str] = mapped_column(String(20), nullable=False)
    order_status: Mapped[str] = mapped_column(String(20), nullable=False)
    sales_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_fact_delivery_orders_statistics_date", "statistics_date"),
        Index("ix_fact_delivery_orders_business_type", "business_type"),
        Index("ix_fact_delivery_orders_order_status", "order_status"),
        Index("ix_fact_delivery_orders_city", "city"),
        Index("ix_fact_delivery_orders_region_group", "region_group"),
    )

