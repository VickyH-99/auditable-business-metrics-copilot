CREATE TABLE IF NOT EXISTS fact_delivery_orders (
    order_id VARCHAR(64) PRIMARY KEY,
    statistics_date DATE NOT NULL,
    delivery_time TIMESTAMP NOT NULL,
    channel VARCHAR(50) NOT NULL,
    region_group VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    store_id VARCHAR(50) NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    sales_person_id VARCHAR(50) NOT NULL,
    sales_person_name VARCHAR(100) NOT NULL,
    business_type VARCHAR(20) NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    sales_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    gross_profit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    customer_id VARCHAR(64) NOT NULL,
    customer_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_fact_delivery_orders_statistics_date
    ON fact_delivery_orders (statistics_date);

CREATE INDEX IF NOT EXISTS ix_fact_delivery_orders_business_type
    ON fact_delivery_orders (business_type);

CREATE INDEX IF NOT EXISTS ix_fact_delivery_orders_order_status
    ON fact_delivery_orders (order_status);

CREATE INDEX IF NOT EXISTS ix_fact_delivery_orders_city
    ON fact_delivery_orders (city);

CREATE INDEX IF NOT EXISTS ix_fact_delivery_orders_region_group
    ON fact_delivery_orders (region_group);

