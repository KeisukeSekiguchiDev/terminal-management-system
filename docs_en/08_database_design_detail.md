# Database Detailed Design Document
## TechCore Solutions TMS

**Document Version**: 1.0
**Created**: November 24, 2025
**Target**: Devin Auto-implementation

---

## 1. Database Basic Information

### 1.1 Database Specifications
- **DBMS**: PostgreSQL 14.x
- **Character Encoding**: UTF-8
- **Collation**: ja_JP.UTF-8
- **Timezone**: Asia/Tokyo
- **Database Name**: tms_db
- **Schema**: public

### 1.2 Naming Conventions
- Table names: snake_case, plural (e.g., terminals)
- Column names: snake_case (e.g., serial_number)
- Index names: idx_tablename_columnname (e.g., idx_terminals_serial_number)
- Foreign key names: fk_tablename_referencetablename (e.g., fk_terminals_customers)

---

## 2. Table Definitions

### 2.1 customers (Customer Companies)

```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL UNIQUE,
    company_name_kana VARCHAR(100),
    contact_person VARCHAR(50) NOT NULL,
    contact_email VARCHAR(254) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    postal_code VARCHAR(8),
    address TEXT,
    contract_type VARCHAR(20) NOT NULL DEFAULT 'basic',
    contract_start_date DATE NOT NULL,
    contract_end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    max_terminals INTEGER DEFAULT 100,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- Indexes
CREATE INDEX idx_customers_company_name ON customers(company_name);
CREATE INDEX idx_customers_is_active ON customers(is_active);
CREATE INDEX idx_customers_contract_type ON customers(contract_type);

-- Comments
COMMENT ON TABLE customers IS 'Customer company master';
COMMENT ON COLUMN customers.contract_type IS 'basic:Basic, standard:Standard, premium:Premium';
```

### 2.2 terminals (Terminals)

```sql
CREATE TABLE terminals (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL,
    model VARCHAR(20) NOT NULL DEFAULT 'TC-200',
    store_name VARCHAR(100) NOT NULL,
    store_code VARCHAR(20),
    installation_address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    firmware_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    agent_version VARCHAR(20),
    ip_address INET,
    mac_address MACADDR,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    installed_date DATE,
    warranty_end_date DATE,

    -- Metrics
    cpu_usage SMALLINT DEFAULT 0 CHECK (cpu_usage >= 0 AND cpu_usage <= 100),
    memory_usage SMALLINT DEFAULT 0 CHECK (memory_usage >= 0 AND memory_usage <= 100),
    disk_usage SMALLINT DEFAULT 0 CHECK (disk_usage >= 0 AND disk_usage <= 100),
    temperature SMALLINT,

    -- Settings
    heartbeat_interval INTEGER DEFAULT 300, -- seconds
    auto_update_enabled BOOLEAN DEFAULT TRUE,
    maintenance_mode BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Indexes
CREATE UNIQUE INDEX idx_terminals_serial_number ON terminals(serial_number);
CREATE INDEX idx_terminals_customer_id ON terminals(customer_id);
CREATE INDEX idx_terminals_status ON terminals(status);
CREATE INDEX idx_terminals_last_heartbeat ON terminals(last_heartbeat);
CREATE INDEX idx_terminals_store_name ON terminals(customer_id, store_name);

-- Comments
COMMENT ON TABLE terminals IS 'Terminal master';
COMMENT ON COLUMN terminals.status IS 'online:Online, offline:Offline, error:Error, maintenance:Maintenance';
```

### 2.3 terminal_logs (Terminal Logs)

```sql
CREATE TABLE terminal_logs (
    id BIGSERIAL PRIMARY KEY,
    terminal_id INTEGER NOT NULL,
    log_type VARCHAR(20) NOT NULL,
    log_level VARCHAR(10) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (terminal_id) REFERENCES terminals(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_terminal_logs_terminal_id ON terminal_logs(terminal_id);
CREATE INDEX idx_terminal_logs_created_at ON terminal_logs(created_at DESC);
CREATE INDEX idx_terminal_logs_log_type ON terminal_logs(log_type);
CREATE INDEX idx_terminal_logs_log_level ON terminal_logs(log_level) WHERE log_level IN ('ERROR', 'CRITICAL');

-- Partitioning (monthly)
-- Configuration for automatically deleting old logs
CREATE TABLE terminal_logs_2025_01 PARTITION OF terminal_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### 2.4 alerts (Alerts)

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    terminal_id INTEGER NOT NULL,
    alert_type VARCHAR(30) NOT NULL,
    severity VARCHAR(10) NOT NULL DEFAULT 'WARNING',
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    auto_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (terminal_id) REFERENCES terminals(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_alerts_terminal_id ON alerts(terminal_id);
CREATE INDEX idx_alerts_is_resolved ON alerts(is_resolved);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity) WHERE is_resolved = FALSE;
CREATE INDEX idx_alerts_alert_type ON alerts(alert_type);

-- Comments
COMMENT ON COLUMN alerts.severity IS 'CRITICAL:Critical, HIGH:High, MEDIUM:Medium, LOW:Low, INFO:Information';
COMMENT ON COLUMN alerts.alert_type IS 'offline,error,high_cpu,high_memory,update_failed,etc';
```

