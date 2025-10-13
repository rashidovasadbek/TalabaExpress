CREATE TABLE IF NOT EXISTS chennels(
id  SERIAL PRIMARY KEY,
username TEXT UNIQUE NOT NULL
)
CREATE TABLE settings (
    id INTEGER PRIMARY KEY, 
    description TEXT NOT NULL, 
    comment VARCHAR(255)
);

INSERT INTO settings (id, description, comment)
VALUES (
);

INSERT INTO settings (id, description, comment)
VALUES (
);

CREATE TABLE IF NOT EXISTS users(
	id SERIAL PRIMARY KEY,
	username VARCHAR(255),
	full_name VARCHAR(255) NOT NULL,
	balance  NUMERIC(10, 2)  DEFAULT 0.00 NOT NULL,
	free_trial_used BOOLEAN DEFAULT FALSE NOT NULL,
	registres_at TIMESTAMP  WITH  TIME ZONE DEFAULT  CURRENT_TIMESTAMP
)

CREATE TABLE IF NOT EXISTS transaction (
	id SERIAL PRIMARY KEY,
	user_id BIGINT NOT NULL REFERENCES  users(telegram_id),
	amout NUMERIC(10,2) NOT NULL,
	type VARCHAR(50) NOT NULL,
	ai_work_id INTEGER,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE IF NOT EXISTS ai_wroks(
	id SERIAL PRIMARY KEY,
	user_id BIGINT  NOT NULL REFERENCES users(telegram_id),
	topic VARCHAR(500) NOT NULL,
	work_type VARCHAR(50) NOT NULL,
	page_range VARCHAR(10) NOT NULL,
	cost NUMERIC(10,2) NOT NULL,
	debit_transaction_id INTEGER  REFERENCES transaction (id),
	is_free_trial BOOLEAN DEFAULT FALSE  NOT NULL,
	is_completed BOOLEAN DEFAULT FALSE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)

ALTER TABLE users
DROP COLUMN full_name

ALTER TABLE users
DROP COLUMN free_trial_used

ALTER TABLE ai_wroks
RENAME TO ai_works

ALTER TABLE transaction
RENAME TO transactions

ALTER TABLE ai_works
DROP COLUMN is_free_trial

ALTER TABLE transactions
RENAME amout TO amount

ALTER TABLE users 
ALTER COLUMN telegram_id TYPE BIGINT

ALTER TABLE transactions 
ALTER COLUMN user_id TYPE BIGINT;	

ALTER TABLE ai_works 
ALTER COLUMN user_id TYPE BIGINT;

ALTER TABLE users ADD COLUMN referrer_id BIGINT DEFAULT NULL;