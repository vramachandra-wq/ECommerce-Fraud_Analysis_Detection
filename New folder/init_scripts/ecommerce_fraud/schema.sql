CREATE SCHEMA IF NOT EXISTS master;

-- PROGRAM MASTER
CREATE TABLE IF NOT EXISTS master.program_master (
    program_id        VARCHAR(10)     PRIMARY KEY,
    program_name      VARCHAR(100)    NOT NULL,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- DEVICE MASTER
CREATE TABLE IF NOT EXISTS master.device_master (
    device_id        VARCHAR(50)     PRIMARY KEY,
    device_name      VARCHAR(100)    NOT NULL,
    device_type      VARCHAR(50)     NOT NULL,
    created_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ANALYST USERS
CREATE TABLE IF NOT EXISTS master.analyst_users (
    analyst_id      VARCHAR(20)     PRIMARY KEY,
    employee_name   VARCHAR(100)    NOT NULL,
    username        VARCHAR(50)     UNIQUE NOT NULL,
    password        VARCHAR(255)    NOT NULL,
    role            VARCHAR(50)     NOT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- RULE MASTER
CREATE TYPE time_interval_unit AS ENUM (
    'MINUTE',
    'HOUR',
    'DAY'
);

CREATE TABLE IF NOT EXISTS master.rule_master (
    rule_id VARCHAR(10) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_description TEXT,
    rule_type VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,
    threshold_value NUMERIC(10,2),
    time_interval_value INT,
    time_interval_unit time_interval_unit,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_time_interval
        CHECK (
            (time_interval_value IS NULL AND time_interval_unit IS NULL) OR
            (time_interval_value IS NOT NULL AND time_interval_unit IS NOT NULL)
        )
);

-- PRODUCTS
CREATE TABLE IF NOT EXISTS master.products (
    product_id        VARCHAR(20)     PRIMARY KEY,
    product_name      VARCHAR(150)    NOT NULL,
    category          VARCHAR(100)    NOT NULL,
    price             NUMERIC(12,2)   NOT NULL,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- IP BLACKLIST
CREATE TABLE IF NOT EXISTS master.ip_blacklist (
    blacklist_id     SERIAL          PRIMARY KEY,
    ip_address       VARCHAR(50)     NOT NULL,
    reason           TEXT            NOT NULL,
    is_active        BOOLEAN         NOT NULL DEFAULT TRUE,
    blacklisted_by   VARCHAR(20)     REFERENCES master.analyst_users(analyst_id),
    blacklisted_at   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    removed_by       VARCHAR(20)     REFERENCES master.analyst_users(analyst_id),
    removed_at       TIMESTAMP
);

CREATE TABLE master.phone_blacklist (
    blacklist_id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    blacklisted_by VARCHAR(100),
    blacklisted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_by VARCHAR(100),
    removed_at TIMESTAMP
);

CREATE TABLE master.email_blacklist (
    blacklist_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    blacklisted_by VARCHAR(100),
    blacklisted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_by VARCHAR(100),
    removed_at TIMESTAMP
);

-- ANALYST PERMISSIONS
CREATE TABLE IF NOT EXISTS master.analyst_permissions (
    analyst_id   VARCHAR(20) NOT NULL REFERENCES master.analyst_users(analyst_id),
    page_key     VARCHAR(50) NOT NULL CHECK (page_key IN ('FRAUD_DASHBOARD', 'ADMIN_PANEL', 'POWER_BI_DASHBOARD', 'AI_CHATBOT')),
    granted      BOOLEAN NOT NULL DEFAULT TRUE,
    granted_by   VARCHAR(20) REFERENCES master.analyst_users(analyst_id),
    granted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (analyst_id, page_key)
);

-- CUSTOMERS
CREATE TABLE IF NOT EXISTS master.customers (
    user_id           VARCHAR(20)     PRIMARY KEY,
    customer_name     VARCHAR(100)    NOT NULL,
    email             VARCHAR(100)    NOT NULL,
    phone_number      VARCHAR(20),
    default_address   TEXT,
    street            VARCHAR(255),
    city              VARCHAR(100),
    state             VARCHAR(100),
    country           VARCHAR(100)    DEFAULT 'India',
    zip_code          VARCHAR(20),
    program_id        VARCHAR(10)     REFERENCES master.program_master(program_id),
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    password          VARCHAR(50)
);

-- ORDERS
CREATE TABLE IF NOT EXISTS master.orders (
    order_id          VARCHAR(20)    PRIMARY KEY,
    user_id           VARCHAR(20)    NOT NULL REFERENCES master.customers(user_id),
    customer_name     VARCHAR(100),
    email             VARCHAR(100),
    phone_number      VARCHAR(20),
    address           TEXT,
    street            VARCHAR(255),
    city              VARCHAR(100),
    state             VARCHAR(100),
    country           VARCHAR(100)   DEFAULT 'India',
    zip_code          VARCHAR(20),
    program_id        VARCHAR(10)    REFERENCES master.program_master(program_id),
    product_id        VARCHAR(20)    REFERENCES master.products(product_id),
    category          VARCHAR(100),
    product_name      VARCHAR(150),
    quantity          INT            DEFAULT 1,
    amount            NUMERIC(12,2)  NOT NULL,
    order_timestamp   TIMESTAMP      NOT NULL,
    order_status      VARCHAR(30)    DEFAULT 'APPROVED' CHECK (order_status IN ('APPROVED', 'PENDING_REVIEW', 'ON_HOLD', 'REJECTED')),
    order_approved_at TIMESTAMP,
    order_rejected_at TIMESTAMP,
    delay_minutes     INT            DEFAULT 0,
    ip_address        VARCHAR(50),
    device_id         VARCHAR(50)    REFERENCES master.device_master(device_id),
    is_fraud          BOOLEAN        DEFAULT FALSE,
    flagged_reason    TEXT,
    reviewed_by       VARCHAR(20)    REFERENCES master.analyst_users(analyst_id),
    review_comments   TEXT
);

-- Order Rule Hit
CREATE TABLE IF NOT EXISTS master.order_rule_hits (
    hit_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES master.orders(order_id) ON DELETE CASCADE,
    rule_id VARCHAR(10) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS master.ai_chat_logs (
    chat_log_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    generated_sql TEXT,
    result_table JSONB,
    generated_summary TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);