CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT,
    rest_day TEXT,
    base_pay REAL,
    daily_rate REAL,
    hourly_rate REAL
);

CREATE TABLE IF NOT EXISTS payrolls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    cutoff TEXT,
    total_earnings REAL,
    total_deductions REAL,
    netpay REAL,
    data_json TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
