import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import time

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# USER ROLES
USER_ROLES = {
    "hr": {
        "stage": 0,
        "title": "HR - Brand Staff"
    },
    "brand_heads": {
        "stage": 1,
        "title": "Brand Head"
    },
    "stage2_approver": {
        "stage": 2,
        "title": "Senior Manager"
    },
    "accounts_team": {
        "stage": 3,
        "title": "Accounts Team"
    },
    "admin": {
        "stage": 99,
        "title": "Administrator"
    }
}

# Brand list
BRANDS = [
    "FundoBaBa", "Salary Adda", "FastPaise", "SnapPaisa", "Salary 4 Sure",
    "Duniya Finance", "Tejas", "BlinkR", "Salary Setu", "Qua Loans",
    "Paisa Pop", "Salary 4 You", "Rupee Hype", "Minutes Loan", "Squid Loan",
    "Zepto", "Paisa on Salary", "Jhatpat"
]

# Expense categories with subcategories
CATEGORIES = {
    "Technology & Software": ["AWS", "G-Suite", "IVR-Dialer", "APIs", "Cursar", "Third Party Tool", 
                               "HRMS", "Microsoft 365", "Power BI", "Metabase"],
    "Rental": [],
    "Assets": ["Laptops", "Phone", "SIM"],
    "Utility": ["Electricity Bill", "Water Bill", "Pantry Supplies", "Cleaning Supplies"],
    "Marketing": ["Google", "Meta", "Twitter", "RCS", "Whatsapp", "Affiliate", 
                  "Database Purchase", "Mailgun", "Agency", "Design"],
    "Petty Cash": [],
    "Salaries": [],
    "Incentives": [],
    "Celebrations/Events": [],
    "Maintenance": [],
    "Others": []
}

PAYMENT_MODES = ["Cash", "Bank Transfer", "Cheque", "UPI", "Card", "Other"]

