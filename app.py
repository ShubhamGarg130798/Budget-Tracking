# Database setup
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # Users table for authentication
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        )
    ''')
    
    # Create default admin user if not exists (password: admin123)
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        import hashlib
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('''
            INSERT INTO users (username, password, full_name, role, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', admin_password, 'System Administrator', 'admin', 'system'))
    
    # Main expenses table with approval workflow
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            added_by TEXT,
            
            -- Approval Stage 1 (Brand Head)
            stage1_status TEXT DEFAULT 'Pending',
            stage1_approved_by TEXT,
            stage1_approved_date TIMESTAMP,
            stage1_remarks TEXT,
            
            -- Approval Stage 2 (Shruti Ma'am)
            stage2_status TEXT DEFAULT 'Pending',
            stage2_approved_by TEXT,
            stage2_approved_date TIMESTAMP,
            stage2_remarks TEXT,
            
            -- Approval Stage 3 (Accounts - Payment)
            stage3_status TEXT DEFAULT 'Pending',
            stage3_paid_by TEXT,
            stage3_paid_date TIMESTAMP,
            stage3_payment_mode TEXT,
            stage3_transaction_ref TEXT,
            stage3_remarks TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
