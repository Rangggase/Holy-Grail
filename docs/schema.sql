-- Skema Holy Grail POS (SQLite). Dihasilkan dari holygrail/db.py. Sumber kebenaran: db.py.
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
	customer_id INTEGER NOT NULL, 
	name VARCHAR(60) NOT NULL, 
	name_key VARCHAR(60) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_customers PRIMARY KEY (customer_id), 
	CONSTRAINT ck_customers_name_min_length CHECK (length(trim(name)) >= 2), 
	CONSTRAINT uq_customers_name_key UNIQUE (name_key)
);


CREATE TABLE menu (
	menu_id INTEGER NOT NULL, 
	menu_name VARCHAR(80) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	price INTEGER NOT NULL, 
	stock INTEGER DEFAULT '0' NOT NULL, 
	is_active INTEGER DEFAULT '1' NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_menu PRIMARY KEY (menu_id), 
	CONSTRAINT ck_menu_price_positive CHECK (price > 0), 
	CONSTRAINT ck_menu_stock_non_negative CHECK (stock >= 0), 
	CONSTRAINT ck_menu_active_bool CHECK (is_active IN (0, 1)), 
	CONSTRAINT uq_menu_menu_name UNIQUE (menu_name)
);

CREATE INDEX ix_menu_category ON menu (category);

CREATE TABLE staff (
	staff_id INTEGER NOT NULL, 
	username VARCHAR(40) NOT NULL, 
	full_name VARCHAR(80) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	is_active INTEGER DEFAULT '1' NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_staff PRIMARY KEY (staff_id), 
	CONSTRAINT ck_staff_role_valid CHECK (role IN ('admin', 'kasir')), 
	CONSTRAINT ck_staff_active_bool CHECK (is_active IN (0, 1)), 
	CONSTRAINT ck_staff_username_format CHECK (username = lower(username) AND length(username) >= 3), 
	CONSTRAINT uq_staff_username UNIQUE (username)
);


CREATE TABLE transactions (
	trx_id INTEGER NOT NULL, 
	idempotency_key VARCHAR(64) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	cashier_id INTEGER, 
	created_at DATETIME NOT NULL, 
	weather VARCHAR(10) NOT NULL, 
	group_size VARCHAR(10) NOT NULL, 
	time_of_day VARCHAR(10) NOT NULL, 
	payment_method VARCHAR(20) NOT NULL, 
	total INTEGER NOT NULL, 
	paid INTEGER NOT NULL, 
	change_amount INTEGER NOT NULL, 
	CONSTRAINT pk_transactions PRIMARY KEY (trx_id), 
	CONSTRAINT ck_transactions_weather_valid CHECK (weather IN ('Cerah', 'Hujan')), 
	CONSTRAINT ck_transactions_group_valid CHECK (group_size IN ('Sendiri', 'Keluarga')), 
	CONSTRAINT ck_transactions_time_valid CHECK (time_of_day IN ('Pagi', 'Siang', 'Sore', 'Malam')), 
	CONSTRAINT ck_transactions_payment_valid CHECK (payment_method IN ('Tunai', 'QRIS', 'Debit/Kredit')), 
	CONSTRAINT ck_transactions_total_positive CHECK (total > 0), 
	CONSTRAINT ck_transactions_paid_covers_total CHECK (paid >= total), 
	CONSTRAINT ck_transactions_change_consistent CHECK (change_amount = paid - total), 
	CONSTRAINT uq_transactions_idempotency_key UNIQUE (idempotency_key), 
	CONSTRAINT fk_transactions_customer_id_customers FOREIGN KEY(customer_id) REFERENCES customers (customer_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_transactions_cashier_id_staff FOREIGN KEY(cashier_id) REFERENCES staff (staff_id) ON DELETE RESTRICT
);

CREATE INDEX ix_transactions_created_at ON transactions (created_at);
CREATE INDEX ix_transactions_customer ON transactions (customer_id);

CREATE TABLE stock_movements (
	movement_id INTEGER NOT NULL, 
	menu_id INTEGER NOT NULL, 
	delta INTEGER NOT NULL, 
	reason VARCHAR(12) NOT NULL, 
	note TEXT, 
	staff_id INTEGER, 
	trx_id INTEGER, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_stock_movements PRIMARY KEY (movement_id), 
	CONSTRAINT ck_stock_movements_delta_nonzero CHECK (delta <> 0), 
	CONSTRAINT ck_stock_movements_reason_valid CHECK (reason IN ('initial', 'restock', 'adjustment', 'sale')), 
	CONSTRAINT fk_stock_movements_menu_id_menu FOREIGN KEY(menu_id) REFERENCES menu (menu_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_stock_movements_staff_id_staff FOREIGN KEY(staff_id) REFERENCES staff (staff_id) ON DELETE SET NULL, 
	CONSTRAINT fk_stock_movements_trx_id_transactions FOREIGN KEY(trx_id) REFERENCES transactions (trx_id) ON DELETE SET NULL
);

CREATE INDEX ix_stock_movements_menu ON stock_movements (menu_id);

CREATE TABLE transaction_items (
	item_id INTEGER NOT NULL, 
	trx_id INTEGER NOT NULL, 
	menu_id INTEGER NOT NULL, 
	qty INTEGER NOT NULL, 
	unit_price INTEGER NOT NULL, 
	subtotal INTEGER NOT NULL, 
	CONSTRAINT pk_transaction_items PRIMARY KEY (item_id), 
	CONSTRAINT ck_transaction_items_qty_range CHECK (qty > 0 AND qty <= 99), 
	CONSTRAINT ck_transaction_items_unit_price_positive CHECK (unit_price > 0), 
	CONSTRAINT ck_transaction_items_subtotal_consistent CHECK (subtotal = qty * unit_price), 
	CONSTRAINT uq_items_trx_menu UNIQUE (trx_id, menu_id), 
	CONSTRAINT fk_transaction_items_trx_id_transactions FOREIGN KEY(trx_id) REFERENCES transactions (trx_id) ON DELETE CASCADE, 
	CONSTRAINT fk_transaction_items_menu_id_menu FOREIGN KEY(menu_id) REFERENCES menu (menu_id) ON DELETE RESTRICT
);

CREATE INDEX ix_items_menu ON transaction_items (menu_id);