### 2.5 firmware_versions (Firmware Versions)

```sql
CREATE TABLE firmware_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    model VARCHAR(20) NOT NULL DEFAULT 'TC-200',
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_url TEXT,
    release_notes TEXT,
    is_mandatory BOOLEAN DEFAULT FALSE,
    is_latest BOOLEAN DEFAULT FALSE,
    min_agent_version VARCHAR(20),
    released_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50)
);

-- Indexes
CREATE UNIQUE INDEX idx_firmware_versions_version_model ON firmware_versions(version, model);
CREATE INDEX idx_firmware_versions_is_latest ON firmware_versions(is_latest) WHERE is_latest = TRUE;
```

### 2.6 update_tasks (Update Tasks)

```sql
CREATE TABLE update_tasks (
    id SERIAL PRIMARY KEY,
    terminal_id INTEGER NOT NULL,
    task_type VARCHAR(20) NOT NULL,
    firmware_version_id INTEGER,
    parameters JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),

    FOREIGN KEY (terminal_id) REFERENCES terminals(id) ON DELETE CASCADE,
    FOREIGN KEY (firmware_version_id) REFERENCES firmware_versions(id)
);

-- Indexes
CREATE INDEX idx_update_tasks_terminal_id ON update_tasks(terminal_id);
CREATE INDEX idx_update_tasks_status ON update_tasks(status);
CREATE INDEX idx_update_tasks_scheduled_at ON update_tasks(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_update_tasks_priority ON update_tasks(priority, scheduled_at);

-- Comments
COMMENT ON COLUMN update_tasks.task_type IS 'firmware:Firmware update, config:Config update, reboot:Reboot, etc';
COMMENT ON COLUMN update_tasks.status IS 'pending:Pending, running:Running, completed:Completed, failed:Failed, cancelled:Cancelled';
```

### 2.7 users (System Users)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    password_hash VARCHAR(255) NOT NULL,
    password_reset_token VARCHAR(100),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Comments
COMMENT ON COLUMN users.role IS 'admin:Administrator, operator:Operator, support:Support, viewer:Viewer';
```

### 2.8 audit_logs (Audit Logs)

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path TEXT,
    request_body JSONB,
    response_status INTEGER,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
```

---

## 3. View Definitions

### 3.1 v_terminal_summary (Terminal Summary View)

```sql
CREATE VIEW v_terminal_summary AS
SELECT
    t.id,
    t.serial_number,
    t.model,
    c.company_name,
    t.store_name,
    t.status,
    t.firmware_version,
    t.last_heartbeat,
    CASE
        WHEN t.last_heartbeat > NOW() - INTERVAL '5 minutes' THEN 'online'
        WHEN t.last_heartbeat > NOW() - INTERVAL '30 minutes' THEN 'warning'
        ELSE 'offline'
    END as connectivity_status,
    COUNT(DISTINCT a.id) FILTER (WHERE a.is_resolved = FALSE) as active_alerts,
    t.cpu_usage,
    t.memory_usage,
    t.disk_usage
FROM terminals t
LEFT JOIN customers c ON t.customer_id = c.id
LEFT JOIN alerts a ON t.id = a.terminal_id
GROUP BY t.id, c.company_name;
```

### 3.2 v_daily_statistics (Daily Statistics View)

```sql
CREATE VIEW v_daily_statistics AS
SELECT
    DATE(created_at) as date,
    COUNT(DISTINCT terminal_id) as active_terminals,
    COUNT(*) as total_heartbeats,
    AVG(cpu_usage) as avg_cpu_usage,
    AVG(memory_usage) as avg_memory_usage,
    COUNT(*) FILTER (WHERE log_level = 'ERROR') as error_count
FROM terminal_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## 4. Stored Procedures

### 4.1 Terminal Status Update

```sql
CREATE OR REPLACE FUNCTION update_terminal_status()
RETURNS void AS $$
BEGIN
    -- Set terminals offline if no communication for 5+ minutes
    UPDATE terminals
    SET status = 'offline',
        updated_at = CURRENT_TIMESTAMP
    WHERE last_heartbeat < NOW() - INTERVAL '5 minutes'
    AND status != 'offline';

    -- Auto-generate alerts
    INSERT INTO alerts (terminal_id, alert_type, severity, title, message)
    SELECT
        id,
        'offline',
        'HIGH',
        'Terminal Offline',
        CONCAT('Terminal ', serial_number, ' has been offline for more than 5 minutes')
    FROM terminals
    WHERE status = 'offline'
    AND last_heartbeat < NOW() - INTERVAL '5 minutes'
    AND NOT EXISTS (
        SELECT 1 FROM alerts
        WHERE terminal_id = terminals.id
        AND alert_type = 'offline'
        AND is_resolved = FALSE
    );
