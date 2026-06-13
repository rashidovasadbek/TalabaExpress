CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    username CHARACTER VARYING(255),
    balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    referrer_id BIGINT DEFAULT NULL
);

CREATE TABLE channels (
    id SERIAL PRIMARY KEY,
    username TEXT
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id),
    amount NUMERIC(10, 2) NOT NULL,
    type CHARACTER VARYING(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_transactions_user_id ON transactions (user_id);

ALTER TABLE users ADD COLUMN referral_bonus_paid BOOLEAN DEFAULT FALSE;

-- AI prompt sozlamalari (admin /prompt paneli shu jadvaldan foydalanadi)
CREATE TABLE IF NOT EXISTS settings (
    key CHARACTER VARYING(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

-- Generatsiya yozuvlari (create_ai_work_record / update_ai_work_status)
CREATE TABLE IF NOT EXISTS ai_works (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id),
    topic TEXT,
    work_type CHARACTER VARYING(50),
    page_range CHARACTER VARYING(50),
    cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    debit_transaction_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_works_user_id ON ai_works (user_id);