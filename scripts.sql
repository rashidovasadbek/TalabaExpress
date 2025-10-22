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