END;
$$ LANGUAGE plpgsql;
```

### 4.2 Old Log Cleanup

```sql
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS void AS $$
BEGIN
    -- Delete logs older than 90 days
    DELETE FROM terminal_logs
    WHERE created_at < NOW() - INTERVAL '90 days';

    -- Delete resolved alerts older than 180 days
    DELETE FROM alerts
    WHERE is_resolved = TRUE
    AND resolved_at < NOW() - INTERVAL '180 days';

    -- Delete audit logs older than 365 days
    DELETE FROM audit_logs
    WHERE created_at < NOW() - INTERVAL '365 days';
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Triggers

### 5.1 Auto-update Updated Timestamp

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to each table
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_terminals_updated_at BEFORE UPDATE ON terminals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## 6. Initial Data

### 6.1 System Users

```sql
-- Initial administrator user
INSERT INTO users (username, email, full_name, role, password_hash) VALUES
('admin', 'admin@techcore.com', 'System Administrator', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/Lewvfmn0ma/SlWpC.'), -- password: admin123
('operator1', 'operator1@techcore.com', 'Operations Operator 1', 'operator', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/Lewvfmn0ma/SlWpC.'),
('support1', 'support1@techcore.com', 'Support Staff 1', 'support', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/Lewvfmn0ma/SlWpC.');
```

### 6.2 Test Data

```sql
-- Test customers
INSERT INTO customers (company_name, contact_person, contact_email, contact_phone, contract_type, contract_start_date) VALUES
('ABC Store Inc.', 'Taro Yamada', 'yamada@abc-store.jp', '03-1234-5678', 'premium', '2025-01-01'),
('XYZ Trading Co.', 'Hanako Suzuki', 'suzuki@xyz.co.jp', '06-9876-5432', 'standard', '2025-01-01'),
('Tanaka Shop', 'Ichiro Tanaka', 'tanaka@tanaka-shop.jp', '052-555-1234', 'basic', '2025-01-01');

-- Test terminals (actual data insertion from agent)
INSERT INTO terminals (serial_number, customer_id, store_name, status)
SELECT
    'TC-200-TEST-' || LPAD(generate_series::text, 3, '0'),
    (ARRAY[1,2,3])[1 + (generate_series % 3)],
    'Store ' || generate_series,
    CASE WHEN random() > 0.1 THEN 'online' ELSE 'offline' END
FROM generate_series(1, 100);
```

---

## 7. Backup & Restore

### 7.1 Backup Commands

```bash
# Daily backup
pg_dump -h localhost -U postgres -d tms_db -F custom -f tms_backup_$(date +%Y%m%d).dump

# Table-specific backup
pg_dump -h localhost -U postgres -d tms_db -t terminals -F custom -f terminals_backup.dump
```

### 7.2 Restore Commands

```bash
# Full restore
pg_restore -h localhost -U postgres -d tms_db -F custom -c tms_backup_20250124.dump

# Table-specific restore
pg_restore -h localhost -U postgres -d tms_db -F custom -t terminals terminals_backup.dump
```

---

## 8. Performance Optimization

### 8.1 Recommended Settings

```sql
-- PostgreSQL settings (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### 8.2 Regular Maintenance

```sql
-- Weekly execution
VACUUM ANALYZE terminals;
VACUUM ANALYZE terminal_logs;
VACUUM ANALYZE alerts;

-- Monthly execution
REINDEX TABLE terminals;
REINDEX TABLE terminal_logs;
```

---

## 9. Connection Information (Development Environment)

```python
# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tms_db',
        'USER': 'tms_user',
        'PASSWORD': 'tms_password_dev_2025',  # Get from environment variable in production
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 600,
    }
}
```

---

## 10. Migration Procedure

```bash
# 1. Create database
createdb -U postgres tms_db

# 2. Create user
psql -U postgres -c "CREATE USER tms_user WITH PASSWORD 'tms_password_dev_2025';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tms_db TO tms_user;"

# 3. Create tables (execute SQL from this file)
psql -U tms_user -d tms_db -f database_schema.sql

# 4. Django migration
python manage.py makemigrations
python manage.py migrate
```

---

Devin can automatically build the database based on this design document.