# Database setup
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # Users table
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
    
    # Create default admin user if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('''
            INSERT INTO users (username, password, full_name, role, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', admin_password, 'System Administrator', 'admin', 'system'))
    
    # Expenses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            amount REAL NOT NULL,
            description TEXT,
            bill_document BLOB,
            bill_filename TEXT,
            bill_filetype TEXT,
            added_by TEXT,
            stage1_assigned_to TEXT,
            stage1_status TEXT DEFAULT 'Pending',
            stage1_approved_by TEXT,
            stage1_approved_date TIMESTAMP,
            stage1_remarks TEXT,
            stage2_status TEXT DEFAULT 'Pending',
            stage2_approved_by TEXT,
            stage2_approved_date TIMESTAMP,
            stage2_remarks TEXT,
            stage3_status TEXT DEFAULT 'Pending',
            stage3_paid_by TEXT,
            stage3_paid_date TIMESTAMP,
            stage3_payment_mode TEXT,
            stage3_transaction_ref TEXT,
            stage3_remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if columns exist, add if not (for existing databases)
    c.execute("PRAGMA table_info(expenses)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'stage1_assigned_to' not in columns:
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN stage1_assigned_to TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    
    if 'subcategory' not in columns:
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN subcategory TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    
    if 'bill_document' not in columns:
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN bill_document BLOB")
            c.execute("ALTER TABLE expenses ADD COLUMN bill_filename TEXT")
            c.execute("ALTER TABLE expenses ADD COLUMN bill_filetype TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# User Management Functions
def authenticate_user(username, password):
    """Authenticate user with username and password"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("""
        SELECT username, full_name, role 
        FROM users 
        WHERE username = ? AND password = ? AND is_active = 1
    """, (username, hashed_password))
    result = c.fetchone()
    conn.close()
    
    return result

def create_user(username, password, full_name, role, created_by):
    """Create a new user"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (username, password, full_name, role, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed_password, full_name, role, created_by))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists"
    except Exception as e:
        conn.close()
        return False, str(e)

def get_all_users():
    """Get all users"""
    conn = sqlite3.connect('expenses.db')
    df = pd.read_sql_query("""
        SELECT id, username, full_name, role, is_active, created_at, created_by
        FROM users
        ORDER BY created_at DESC
    """, conn)
    conn.close()
    return df

def update_user_status(user_id, is_active):
    """Activate/Deactivate user"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Delete user"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()
    conn.close()

def reset_user_password(user_id, new_password):
    """Reset user password"""
    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
    
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
    conn.commit()
    conn.close()

# Expense Functions
def add_expense(date, brand, category, subcategory, amount, description, added_by, assigned_to=None, bill_document=None, bill_filename=None, bill_filetype=None):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO expenses (date, brand, category, subcategory, amount, description, added_by, stage1_assigned_to, bill_document, bill_filename, bill_filetype)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, brand, category, subcategory, amount, description, added_by, assigned_to, bill_document, bill_filename, bill_filetype))
    conn.commit()
    conn.close()

def get_brand_heads():
    """Get all users with brand_heads role"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, full_name, username 
        FROM users 
        WHERE role = 'brand_heads' AND is_active = 1
        ORDER BY full_name
    """)
    result = c.fetchall()
    conn.close()
    return result

def update_expense_bill(expense_id, bill_document, bill_filename, bill_filetype):
    """Update expense with bill document"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses 
        SET bill_document = ?, bill_filename = ?, bill_filetype = ?
        WHERE id = ?
    ''', (bill_document, bill_filename, bill_filetype, expense_id))
    conn.commit()
    conn.close()

def change_password(username, old_password, new_password):
    """Change user's own password"""
    # First verify old password
    old_hashed = hashlib.sha256(old_password.encode()).hexdigest()
    new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
    
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # Check if old password is correct
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, old_hashed))
    if not c.fetchone():
        conn.close()
        return False, "Current password is incorrect"
    
    # Update password
    c.execute("UPDATE users SET password = ? WHERE username = ?", (new_hashed, username))
    conn.commit()
    conn.close()
    return True, "Password changed successfully"

def get_all_expenses():
    conn = sqlite3.connect('expenses.db')
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC", conn)
    conn.close()
    return df

def get_expenses_for_approval(stage, username=None):
    """Get expenses pending at specific approval stage"""
    conn = sqlite3.connect('expenses.db')
    if stage == 1:
        # Brand heads only see expenses assigned to them
        if username:
            query = """
                SELECT * FROM expenses 
                WHERE stage1_status = 'Pending' AND stage1_assigned_to = ?
                ORDER BY created_at ASC
            """
            df = pd.read_sql_query(query, conn, params=(username,))
        else:
            query = """
                SELECT * FROM expenses 
                WHERE stage1_status = 'Pending' 
                ORDER BY created_at ASC
            """
            df = pd.read_sql_query(query, conn)
    elif stage == 2:
        query = """
            SELECT * FROM expenses 
            WHERE stage1_status = 'Approved' AND stage2_status = 'Pending' 
            ORDER BY created_at ASC
        """
        df = pd.read_sql_query(query, conn)
    elif stage == 3:
        query = """
            SELECT * FROM expenses 
            WHERE stage1_status = 'Approved' AND stage2_status = 'Approved' 
            AND stage3_status = 'Pending' 
            ORDER BY created_at ASC
        """
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_approved_expenses_by_user(username, stage):
    """Get all expenses approved/rejected by a specific user at a given stage"""
    conn = sqlite3.connect('expenses.db')
    if stage == 1:
        query = """
            SELECT * FROM expenses 
            WHERE stage1_approved_by = ? AND stage1_status IN ('Approved', 'Rejected')
            ORDER BY stage1_approved_date DESC
        """
    elif stage == 2:
        query = """
            SELECT * FROM expenses 
            WHERE stage2_approved_by = ? AND stage2_status IN ('Approved', 'Rejected')
            ORDER BY stage2_approved_date DESC
        """
    elif stage == 3:
        query = """
            SELECT * FROM expenses 
            WHERE stage3_paid_by = ? AND stage3_status IN ('Paid', 'Rejected')
            ORDER BY stage3_paid_date DESC
        """
    df = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return df

def get_expenses_by_user(username):
    """Get all expenses added by a specific user"""
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT * FROM expenses 
        WHERE added_by = ? 
        ORDER BY created_at DESC
    """
    df = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return df

def approve_expense_stage1(expense_id, approved_by, status, remarks):
    """Approve/Reject at Stage 1"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses 
        SET stage1_status = ?, stage1_approved_by = ?, 
            stage1_approved_date = ?, stage1_remarks = ?
        WHERE id = ?
    ''', (status, approved_by, datetime.now(), remarks, expense_id))
    conn.commit()
    conn.close()

def approve_expense_stage2(expense_id, approved_by, status, remarks):
    """Approve/Reject at Stage 2"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses 
        SET stage2_status = ?, stage2_approved_by = ?, 
            stage2_approved_date = ?, stage2_remarks = ?
        WHERE id = ?
    ''', (status, approved_by, datetime.now(), remarks, expense_id))
    conn.commit()
    conn.close()

def approve_expense_stage3(expense_id, paid_by, status, payment_mode, transaction_ref, remarks):
    """Mark as Paid at Stage 3"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses 
        SET stage3_status = ?, stage3_paid_by = ?, 
            stage3_paid_date = ?, stage3_payment_mode = ?,
            stage3_transaction_ref = ?, stage3_remarks = ?
        WHERE id = ?
    ''', (status, paid_by, datetime.now(), payment_mode, transaction_ref, remarks, expense_id))
    conn.commit()
    conn.close()

def get_overall_status(row):
    """Determine overall status of expense"""
    if row['stage3_status'] == 'Paid':
        return '✅ Paid'
    elif row['stage3_status'] == 'Rejected' or row['stage2_status'] == 'Rejected' or row['stage1_status'] == 'Rejected':
        return '❌ Rejected'
    elif row['stage2_status'] == 'Approved':
        return '⏳ Payment Pending'
    elif row['stage1_status'] == 'Approved':
        return '⏳ Stage 2 Approval Pending'
    else:
        return '⏳ Stage 1 Approval Pending'

def get_stage_status_display(row):
    """Get formatted status display for all stages"""
    # Stage 1 - Brand Head
    if row['stage1_status'] == 'Approved':
        s1 = "Brand Head: ✅ Approved"
    elif row['stage1_status'] == 'Rejected':
        s1 = "Brand Head: ❌ Rejected"
    else:
        s1 = "Brand Head: ⏳ Pending"
    
    # Stage 2 - Senior Manager
    if row['stage2_status'] == 'Approved':
        s2 = "Senior Manager: ✅ Approved"
    elif row['stage2_status'] == 'Rejected':
        s2 = "Senior Manager: ❌ Rejected"
    else:
        s2 = "Senior Manager: ⏳ Pending"
    
    # Stage 3 - Accounts
    if row['stage3_status'] == 'Paid':
        s3 = "Accounts: ✅ Paid"
    elif row['stage3_status'] == 'Rejected':
        s3 = "Accounts: ❌ Rejected"
    else:
        s3 = "Accounts: ⏳ Pending"
    
    return f"{s1} | {s2} | {s3}"

def get_category_display(row):
    """Format category and subcategory for display"""
    if pd.notna(row.get('subcategory')) and row['subcategory']:
        return f"{row['category']} - {row['subcategory']}"
    return row['category']

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.full_name = None
    st.session_state.user_role = None

# Login Page
if not st.session_state.logged_in:
    st.title("🔐 Brand Expense Tracker")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 👤 Please Login")
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("🚀 Login", use_container_width=True, type="primary"):
            if username and password:
                user_data = authenticate_user(username, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.username = user_data[0]
                    st.session_state.full_name = user_data[1]
                    st.session_state.user_role = user_data[2]
                    st.success(f"✅ Welcome {user_data[1]}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password!")
            else:
                st.warning("⚠️ Please enter both username and password")
    
    st.stop()

# Main App (After Login)
st.title("💰 Brand Expense Tracker")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"**Logged in as:** {st.session_state.full_name} ({USER_ROLES[st.session_state.user_role]['title']})")
with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.full_name = None
        st.session_state.user_role = None
        st.rerun()

st.markdown("---")

# Navigation
page_options = ["➕ Add Expense"]

if st.session_state.user_role == "hr":
    page_options.extend(["📝 My Expenses", "🔐 Change Password"])
else:
    if st.session_state.user_role in ["brand_heads", "admin"]:
        page_options.append("✅ Approval Stage 1 (Brand Head)")
    
    if st.session_state.user_role in ["stage2_approver", "admin"]:
        page_options.append("✅ Approval Stage 2 (Senior Manager)")
    
    if st.session_state.user_role in ["accounts_team", "admin"]:
        page_options.append("💳 Approval Stage 3 (Accounts Payment)")
    
    page_options.extend(["📊 Dashboard", "📋 View All Expenses", "🔐 Change Password"])

if st.session_state.user_role == "admin":
    page_options.append("👥 User Management")

page = st.sidebar.selectbox("📌 Navigation", page_options)

# Remove emoji from page name
page_clean = page.split(" ", 1)[1] if " " in page else page

# Page 1: Add Expense
if page_clean == "Add Expense":
    st.header("➕ Add New Expense")
    
    # Category and Subcategory selection OUTSIDE form for dynamic updates
    st.subheader("📂 Select Category")
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category *", options=list(CATEGORIES.keys()), key="expense_category")
    
    with col2:
        # Subcategory selection (conditional based on category)
        if CATEGORIES[category]:  # If subcategories exist for selected category
            subcategory = st.selectbox("Subcategory *", options=CATEGORIES[category], key="expense_subcategory")
        else:
            st.info(f"ℹ️ No subcategories for {category}")
            subcategory = None
    
    st.markdown("---")
    st.subheader("📝 Expense Details")
    
    # Rest of the form
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("📅 Date", value=date.today())
            brand = st.selectbox("🏢 Brand", BRANDS)
            amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
        
        with col2:
            added_by = st.text_input("👤 Added By", value=st.session_state.full_name)
            
            # Get brand heads for assignment
            brand_heads = get_brand_heads()
            if brand_heads:
                brand_head_options = {bh[1]: bh[1] for bh in brand_heads}
                assigned_to = st.selectbox("👨‍💼 Assign to Brand Head *", options=list(brand_head_options.keys()))
            else:
                st.warning("⚠️ No Brand Heads available. Please contact admin.")
                assigned_to = None
        
        description = st.text_area("📝 Description", placeholder="Enter expense details...")
        
        # File upload for bill/document
        uploaded_file = st.file_uploader("📎 Upload Bill/Document (PDF or Image)", type=['pdf', 'png', 'jpg', 'jpeg'], help="Upload bill, invoice or supporting document")
        
        submitted = st.form_submit_button("✅ Add Expense", use_container_width=True, type="primary")
        
        if submitted:
            if amount > 0 and added_by and assigned_to:
                # Process uploaded file
                bill_document = None
                bill_filename = None
                bill_filetype = None
                
                if uploaded_file is not None:
                    bill_document = uploaded_file.read()
                    bill_filename = uploaded_file.name
                    bill_filetype = uploaded_file.type
                
                add_expense(expense_date, brand, category, subcategory, amount, description, added_by, assigned_to, bill_document, bill_filename, bill_filetype)
                st.toast("✅ Expense has been added successfully!", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.error("⚠️ Please fill all required fields!")

# Page 2: My Expenses (HR View)
elif page_clean == "My Expenses":
    st.header("📝 My Submitted Expenses")
    
    my_expenses = get_expenses_by_user(st.session_state.full_name)
    
    if not my_expenses.empty:
        my_expenses['Overall_Status'] = my_expenses.apply(get_overall_status, axis=1)
        my_expenses['Category_Display'] = my_expenses.apply(get_category_display, axis=1)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Amount", f"₹{my_expenses['amount'].sum():,.2f}")
        col2.metric("📝 Total Expenses", len(my_expenses))
        col3.metric("⏳ Pending", len(my_expenses[my_expenses['stage1_status'] == 'Pending']))
        col4.metric("✅ Paid", len(my_expenses[my_expenses['stage3_status'] == 'Paid']))
        
        st.markdown("---")
        
        # Display each expense with detailed status
        for idx, row in my_expenses.iterrows():
            status_display = get_stage_status_display(row)
            
            with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                # Basic Details
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                col2.metric("🏢 Brand", row['brand'])
                col3.metric("📂 Category", row['Category_Display'])
                
                st.markdown(f"**📝 Description:** {row['description']}")
                st.markdown(f"**📅 Expense Date:** {row['date']}")
                st.markdown(f"**🕐 Submitted On:** {row['created_at']}")
                if pd.notna(row.get('stage1_assigned_to')):
                    st.markdown(f"**👨‍💼 Assigned To:** {row['stage1_assigned_to']}")
                
                st.markdown("---")
                
                # Bill/Document Section
                st.markdown("### 📎 Bill/Document")
                has_bill = pd.notna(row.get('bill_filename'))
                
                if has_bill:
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.success(f"✅ Document uploaded: **{row['bill_filename']}**")
                    with col2:
                        if st.download_button(
                            label="📥 Download",
                            data=row['bill_document'],
                            file_name=row['bill_filename'],
                            mime=row['bill_filetype'],
                            key=f"my_download_bill_{row['id']}"
                        ):
                            st.success("Downloaded!")
                else:
                    st.info("ℹ️ No bill/document uploaded yet")
                
                # Allow uploading/updating bill
                uploaded_bill = st.file_uploader(
                    "Upload/Update Bill", 
                    type=['pdf', 'png', 'jpg', 'jpeg'],
                    key=f"my_upload_bill_{row['id']}"
                )
                
                if uploaded_bill is not None:
                    if st.button(f"💾 Save Bill", key=f"my_save_bill_{row['id']}", type="primary"):
                        bill_data = uploaded_bill.read()
                        update_expense_bill(row['id'], bill_data, uploaded_bill.name, uploaded_bill.type)
                        st.toast("✅ Bill has been uploaded successfully!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                
                st.markdown("---")
                
                # Stage 1 Status
                st.markdown("### 📋 Stage 1: Brand Head Approval")
                col1, col2, col3 = st.columns(3)
                
                if row['stage1_status'] == 'Pending':
                    col1.markdown("**Status:** ⏳ Pending")
                    col2.markdown("**Approved By:** -")
                    col3.markdown("**Date:** -")
                elif row['stage1_status'] == 'Approved':
                    col1.markdown("**Status:** ✅ Approved")
                    col2.markdown(f"**Approved By:** {row['stage1_approved_by']}")
                    col3.markdown(f"**Date:** {row['stage1_approved_date']}")
                    if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage1_remarks']}")
                elif row['stage1_status'] == 'Rejected':
                    col1.markdown("**Status:** ❌ Rejected")
                    col2.markdown(f"**Rejected By:** {row['stage1_approved_by']}")
                    col3.markdown(f"**Date:** {row['stage1_approved_date']}")
                    if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage1_remarks']}")
                
                st.markdown("---")
                
                # Stage 2 Status
                st.markdown("### 📋 Stage 2: Senior Manager Approval")
                col1, col2, col3 = st.columns(3)
                
                if row['stage1_status'] != 'Approved':
                    col1.markdown("**Status:** ⏸️ Awaiting Stage 1")
                    col2.markdown("**Approved By:** -")
                    col3.markdown("**Date:** -")
                elif row['stage2_status'] == 'Pending':
                    col1.markdown("**Status:** ⏳ Pending")
                    col2.markdown("**Approved By:** -")
                    col3.markdown("**Date:** -")
                elif row['stage2_status'] == 'Approved':
                    col1.markdown("**Status:** ✅ Approved")
                    col2.markdown(f"**Approved By:** {row['stage2_approved_by']}")
                    col3.markdown(f"**Date:** {row['stage2_approved_date']}")
                    if pd.notna(row.get('stage2_remarks')) and row['stage2_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage2_remarks']}")
                elif row['stage2_status'] == 'Rejected':
                    col1.markdown("**Status:** ❌ Rejected")
                    col2.markdown(f"**Rejected By:** {row['stage2_approved_by']}")
                    col3.markdown(f"**Date:** {row['stage2_approved_date']}")
                    if pd.notna(row.get('stage2_remarks')) and row['stage2_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage2_remarks']}")
                
                st.markdown("---")
                
                # Stage 3 Status (Payment)
                st.markdown("### 📋 Stage 3: Accounts Payment")
                col1, col2, col3 = st.columns(3)
                
                if row['stage1_status'] != 'Approved' or row['stage2_status'] != 'Approved':
                    col1.markdown("**Status:** ⏸️ Awaiting Previous Approvals")
                    col2.markdown("**Processed By:** -")
                    col3.markdown("**Date:** -")
                elif row['stage3_status'] == 'Pending':
                    col1.markdown("**Status:** ⏳ Payment Pending")
                    col2.markdown("**Processed By:** -")
                    col3.markdown("**Date:** -")
                elif row['stage3_status'] == 'Paid':
                    col1.markdown("**Status:** ✅ Paid")
                    col2.markdown(f"**Paid By:** {row['stage3_paid_by']}")
                    col3.markdown(f"**Date:** {row['stage3_paid_date']}")
                    if pd.notna(row.get('stage3_payment_mode')):
                        st.markdown(f"**💳 Payment Mode:** {row['stage3_payment_mode']}")
                    if pd.notna(row.get('stage3_transaction_ref')):
                        st.markdown(f"**🔢 Transaction Ref:** {row['stage3_transaction_ref']}")
                    if pd.notna(row.get('stage3_remarks')) and row['stage3_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage3_remarks']}")
                elif row['stage3_status'] == 'Rejected':
                    col1.markdown("**Status:** ❌ Rejected")
                    col2.markdown(f"**Rejected By:** {row['stage3_paid_by']}")
                    col3.markdown(f"**Date:** {row['stage3_paid_date']}")
                    if pd.notna(row.get('stage3_remarks')) and row['stage3_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage3_remarks']}")
                
                st.markdown("---")
                st.markdown(f"### 📊 **Overall Status: {row['Overall_Status']}**")
    else:
        st.info("📌 You haven't submitted any expenses yet.")

# Page 3: Approval Stage 1
elif "Approval Stage 1" in page_clean:
    st.header("✅ Approval Stage 1 - Brand Head Review")
    
    tab1, tab2 = st.tabs(["⏳ Approval Pending", "✅ Approved/Rejected"])
    
    with tab1:
        st.subheader("Expenses Pending Your Approval")
        
        # Brand heads only see expenses assigned to them
        if st.session_state.user_role == "brand_heads":
            pending_expenses = get_expenses_for_approval(1, st.session_state.full_name)
        else:
            # Admin sees all
            pending_expenses = get_expenses_for_approval(1)
        
        if not pending_expenses.empty:
            pending_expenses['Category_Display'] = pending_expenses.apply(get_category_display, axis=1)
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending approval")
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    if pd.notna(row.get('stage1_assigned_to')):
                        st.markdown(f"**👨‍💼 Assigned To:** {row['stage1_assigned_to']}")
                    st.markdown(f"**📅 Submitted On:** {row['created_at']}")
                    
                    # Show bill if available
                    if pd.notna(row.get('bill_filename')):
                        st.markdown("---")
                        st.markdown("### 📎 Attached Bill/Document")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.success(f"✅ **{row['bill_filename']}**")
                        with col2:
                            st.download_button(
                                label="📥 View Bill",
                                data=row['bill_document'],
                                file_name=row['bill_filename'],
                                mime=row['bill_filetype'],
                                key=f"s1_view_bill_{row['id']}"
                            )
                    else:
                        st.info("ℹ️ No bill attached")
                    
                    st.markdown("---")
                    remarks = st.text_area("💬 Remarks", key=f"remarks_s1_{row['id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_s1_{row['id']}", type="primary", use_container_width=True):
                            approve_expense_stage1(row['id'], st.session_state.full_name, 'Approved', remarks)
                            st.toast("✅ Expense has been approved successfully!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_s1_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage1(row['id'], st.session_state.full_name, 'Rejected', remarks)
                                st.toast("❌ Expense has been rejected successfully!", icon="❌")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals!")
    
    with tab2:
        st.subheader("My Approval History")
        
        approved_expenses = get_approved_expenses_by_user(st.session_state.full_name, 1)
        
        if not approved_expenses.empty:
            # Add overall status and category display
            approved_expenses['Overall_Status'] = approved_expenses.apply(get_overall_status, axis=1)
            approved_expenses['Category_Display'] = approved_expenses.apply(get_category_display, axis=1)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            total_approved = len(approved_expenses[approved_expenses['stage1_status'] == 'Approved'])
            total_rejected = len(approved_expenses[approved_expenses['stage1_status'] == 'Rejected'])
            amount_approved = approved_expenses[approved_expenses['stage1_status'] == 'Approved']['amount'].sum()
            
            col1.metric("✅ Approved", total_approved)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💰 Amount Approved", f"₹{amount_approved:,.2f}")
            col4.metric("📝 Total Reviewed", len(approved_expenses))
            
            st.markdown("---")
            
            # Display table
            for idx, row in approved_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**My Approval Details:**")
                    st.markdown(f"- **Decision:** {row['stage1_status']}")
                    st.markdown(f"- **Approved On:** {row['stage1_approved_date']}")
                    if row['stage1_remarks']:
                        st.markdown(f"- **My Remarks:** {row['stage1_remarks']}")
                    
                    st.markdown("---")
                    st.markdown(f"**Current Status:** {row['Overall_Status']}")
                    if row['stage1_status'] == 'Approved':
                        st.markdown(f"- Stage 2 Status: {row['stage2_status']}")
                        st.markdown(f"- Payment Status: {row['stage3_status']}")
        else:
            st.info("📌 You haven't approved or rejected any expenses yet.")

# Page 4: Approval Stage 2
elif "Approval Stage 2" in page_clean:
    st.header("✅ Approval Stage 2 - Senior Manager Review")
    
    tab1, tab2 = st.tabs(["⏳ Approval Pending", "✅ Approved/Rejected"])
    
    with tab1:
        st.subheader("Expenses Pending Your Approval")
        
        pending_expenses = get_expenses_for_approval(2)
        
        if not pending_expenses.empty:
            pending_expenses['Category_Display'] = pending_expenses.apply(get_category_display, axis=1)
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending approval")
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    # Show bill if available
                    if pd.notna(row.get('bill_filename')):
                        st.markdown("---")
                        st.markdown("### 📎 Attached Bill/Document")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.success(f"✅ **{row['bill_filename']}**")
                        with col2:
                            st.download_button(
                                label="📥 View Bill",
                                data=row['bill_document'],
                                file_name=row['bill_filename'],
                                mime=row['bill_filetype'],
                                key=f"s2_view_bill_{row['id']}"
                            )
                    else:
                        st.info("ℹ️ No bill attached")
                    
                    st.markdown("---")
                    st.markdown("**Stage 1 Approval:**")
                    st.markdown(f"- ✅ Approved by: {row['stage1_approved_by']}")
                    st.markdown(f"- 📅 Approved on: {row['stage1_approved_date']}")
                    if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                        st.markdown(f"- 💬 Remarks: {row['stage1_remarks']}")
                    
                    st.markdown("---")
                    remarks = st.text_area("💬 Remarks", key=f"remarks_s2_{row['id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_s2_{row['id']}", type="primary", use_container_width=True):
                            approve_expense_stage2(row['id'], st.session_state.full_name, 'Approved', remarks)
                            st.toast("✅ Expense has been approved successfully!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_s2_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage2(row['id'], st.session_state.full_name, 'Rejected', remarks)
                                st.toast("❌ Expense has been rejected successfully!", icon="❌")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals!")
    
    with tab2:
        st.subheader("My Approval History")
        
        approved_expenses = get_approved_expenses_by_user(st.session_state.full_name, 2)
        
        if not approved_expenses.empty:
            # Add overall status and category display
            approved_expenses['Overall_Status'] = approved_expenses.apply(get_overall_status, axis=1)
            approved_expenses['Category_Display'] = approved_expenses.apply(get_category_display, axis=1)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            total_approved = len(approved_expenses[approved_expenses['stage2_status'] == 'Approved'])
            total_rejected = len(approved_expenses[approved_expenses['stage2_status'] == 'Rejected'])
            amount_approved = approved_expenses[approved_expenses['stage2_status'] == 'Approved']['amount'].sum()
            
            col1.metric("✅ Approved", total_approved)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💰 Amount Approved", f"₹{amount_approved:,.2f}")
            col4.metric("📝 Total Reviewed", len(approved_expenses))
            
            st.markdown("---")
            
            # Display table
            for idx, row in approved_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**Stage 1 Approval:**")
                    st.markdown(f"- Approved by: {row['stage1_approved_by']}")
                    st.markdown(f"- Approved on: {row['stage1_approved_date']}")
                    
                    st.markdown("---")
                    st.markdown("**My Approval Details (Stage 2):**")
                    st.markdown(f"- **Decision:** {row['stage2_status']}")
                    st.markdown(f"- **Approved On:** {row['stage2_approved_date']}")
                    if row['stage2_remarks']:
                        st.markdown(f"- **My Remarks:** {row['stage2_remarks']}")
                    
                    st.markdown("---")
                    st.markdown(f"**Current Status:** {row['Overall_Status']}")
                    if row['stage2_status'] == 'Approved':
                        st.markdown(f"- Payment Status: {row['stage3_status']}")
        else:
            st.info("📌 You haven't approved or rejected any expenses yet.")

# Page 5: Approval Stage 3 (Payment)
elif "Approval Stage 3" in page_clean:
    st.header("💳 Approval Stage 3 - Accounts Payment Processing")
    
    tab1, tab2 = st.tabs(["⏳ Payment Pending", "✅ Paid/Rejected"])
    
    with tab1:
        st.subheader("Expenses Ready for Payment")
        
        pending_expenses = get_expenses_for_approval(3)
        
        if not pending_expenses.empty:
            pending_expenses['Category_Display'] = pending_expenses.apply(get_category_display, axis=1)
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) ready for payment")
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount to Pay", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    # Show bill if available
                    if pd.notna(row.get('bill_filename')):
                        st.markdown("---")
                        st.markdown("### 📎 Attached Bill/Document")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.success(f"✅ **{row['bill_filename']}**")
                        with col2:
                            st.download_button(
                                label="📥 View Bill",
                                data=row['bill_document'],
                                file_name=row['bill_filename'],
                                mime=row['bill_filetype'],
                                key=f"s3_view_bill_{row['id']}"
                            )
                    else:
                        st.info("ℹ️ No bill attached")
                    
                    st.markdown("---")
                    st.markdown("**✅ Approval Status:**")
                    st.markdown(f"- Stage 1: ✅ Approved by {row['stage1_approved_by']} on {row['stage1_approved_date']}")
                    st.markdown(f"- Stage 2: ✅ Approved by {row['stage2_approved_by']} on {row['stage2_approved_date']}")
                    
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        payment_mode = st.selectbox("💳 Payment Mode", PAYMENT_MODES, key=f"pm_{row['id']}")
                        transaction_ref = st.text_input("🔢 Transaction Reference/Cheque No.", key=f"tr_{row['id']}")
                    
                    with col2:
                        remarks = st.text_area("💬 Payment Remarks", key=f"remarks_s3_{row['id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💰 Mark as Paid", key=f"paid_{row['id']}", type="primary", use_container_width=True):
                            if transaction_ref:
                                approve_expense_stage3(row['id'], st.session_state.full_name, 'Paid', 
                                                     payment_mode, transaction_ref, remarks)
                                st.toast("✅ Expense has been paid successfully!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide transaction reference")
                    
                    with col2:
                        if st.button("❌ Reject Payment", key=f"reject_s3_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage3(row['id'], st.session_state.full_name, 'Rejected', 
                                                     None, None, remarks)
                                st.toast("❌ Payment has been rejected successfully!", icon="❌")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending payments!")
    
    with tab2:
        st.subheader("Payment History")
        
        payment_history = get_approved_expenses_by_user(st.session_state.full_name, 3)
        
        if not payment_history.empty:
            payment_history['Category_Display'] = payment_history.apply(get_category_display, axis=1)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            total_paid = len(payment_history[payment_history['stage3_status'] == 'Paid'])
            total_rejected = len(payment_history[payment_history['stage3_status'] == 'Rejected'])
            amount_paid = payment_history[payment_history['stage3_status'] == 'Paid']['amount'].sum()
            
            col1.metric("💰 Paid", total_paid)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💵 Total Amount Paid", f"₹{amount_paid:,.2f}")
            col4.metric("📝 Total Processed", len(payment_history))
            
            st.markdown("---")
            
            # Display table
            for idx, row in payment_history.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**Approval History:**")
                    st.markdown(f"- Stage 1: Approved by {row['stage1_approved_by']}")
                    st.markdown(f"- Stage 2: Approved by {row['stage2_approved_by']}")
                    
                    st.markdown("---")
                    st.markdown("**My Payment Details (Stage 3):**")
                    st.markdown(f"- **Status:** {row['stage3_status']}")
                    st.markdown(f"- **Processed On:** {row['stage3_paid_date']}")
                    if row['stage3_status'] == 'Paid':
                        st.markdown(f"- **Payment Mode:** {row['stage3_payment_mode']}")
                        st.markdown(f"- **Transaction Ref:** {row['stage3_transaction_ref']}")
                    if row['stage3_remarks']:
                        st.markdown(f"- **Remarks:** {row['stage3_remarks']}")
        else:
            st.info("📌 You haven't processed any payments yet.")

# Page 6: Dashboard
elif page_clean == "Dashboard":
    st.header("📊 Dashboard Overview")
    
    df = get_all_expenses()
    
    if not df.empty:
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        df['Category_Display'] = df.apply(get_category_display, axis=1)
        
        # Filters Section
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            # Brand filter
            all_brands = ["All"] + sorted(df['brand'].unique().tolist())
            selected_brand = st.selectbox("🏢 Brand", all_brands, key="dash_brand_filter")
        
        with col2:
            # Status filter
            status_options = ["All", "Stage 1 Pending", "Stage 2 Pending", "Payment Pending", "Paid", "Rejected"]
            selected_status = st.selectbox("📊 Status", status_options, key="dash_status_filter")
        
        with col3:
            # Category filter
            all_categories = ["All"] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox("📂 Category", all_categories, key="dash_category_filter")
        
        with col4:
            # Subcategory filter (based on selected category)
            if selected_category != "All":
                filtered_subcats = df[df['category'] == selected_category]['subcategory'].dropna().unique().tolist()
                all_subcategories = ["All"] + sorted(filtered_subcats) if filtered_subcats else ["All"]
            else:
                all_subcategories = ["All"] + sorted(df['subcategory'].dropna().unique().tolist())
            selected_subcategory = st.selectbox("📑 Subcategory", all_subcategories, key="dash_subcat_filter")
        
        with col5:
            # Date range filter
            date_filter = st.selectbox("📅 Date Range", ["All Time", "Custom Range"], key="dash_date_filter")
        
        # Date range picker (if custom selected)
        if date_filter == "Custom Range":
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("Start Date", value=pd.to_datetime(df['date'].min()), key="dash_start_date")
            with col_date2:
                end_date = st.date_input("End Date", value=pd.to_datetime(df['date'].max()), key="dash_end_date")
        
        st.markdown("---")
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_brand != "All":
            filtered_df = filtered_df[filtered_df['brand'] == selected_brand]
        
        if selected_status != "All":
            if selected_status == "Stage 1 Pending":
                filtered_df = filtered_df[filtered_df['stage1_status'] == 'Pending']
            elif selected_status == "Stage 2 Pending":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Approved') & 
                    (filtered_df['stage2_status'] == 'Pending')
                ]
            elif selected_status == "Payment Pending":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Approved') & 
                    (filtered_df['stage2_status'] == 'Approved') & 
                    (filtered_df['stage3_status'] == 'Pending')
                ]
            elif selected_status == "Paid":
                filtered_df = filtered_df[filtered_df['stage3_status'] == 'Paid']
            elif selected_status == "Rejected":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Rejected') | 
                    (filtered_df['stage2_status'] == 'Rejected') | 
                    (filtered_df['stage3_status'] == 'Rejected')
                ]
        
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        if selected_subcategory != "All":
            filtered_df = filtered_df[filtered_df['subcategory'] == selected_subcategory]
        
        if date_filter == "Custom Range":
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            filtered_df = filtered_df[
                (filtered_df['date'] >= pd.to_datetime(start_date)) & 
                (filtered_df['date'] <= pd.to_datetime(end_date))
            ]
        
        # Display metrics for filtered data
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Total Expenses", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("📝 Total Transactions", len(filtered_df))
        col3.metric("✅ Paid", len(filtered_df[filtered_df['stage3_status'] == 'Paid']))
        col4.metric("⏳ Pending", len(filtered_df[filtered_df['stage3_status'] == 'Pending']))
        
        st.markdown("---")
        
        if not filtered_df.empty:
            # Charts in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                # Brand summary chart
                brand_summary = filtered_df.groupby('brand')['amount'].sum().reset_index()
                brand_summary = brand_summary.nlargest(10, 'amount')
                
                fig = px.bar(brand_summary, x='brand', y='amount', 
                            title='Top 10 Brands by Expense',
                            labels={'amount': 'Amount (₹)', 'brand': 'Brand'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Category summary chart
                category_summary = filtered_df.groupby('category')['amount'].sum().reset_index()
                category_summary = category_summary.nlargest(10, 'amount')
                
                fig = px.pie(category_summary, values='amount', names='category',
                            title='Expense Distribution by Category')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📌 No expenses match the selected filters.")
    else:
        st.info("📌 No expenses recorded yet.")

# Page 7: View All Expenses
elif page_clean == "View All Expenses":
    st.header("📋 All Expenses")
    
    df = get_all_expenses()
    
    if not df.empty:
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        df['Category_Display'] = df.apply(get_category_display, axis=1)
        
        # Filters Section
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            # Brand filter
            all_brands = ["All"] + sorted(df['brand'].unique().tolist())
            selected_brand = st.selectbox("🏢 Brand", all_brands, key="view_brand_filter")
        
        with col2:
            # Status filter
            status_options = ["All", "Stage 1 Pending", "Stage 2 Pending", "Payment Pending", "Paid", "Rejected"]
            selected_status = st.selectbox("📊 Status", status_options, key="view_status_filter")
        
        with col3:
            # Category filter
            all_categories = ["All"] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox("📂 Category", all_categories, key="view_category_filter")
        
        with col4:
            # Subcategory filter (based on selected category)
            if selected_category != "All":
                filtered_subcats = df[df['category'] == selected_category]['subcategory'].dropna().unique().tolist()
                all_subcategories = ["All"] + sorted(filtered_subcats) if filtered_subcats else ["All"]
            else:
                all_subcategories = ["All"] + sorted(df['subcategory'].dropna().unique().tolist())
            selected_subcategory = st.selectbox("📑 Subcategory", all_subcategories, key="view_subcat_filter")
        
        with col5:
            # Date range filter
            date_filter = st.selectbox("📅 Date Range", ["All Time", "Custom Range"], key="view_date_filter")
        
        # Date range picker (if custom selected)
        if date_filter == "Custom Range":
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("Start Date", value=pd.to_datetime(df['date'].min()), key="view_start_date")
            with col_date2:
                end_date = st.date_input("End Date", value=pd.to_datetime(df['date'].max()), key="view_end_date")
        
        st.markdown("---")
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_brand != "All":
            filtered_df = filtered_df[filtered_df['brand'] == selected_brand]
        
        if selected_status != "All":
            if selected_status == "Stage 1 Pending":
                filtered_df = filtered_df[filtered_df['stage1_status'] == 'Pending']
            elif selected_status == "Stage 2 Pending":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Approved') & 
                    (filtered_df['stage2_status'] == 'Pending')
                ]
            elif selected_status == "Payment Pending":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Approved') & 
                    (filtered_df['stage2_status'] == 'Approved') & 
                    (filtered_df['stage3_status'] == 'Pending')
                ]
            elif selected_status == "Paid":
                filtered_df = filtered_df[filtered_df['stage3_status'] == 'Paid']
            elif selected_status == "Rejected":
                filtered_df = filtered_df[
                    (filtered_df['stage1_status'] == 'Rejected') | 
                    (filtered_df['stage2_status'] == 'Rejected') | 
                    (filtered_df['stage3_status'] == 'Rejected')
                ]
        
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        if selected_subcategory != "All":
            filtered_df = filtered_df[filtered_df['subcategory'] == selected_subcategory]
        
        if date_filter == "Custom Range":
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            filtered_df = filtered_df[
                (filtered_df['date'] >= pd.to_datetime(start_date)) & 
                (filtered_df['date'] <= pd.to_datetime(end_date))
            ]
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Total", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("📝 Count", len(filtered_df))
        col3.metric("✅ Paid", len(filtered_df[filtered_df['stage3_status'] == 'Paid']))
        col4.metric("📎 With Bills", len(filtered_df[filtered_df['bill_filename'].notna()]))
        
        st.markdown("---")
        
        if not filtered_df.empty:
            # Expandable view for each expense
            st.subheader("📋 Detailed Expense Records")
            
            for idx, row in filtered_df.iterrows():
                has_bill = pd.notna(row.get('bill_filename'))
                bill_icon = "📎" if has_bill else "📄"
                
                with st.expander(f"{bill_icon} ID: {row['id']} | {row['brand']} | {row['Category_Display']} | ₹{row['amount']:,.2f} | {row['Overall_Status']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['Category_Display'])
                    col4.metric("📊 Status", row['Overall_Status'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    st.markdown(f"**🕐 Submitted On:** {row['created_at']}")
                    
                    if pd.notna(row.get('stage1_assigned_to')):
                        st.markdown(f"**👨‍💼 Assigned To:** {row['stage1_assigned_to']}")
                    
                    st.markdown("---")
                    
                    # Bill/Document Section
                    st.markdown("### 📎 Bill/Document")
                    
                    if has_bill:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.success(f"✅ Document uploaded: **{row['bill_filename']}**")
                        with col2:
                            if st.download_button(
                                label="📥 Download Bill",
                                data=row['bill_document'],
                                file_name=row['bill_filename'],
                                mime=row['bill_filetype'],
                                key=f"download_bill_{row['id']}"
                            ):
                                st.success("Downloaded!")
                    else:
                        st.info("ℹ️ No bill/document uploaded yet")
                    
                    # Allow uploading bill if not present or updating
                    st.markdown("**Upload/Update Bill:**")
                    uploaded_bill = st.file_uploader(
                        "Upload Bill/Document (PDF or Image)", 
                        type=['pdf', 'png', 'jpg', 'jpeg'],
                        key=f"upload_bill_{row['id']}"
                    )
                    
                    if uploaded_bill is not None:
                        if st.button(f"💾 Save Bill", key=f"save_bill_{row['id']}", type="primary"):
                            bill_data = uploaded_bill.read()
                            update_expense_bill(row['id'], bill_data, uploaded_bill.name, uploaded_bill.type)
                            st.toast("✅ Bill has been uploaded successfully!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # Approval Status
                    st.markdown("### 📋 Approval Status")
                    status_col1, status_col2, status_col3 = st.columns(3)
                    
                    with status_col1:
                        st.markdown("**Stage 1: Brand Head**")
                        if row['stage1_status'] == 'Approved':
                            st.success("✅ Approved")
                            st.caption(f"By: {row['stage1_approved_by']}")
                        elif row['stage1_status'] == 'Rejected':
                            st.error("❌ Rejected")
                            st.caption(f"By: {row['stage1_approved_by']}")
                        else:
                            st.warning("⏳ Pending")
                    
                    with status_col2:
                        st.markdown("**Stage 2: Senior Manager**")
                        if row['stage2_status'] == 'Approved':
                            st.success("✅ Approved")
                            st.caption(f"By: {row['stage2_approved_by']}")
                        elif row['stage2_status'] == 'Rejected':
                            st.error("❌ Rejected")
                            st.caption(f"By: {row['stage2_approved_by']}")
                        else:
                            st.warning("⏳ Pending")
                    
                    with status_col3:
                        st.markdown("**Stage 3: Accounts**")
                        if row['stage3_status'] == 'Paid':
                            st.success("✅ Paid")
                            st.caption(f"By: {row['stage3_paid_by']}")
                            if pd.notna(row.get('stage3_payment_mode')):
                                st.caption(f"Mode: {row['stage3_payment_mode']}")
                        elif row['stage3_status'] == 'Rejected':
                            st.error("❌ Rejected")
                            st.caption(f"By: {row['stage3_paid_by']}")
                        else:
                            st.warning("⏳ Pending")
            
            st.markdown("---")
            st.subheader("📊 Summary Table")
            
            display_df = filtered_df[[
                'id', 'date', 'brand', 'Category_Display', 'amount', 'description',
                'stage1_status', 'stage2_status', 'stage3_status', 'Overall_Status'
            ]].copy()
            
            # Add bill status column
            display_df['has_bill'] = filtered_df['bill_filename'].notna().apply(lambda x: '✅' if x else '❌')
            
            # Add assigned_to column if it exists
            if 'stage1_assigned_to' in filtered_df.columns:
                display_df.insert(6, 'assigned_to', filtered_df['stage1_assigned_to'])
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            excel_data = to_excel(filtered_df)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("📌 No expenses match the selected filters.")
    else:
        st.info("📌 No expenses recorded yet.")

# Page 8: User Management (Admin Only)
elif page_clean == "User Management":
    st.header("👥 User Management (Admin Only)")
    
    tab1, tab2 = st.tabs(["➕ Create New User", "📋 Manage Users"])
    
    with tab1:
        st.subheader("Create New User Account")
        
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username *", placeholder="e.g., john.doe")
                new_full_name = st.text_input("Full Name *", placeholder="e.g., John Doe")
            
            with col2:
                new_password = st.text_input("Password *", type="password", placeholder="Min 6 characters")
                new_role = st.selectbox("Role *", options=list(USER_ROLES.keys()), 
                                       format_func=lambda x: USER_ROLES[x]["title"])
            
            submitted = st.form_submit_button("✅ Create User", type="primary")
            
            if submitted:
                if new_username and new_password and new_full_name:
                    if len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters!")
                    else:
                        success, message = create_user(
                            new_username.lower().strip(),
                            new_password,
                            new_full_name,
                            new_role,
                            st.session_state.username
                        )
                        if success:
                            st.toast(f"✅ {message}", icon="✅")
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.error("❌ Please fill all fields!")
    
    with tab2:
        st.subheader("Existing Users")
        
        users_df = get_all_users()
        
        if not users_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👥 Total Users", len(users_df))
            col2.metric("✅ Active", len(users_df[users_df['is_active'] == 1]))
            col3.metric("❌ Inactive", len(users_df[users_df['is_active'] == 0]))
            col4.metric("🔐 Admins", len(users_df[users_df['role'] == 'admin']))
            
            st.markdown("---")
            
            for idx, user in users_df.iterrows():
                status_icon = '✅' if user['is_active'] else '❌'
                with st.expander(f"{status_icon} {user['full_name']} (@{user['username']}) - {USER_ROLES[user['role']]['title']}"):
                    col1, col2 = st.columns(2)
                    
                    col1.markdown(f"**Username:** {user['username']}")
                    col1.markdown(f"**Full Name:** {user['full_name']}")
                    col1.markdown(f"**Role:** {USER_ROLES[user['role']]['title']}")
                    
                    col2.markdown(f"**Status:** {'Active ✅' if user['is_active'] else 'Inactive ❌'}")
                    col2.markdown(f"**Created:** {user['created_at']}")
                    col2.markdown(f"**Created By:** {user['created_by']}")
                    
                    st.markdown("---")
                    st.markdown("**Actions:**")
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    # Toggle Active/Inactive
                    with col_a:
                        if user['username'] != 'admin':
                            if user['is_active']:
                                if st.button("⏸️ Deactivate", key=f"deact_{user['id']}", use_container_width=True):
                                    update_user_status(user['id'], 0)
                                    st.success("User deactivated!")
                                    st.rerun()
                            else:
                                if st.button("▶️ Activate", key=f"act_{user['id']}", use_container_width=True):
                                    update_user_status(user['id'], 1)
                                    st.success("User activated!")
                                    st.rerun()
                    
                    # Reset Password
                    with col_b:
                        if st.button("🔑 Reset Password", key=f"reset_{user['id']}", use_container_width=True):
                            st.session_state[f'show_reset_{user["id"]}'] = True
                    
                    # Delete User
                    with col_c:
                        if user['username'] != 'admin':
                            if st.button("🗑️ Delete", key=f"del_{user['id']}", use_container_width=True):
                                st.session_state[f'confirm_delete_{user["id"]}'] = True
                    
                    # Reset Password Form
                    if st.session_state.get(f'show_reset_{user["id"]}', False):
                        with st.form(f"reset_form_{user['id']}"):
                            new_pwd = st.text_input("New Password", type="password", key=f"new_pwd_{user['id']}")
                            col_x, col_y = st.columns(2)
                            with col_x:
                                if st.form_submit_button("✅ Reset", use_container_width=True):
                                    if len(new_pwd) >= 6:
                                        reset_user_password(user['id'], new_pwd)
                                        st.success("Password reset successfully!")
                                        st.session_state[f'show_reset_{user["id"]}'] = False
                                        st.rerun()
                                    else:
                                        st.error("Password must be at least 6 characters!")
                            with col_y:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f'show_reset_{user["id"]}'] = False
                                    st.rerun()
                    
                    # Delete Confirmation
                    if st.session_state.get(f'confirm_delete_{user["id"]}', False):
                        st.warning(f"⚠️ Are you sure you want to delete user '{user['username']}'?")
                        col_x, col_y = st.columns(2)
                        with col_x:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{user['id']}", type="primary"):
                                delete_user(user['id'])
                                st.success("User deleted successfully!")
                                st.session_state[f'confirm_delete_{user["id"]}'] = False
                                st.rerun()
                        with col_y:
                            if st.button("❌ Cancel", key=f"confirm_no_{user['id']}"):
                                st.session_state[f'confirm_delete_{user["id"]}'] = False
                                st.rerun()
        else:
            st.info("No users found.")

# Page 9: Change Password
elif page_clean == "Change Password":
    st.header("🔐 Change Password")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"### Change password for: **{st.session_state.full_name}**")
        st.markdown("---")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password", placeholder="Enter your current password")
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)")
            confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
            
            submitted = st.form_submit_button("🔄 Change Password", use_container_width=True, type="primary")
            
            if submitted:
                if not current_password or not new_password or not confirm_password:
                    st.error("❌ Please fill all fields!")
                elif len(new_password) < 6:
                    st.error("❌ New password must be at least 6 characters long!")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match!")
                else:
                    success, message = change_password(st.session_state.username, current_password, new_password)
                    if success:
                        st.toast(f"✅ {message}", icon="✅")
                    else:
                        st.error(f"❌ {message}")
