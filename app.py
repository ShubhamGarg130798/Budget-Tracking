import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
import plotly.express as px
import plotly.graph_objects as go
import hashlib

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    /* Main styling */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    /* Card styling */
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .status-approved {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-rejected {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    .status-paid {
        background-color: #d1ecf1;
        color: #0c5460;
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
    }
    
    section[data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #e0e0e0;
    }
    
    /* Form styling */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 2px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# USER ROLES
USER_ROLES = {
    "hr": {
        "stage": 0,
        "title": "HR - Brand Staff",
        "icon": "👤"
    },
    "brand_heads": {
        "stage": 1,
        "title": "Brand Head",
        "icon": "👨‍💼"
    },
    "stage2_approver": {
        "stage": 2,
        "title": "Senior Manager",
        "icon": "👔"
    },
    "accounts_team": {
        "stage": 3,
        "title": "Accounts Team",
        "icon": "💼"
    },
    "admin": {
        "stage": 99,
        "title": "Administrator",
        "icon": "🔐"
    }
}

# Brand list
BRANDS = [
    "FundoBaBa", "Salary Adda", "FastPaise", "SnapPaisa", "Salary 4 Sure",
    "Duniya Finance", "Tejas", "BlinkR", "Salary Setu", "Qua Loans",
    "Paisa Pop", "Salary 4 You", "Rupee Hype", "Minutes Loan", "Squid Loan",
    "Zepto", "Paisa on Salary", "Jhatpat"
]

# Expense categories
CATEGORIES = [
    "Marketing", "Operations", "Salaries", "Technology", "Office Rent",
    "Utilities", "Travel", "Professional Fees", "Commission", "Interest",
    "Petty Cash", "Other"
]

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
            amount REAL NOT NULL,
            description TEXT,
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
    
    # Check if stage1_assigned_to column exists, add if not
    c.execute("PRAGMA table_info(expenses)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'stage1_assigned_to' not in columns:
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN stage1_assigned_to TEXT")
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
def add_expense(date, brand, category, amount, description, added_by, assigned_to=None):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO expenses (date, brand, category, amount, description, added_by, stage1_assigned_to)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (date, brand, category, amount, description, added_by, assigned_to))
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

def change_password(username, old_password, new_password):
    """Change user's own password"""
    old_hashed = hashlib.sha256(old_password.encode()).hexdigest()
    new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
    
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, old_hashed))
    if not c.fetchone():
        conn.close()
        return False, "Current password is incorrect"
    
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
    if row['stage1_status'] == 'Approved':
        s1 = "Brand Head: ✅ Approved"
    elif row['stage1_status'] == 'Rejected':
        s1 = "Brand Head: ❌ Rejected"
    else:
        s1 = "Brand Head: ⏳ Pending"
    
    if row['stage2_status'] == 'Approved':
        s2 = "Senior Manager: ✅ Approved"
    elif row['stage2_status'] == 'Rejected':
        s2 = "Senior Manager: ❌ Rejected"
    else:
        s2 = "Senior Manager: ⏳ Pending"
    
    if row['stage3_status'] == 'Paid':
        s3 = "Accounts: ✅ Paid"
    elif row['stage3_status'] == 'Rejected':
        s3 = "Accounts: ❌ Rejected"
    else:
        s3 = "Accounts: ⏳ Pending"
    
    return f"{s1} | {s2} | {s3}"

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
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="main-header">
            <h1>💰 Brand Expense Tracker</h1>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">Multi-Stage Approval System</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Login card
        with st.container():
            st.markdown("### 🔐 Sign In")
            st.markdown("Please enter your credentials to continue")
            
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if username and password:
                    user_data = authenticate_user(username, password)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.username = user_data[0]
                        st.session_state.full_name = user_data[1]
                        st.session_state.user_role = user_data[2]
                        st.success(f"✅ Welcome back, {user_data[1]}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Please try again.")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **Default Admin Login:** Username: `admin` | Password: `admin123`")
    
    st.stop()

# Main App (After Login)
# Header
st.markdown("""
<div class="main-header">
    <h1>💰 Brand Expense Tracker</h1>
    <p style="margin: 0.5rem 0 0 0; font-size: 1rem;">Streamlined Multi-Stage Approval Workflow</p>
</div>
""", unsafe_allow_html=True)

# User info bar
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    role_info = USER_ROLES[st.session_state.user_role]
    st.markdown(f"""
    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <strong>{role_info['icon']} {st.session_state.full_name}</strong><br>
        <span style="color: #666; font-size: 0.9rem;">{role_info['title']}</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <strong>📅 {datetime.now().strftime('%B %d, %Y')}</strong><br>
        <span style="color: #666; font-size: 0.9rem;">{datetime.now().strftime('%I:%M %p')}</span>
    </div>
    """, unsafe_allow_html=True)

with col3:
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.full_name = None
        st.session_state.user_role = None
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 📋 Navigation")
    
    page_options = ["➕ Add Expense"]
    
    if st.session_state.user_role == "hr":
        page_options.extend(["📝 My Expenses", "🔐 Change Password"])
    else:
        if st.session_state.user_role in ["brand_heads", "admin"]:
            page_options.append("✅ Stage 1 Approval")
        
        if st.session_state.user_role in ["stage2_approver", "admin"]:
            page_options.append("✅ Stage 2 Approval")
        
        if st.session_state.user_role in ["accounts_team", "admin"]:
            page_options.append("💳 Stage 3 Payment")
        
        page_options.extend(["📊 Dashboard", "📋 All Expenses", "🔐 Change Password"])
    
    if st.session_state.user_role == "admin":
        page_options.append("👥 User Management")
    
    page = st.selectbox("Select Page", page_options, label_visibility="collapsed")

# Remove emoji from page name
page_clean = page.split(" ", 1)[1] if " " in page else page

# Page 1: Add Expense
if page_clean == "Add Expense":
    st.markdown("### ➕ Add New Expense")
    
    with st.container():
        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username *", placeholder="e.g., john.doe")
                new_full_name = st.text_input("Full Name *", placeholder="e.g., John Doe")
            
            with col2:
                new_password = st.text_input("Password *", type="password", placeholder="Min 6 characters")
                new_role = st.selectbox("Role *", options=list(USER_ROLES.keys()), 
                                       format_func=lambda x: f"{USER_ROLES[x]['icon']} {USER_ROLES[x]['title']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                submitted = st.form_submit_button("✅ Create User", type="primary", use_container_width=True)
            
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
                            st.success(f"✅ {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.error("❌ Please fill all required fields!")
    
    with tab2:
        st.markdown("#### Existing Users")
        
        users_df = get_all_users()
        
        if not users_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👥 Total Users", len(users_df))
            col2.metric("✅ Active", len(users_df[users_df['is_active'] == 1]))
            col3.metric("❌ Inactive", len(users_df[users_df['is_active'] == 0]))
            col4.metric("🔐 Admins", len(users_df[users_df['role'] == 'admin']))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, user in users_df.iterrows():
                status_icon = '✅' if user['is_active'] else '❌'
                role_icon = USER_ROLES[user['role']]['icon']
                
                with st.expander(f"{status_icon} {role_icon} **{user['full_name']}** (@{user['username']}) - {USER_ROLES[user['role']]['title']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Username:** {user['username']}")
                        st.markdown(f"**Full Name:** {user['full_name']}")
                        st.markdown(f"**Role:** {USER_ROLES[user['role']]['title']}")
                    
                    with col2:
                        st.markdown(f"**Status:** {'Active ✅' if user['is_active'] else 'Inactive ❌'}")
                        st.markdown(f"**Created:** {user['created_at']}")
                        st.markdown(f"**Created By:** {user['created_by']}")
                    
                    st.markdown("---")
                    st.markdown("**Actions:**")
                    
                    col_a, col_b, col_c = st.columns(3)
                    
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
                    
                    with col_b:
                        if st.button("🔑 Reset Password", key=f"reset_{user['id']}", use_container_width=True):
                            st.session_state[f'show_reset_{user["id"]}'] = True
                    
                    with col_c:
                        if user['username'] != 'admin':
                            if st.button("🗑️ Delete", key=f"del_{user['id']}", use_container_width=True):
                                st.session_state[f'confirm_delete_{user["id"]}'] = True
                    
                    if st.session_state.get(f'show_reset_{user["id"]}', False):
                        st.markdown("---")
                        with st.form(f"reset_form_{user['id']}"):
                            new_pwd = st.text_input("New Password", type="password", key=f"new_pwd_{user['id']}", 
                                                   placeholder="Min 6 characters")
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
                    
                    if st.session_state.get(f'confirm_delete_{user["id"]}', False):
                        st.markdown("---")
                        st.warning(f"⚠️ Are you sure you want to delete user **'{user['username']}'**?")
                        col_x, col_y = st.columns(2)
                        with col_x:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{user['id']}", type="primary", use_container_width=True):
                                delete_user(user['id'])
                                st.success("User deleted successfully!")
                                st.session_state[f'confirm_delete_{user["id"]}'] = False
                                st.rerun()
                        with col_y:
                            if st.button("❌ Cancel", key=f"confirm_no_{user['id']}", use_container_width=True):
                                st.session_state[f'confirm_delete_{user["id"]}'] = False
                                st.rerun()
        else:
            st.info("No users found.")

# Page 9: Change Password
elif page_clean == "Change Password":
    st.markdown("### 🔐 Change Password")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"#### Change password for: **{st.session_state.full_name}**")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password", 
                                           placeholder="Enter your current password")
            new_password = st.text_input("New Password", type="password", 
                                        placeholder="Enter new password (min 6 characters)")
            confirm_password = st.text_input("Confirm New Password", type="password", 
                                            placeholder="Re-enter new password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
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
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")

# Footer
# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown('<div style="text-align: center; color: #666; font-size: 0.9rem;"><strong>Brand Expense Tracker v2.0</strong> | Multi-Stage Approval System<br>HR Entry - Brand Head Approval - Senior Manager Approval - Accounts Payment</div>', unsafe_allow_html=True) col1:
                expense_date = st.date_input("📅 Expense Date", value=date.today())
                brand = st.selectbox("🏢 Brand", BRANDS)
                category = st.selectbox("📂 Category", CATEGORIES)
            
            with col2:
                amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
                added_by = st.text_input("👤 Submitted By", value=st.session_state.full_name, disabled=True)
                
                # Get brand heads for assignment
                brand_heads = get_brand_heads()
                if brand_heads:
                    brand_head_options = {bh[1]: bh[1] for bh in brand_heads}
                    assigned_to = st.selectbox("👨‍💼 Assign to Brand Head *", options=list(brand_head_options.keys()))
                else:
                    st.warning("⚠️ No Brand Heads available. Please contact admin.")
                    assigned_to = None
            
            description = st.text_area("📝 Description", placeholder="Enter detailed expense description...", height=100)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                submitted = st.form_submit_button("✅ Submit Expense", use_container_width=True, type="primary")
            with col2:
                st.form_submit_button("🔄 Clear", use_container_width=True)
            
            if submitted:
                if amount > 0 and added_by and assigned_to:
                    add_expense(expense_date, brand, category, amount, description, added_by, assigned_to)
                    st.success(f"🎉 Expense submitted successfully and assigned to **{assigned_to}**!")
                    st.balloons()
                else:
                    st.error("⚠️ Please fill all required fields!")

# Page 2: My Expenses (HR View)
elif page_clean == "My Expenses":
    st.markdown("### 📝 My Submitted Expenses")
    
    my_expenses = get_expenses_by_user(st.session_state.full_name)
    
    if not my_expenses.empty:
        my_expenses['Overall_Status'] = my_expenses.apply(get_overall_status, axis=1)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Amount", f"₹{my_expenses['amount'].sum():,.2f}")
        col2.metric("📝 Total Expenses", len(my_expenses))
        col3.metric("⏳ Pending", len(my_expenses[my_expenses['stage1_status'] == 'Pending']))
        col4.metric("✅ Paid", len(my_expenses[my_expenses['stage3_status'] == 'Paid']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display expenses
        for idx, row in my_expenses.iterrows():
            status_display = get_stage_status_display(row)
            
            with st.expander(f"**ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                with col2:
                    st.metric("🏢 Brand", row['brand'])
                with col3:
                    st.metric("📂 Category", row['category'])
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                with col2:
                    st.markdown(f"**🕐 Submitted On:** {row['created_at']}")
                    if pd.notna(row.get('stage1_assigned_to')):
                        st.markdown(f"**👨‍💼 Assigned To:** {row['stage1_assigned_to']}")
                
                st.markdown("---")
                
                # Stage details in tabs
                tab1, tab2, tab3 = st.tabs(["📋 Stage 1: Brand Head", "📋 Stage 2: Senior Manager", "📋 Stage 3: Accounts"])
                
                with tab1:
                    if row['stage1_status'] == 'Pending':
                        st.info("⏳ **Status:** Pending Approval")
                    elif row['stage1_status'] == 'Approved':
                        st.success("✅ **Status:** Approved")
                        st.markdown(f"**Approved By:** {row['stage1_approved_by']}")
                        st.markdown(f"**Date:** {row['stage1_approved_date']}")
                        if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage1_remarks']}")
                    elif row['stage1_status'] == 'Rejected':
                        st.error("❌ **Status:** Rejected")
                        st.markdown(f"**Rejected By:** {row['stage1_approved_by']}")
                        st.markdown(f"**Date:** {row['stage1_approved_date']}")
                        if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage1_remarks']}")
                
                with tab2:
                    if row['stage1_status'] != 'Approved':
                        st.warning("⏸️ Awaiting Stage 1 Approval")
                    elif row['stage2_status'] == 'Pending':
                        st.info("⏳ **Status:** Pending Approval")
                    elif row['stage2_status'] == 'Approved':
                        st.success("✅ **Status:** Approved")
                        st.markdown(f"**Approved By:** {row['stage2_approved_by']}")
                        st.markdown(f"**Date:** {row['stage2_approved_date']}")
                        if pd.notna(row.get('stage2_remarks')) and row['stage2_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage2_remarks']}")
                    elif row['stage2_status'] == 'Rejected':
                        st.error("❌ **Status:** Rejected")
                        st.markdown(f"**Rejected By:** {row['stage2_approved_by']}")
                        st.markdown(f"**Date:** {row['stage2_approved_date']}")
                        if pd.notna(row.get('stage2_remarks')) and row['stage2_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage2_remarks']}")
                
                with tab3:
                    if row['stage1_status'] != 'Approved' or row['stage2_status'] != 'Approved':
                        st.warning("⏸️ Awaiting Previous Stage Approvals")
                    elif row['stage3_status'] == 'Pending':
                        st.info("⏳ **Status:** Payment Pending")
                    elif row['stage3_status'] == 'Paid':
                        st.success("✅ **Status:** Paid")
                        st.markdown(f"**Paid By:** {row['stage3_paid_by']}")
                        st.markdown(f"**Date:** {row['stage3_paid_date']}")
                        if pd.notna(row.get('stage3_payment_mode')):
                            st.markdown(f"**💳 Payment Mode:** {row['stage3_payment_mode']}")
                        if pd.notna(row.get('stage3_transaction_ref')):
                            st.markdown(f"**🔢 Transaction Ref:** {row['stage3_transaction_ref']}")
                        if pd.notna(row.get('stage3_remarks')) and row['stage3_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage3_remarks']}")
                    elif row['stage3_status'] == 'Rejected':
                        st.error("❌ **Status:** Payment Rejected")
                        st.markdown(f"**Rejected By:** {row['stage3_paid_by']}")
                        st.markdown(f"**Date:** {row['stage3_paid_date']}")
                        if pd.notna(row.get('stage3_remarks')) and row['stage3_remarks']:
                            st.markdown(f"**💬 Remarks:** {row['stage3_remarks']}")
    else:
        st.info("📌 You haven't submitted any expenses yet.")

# Page 3: Approval Stage 1
elif "Stage 1 Approval" in page_clean:
    st.markdown("### ✅ Stage 1: Brand Head Approval")
    
    tab1, tab2 = st.tabs(["⏳ Pending Approval", "📜 Approval History"])
    
    with tab1:
        if st.session_state.user_role == "brand_heads":
            pending_expenses = get_expenses_for_approval(1, st.session_state.full_name)
        else:
            pending_expenses = get_expenses_for_approval(1)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending your approval")
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"**ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**📝 Description:** {row['description']}")
                        st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    with col2:
                        if pd.notna(row.get('stage1_assigned_to')):
                            st.markdown(f"**👨‍💼 Assigned To:** {row['stage1_assigned_to']}")
                        st.markdown(f"**📅 Submitted On:** {row['created_at']}")
                    
                    st.markdown("---")
                    st.markdown("**📝 Your Decision**")
                    
                    remarks = st.text_area("💬 Remarks (Optional for Approval, Required for Rejection)", 
                                         key=f"remarks_s1_{row['id']}", 
                                         placeholder="Enter your comments here...",
                                         height=80)
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("✅ Approve", key=f"approve_s1_{row['id']}", type="primary", use_container_width=True):
                            approve_expense_stage1(row['id'], st.session_state.full_name, 'Approved', remarks)
                            st.success("✅ Expense Approved!")
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_s1_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage1(row['id'], st.session_state.full_name, 'Rejected', remarks)
                                st.error("❌ Expense Rejected!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals!")
    
    with tab2:
        approved_expenses = get_approved_expenses_by_user(st.session_state.full_name, 1)
        
        if not approved_expenses.empty:
            approved_expenses['Overall_Status'] = approved_expenses.apply(get_overall_status, axis=1)
            
            col1, col2, col3, col4 = st.columns(4)
            total_approved = len(approved_expenses[approved_expenses['stage1_status'] == 'Approved'])
            total_rejected = len(approved_expenses[approved_expenses['stage1_status'] == 'Rejected'])
            amount_approved = approved_expenses[approved_expenses['stage1_status'] == 'Approved']['amount'].sum()
            
            col1.metric("✅ Approved", total_approved)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💰 Amount Approved", f"₹{amount_approved:,.2f}")
            col4.metric("📝 Total Reviewed", len(approved_expenses))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in approved_expenses.iterrows():
                status_display = get_stage_status_display(row)
                status_icon = "✅" if row['stage1_status'] == 'Approved' else "❌"
                
                with st.expander(f"{status_icon} **ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**Your Approval Details:**")
                    if row['stage1_status'] == 'Approved':
                        st.success(f"✅ **Approved** on {row['stage1_approved_date']}")
                    else:
                        st.error(f"❌ **Rejected** on {row['stage1_approved_date']}")
                    
                    if row['stage1_remarks']:
                        st.markdown(f"**💬 Your Remarks:** {row['stage1_remarks']}")
                    
                    st.markdown("---")
                    st.markdown(f"**📊 Current Status:** {row['Overall_Status']}")
        else:
            st.info("📌 You haven't approved or rejected any expenses yet.")

# Page 4: Approval Stage 2
elif "Stage 2 Approval" in page_clean:
    st.markdown("### ✅ Stage 2: Senior Manager Approval")
    
    tab1, tab2 = st.tabs(["⏳ Pending Approval", "📜 Approval History"])
    
    with tab1:
        pending_expenses = get_expenses_for_approval(2)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending your approval")
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"**ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**📝 Description:** {row['description']}")
                        st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                        st.markdown(f"**📅 Expense Date:** {row['date']}")
                    with col2:
                        st.markdown("**Stage 1 Approval:**")
                        st.success(f"✅ Approved by {row['stage1_approved_by']}")
                        st.markdown(f"📅 {row['stage1_approved_date']}")
                        if pd.notna(row.get('stage1_remarks')) and row['stage1_remarks']:
                            st.markdown(f"💬 {row['stage1_remarks']}")
                    
                    st.markdown("---")
                    st.markdown("**📝 Your Decision**")
                    
                    remarks = st.text_area("💬 Remarks (Optional for Approval, Required for Rejection)", 
                                         key=f"remarks_s2_{row['id']}", 
                                         placeholder="Enter your comments here...",
                                         height=80)
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("✅ Approve", key=f"approve_s2_{row['id']}", type="primary", use_container_width=True):
                            approve_expense_stage2(row['id'], st.session_state.full_name, 'Approved', remarks)
                            st.success("✅ Expense Approved!")
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_s2_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage2(row['id'], st.session_state.full_name, 'Rejected', remarks)
                                st.error("❌ Expense Rejected!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals!")
    
    with tab2:
        approved_expenses = get_approved_expenses_by_user(st.session_state.full_name, 2)
        
        if not approved_expenses.empty:
            approved_expenses['Overall_Status'] = approved_expenses.apply(get_overall_status, axis=1)
            
            col1, col2, col3, col4 = st.columns(4)
            total_approved = len(approved_expenses[approved_expenses['stage2_status'] == 'Approved'])
            total_rejected = len(approved_expenses[approved_expenses['stage2_status'] == 'Rejected'])
            amount_approved = approved_expenses[approved_expenses['stage2_status'] == 'Approved']['amount'].sum()
            
            col1.metric("✅ Approved", total_approved)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💰 Amount Approved", f"₹{amount_approved:,.2f}")
            col4.metric("📝 Total Reviewed", len(approved_expenses))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in approved_expenses.iterrows():
                status_display = get_stage_status_display(row)
                status_icon = "✅" if row['stage2_status'] == 'Approved' else "❌"
                
                with st.expander(f"{status_icon} **ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**Your Approval Details:**")
                    if row['stage2_status'] == 'Approved':
                        st.success(f"✅ **Approved** on {row['stage2_approved_date']}")
                    else:
                        st.error(f"❌ **Rejected** on {row['stage2_approved_date']}")
                    
                    if row['stage2_remarks']:
                        st.markdown(f"**💬 Your Remarks:** {row['stage2_remarks']}")
                    
                    st.markdown("---")
                    st.markdown(f"**📊 Current Status:** {row['Overall_Status']}")
        else:
            st.info("📌 You haven't approved or rejected any expenses yet.")

# Page 5: Approval Stage 3 (Payment)
elif "Stage 3 Payment" in page_clean:
    st.markdown("### 💳 Stage 3: Accounts Payment Processing")
    
    tab1, tab2 = st.tabs(["⏳ Payment Pending", "📜 Payment History"])
    
    with tab1:
        pending_expenses = get_expenses_for_approval(3)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) ready for payment")
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in pending_expenses.iterrows():
                status_display = get_stage_status_display(row)
                
                with st.expander(f"**ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount to Pay", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**📝 Description:** {row['description']}")
                        st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                        st.markdown(f"**📅 Expense Date:** {row['date']}")
                    with col2:
                        st.markdown("**✅ Approval Status:**")
                        st.success(f"Stage 1: ✅ {row['stage1_approved_by']}")
                        st.success(f"Stage 2: ✅ {row['stage2_approved_by']}")
                    
                    st.markdown("---")
                    st.markdown("**💳 Payment Details**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        payment_mode = st.selectbox("Payment Mode", PAYMENT_MODES, key=f"pm_{row['id']}")
                        transaction_ref = st.text_input("Transaction Reference/Cheque No.", key=f"tr_{row['id']}", 
                                                       placeholder="Enter reference number")
                    with col2:
                        remarks = st.text_area("Payment Remarks", key=f"remarks_s3_{row['id']}", 
                                             placeholder="Enter payment notes...",
                                             height=100)
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("💰 Mark as Paid", key=f"paid_{row['id']}", type="primary", use_container_width=True):
                            if transaction_ref:
                                approve_expense_stage3(row['id'], st.session_state.full_name, 'Paid', 
                                                     payment_mode, transaction_ref, remarks)
                                st.success("✅ Payment Processed!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide transaction reference")
                    
                    with col2:
                        if st.button("❌ Reject Payment", key=f"reject_s3_{row['id']}", use_container_width=True):
                            if remarks:
                                approve_expense_stage3(row['id'], st.session_state.full_name, 'Rejected', 
                                                     None, None, remarks)
                                st.error("❌ Payment Rejected!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending payments!")
    
    with tab2:
        payment_history = get_approved_expenses_by_user(st.session_state.full_name, 3)
        
        if not payment_history.empty:
            col1, col2, col3, col4 = st.columns(4)
            total_paid = len(payment_history[payment_history['stage3_status'] == 'Paid'])
            total_rejected = len(payment_history[payment_history['stage3_status'] == 'Rejected'])
            amount_paid = payment_history[payment_history['stage3_status'] == 'Paid']['amount'].sum()
            
            col1.metric("💰 Paid", total_paid)
            col2.metric("❌ Rejected", total_rejected)
            col3.metric("💵 Total Amount Paid", f"₹{amount_paid:,.2f}")
            col4.metric("📝 Total Processed", len(payment_history))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            for idx, row in payment_history.iterrows():
                status_display = get_stage_status_display(row)
                status_icon = "✅" if row['stage3_status'] == 'Paid' else "❌"
                
                with st.expander(f"{status_icon} **ID: {row['id']}** | {row['brand']} | **₹{row['amount']:,.2f}** | {status_display}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    with col2:
                        st.metric("🏢 Brand", row['brand'])
                    with col3:
                        st.metric("📂 Category", row['category'])
                    
                    st.markdown("---")
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("---")
                    st.markdown("**Your Payment Details:**")
                    if row['stage3_status'] == 'Paid':
                        st.success(f"✅ **Paid** on {row['stage3_paid_date']}")
                        st.markdown(f"**💳 Payment Mode:** {row['stage3_payment_mode']}")
                        st.markdown(f"**🔢 Transaction Ref:** {row['stage3_transaction_ref']}")
                    else:
                        st.error(f"❌ **Rejected** on {row['stage3_paid_date']}")
                    
                    if row['stage3_remarks']:
                        st.markdown(f"**💬 Remarks:** {row['stage3_remarks']}")
        else:
            st.info("📌 You haven't processed any payments yet.")

# Page 6: Dashboard
elif page_clean == "Dashboard":
    st.markdown("### 📊 Dashboard Overview")
    
    df = get_all_expenses()
    
    if not df.empty:
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Total Expenses", f"₹{df['amount'].sum():,.2f}")
        col2.metric("📝 Total Transactions", len(df))
        col3.metric("✅ Paid", len(df[df['stage3_status'] == 'Paid']))
        col4.metric("⏳ Pending", len(df[df['stage3_status'] == 'Pending']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Brand summary chart
            brand_summary = df.groupby('brand')['amount'].sum().reset_index()
            brand_summary = brand_summary.nlargest(10, 'amount')
            
            fig = px.bar(brand_summary, x='brand', y='amount', 
                        title='Top 10 Brands by Expense',
                        labels={'amount': 'Amount (₹)', 'brand': 'Brand'},
                        color='amount',
                        color_continuous_scale='Blues')
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Category summary
            category_summary = df.groupby('category')['amount'].sum().reset_index()
            fig = px.pie(category_summary, values='amount', names='category',
                        title='Expenses by Category')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Status summary
        st.markdown("### 📈 Status Distribution")
        status_counts = df['Overall_Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            paid_count = len(df[df['stage3_status'] == 'Paid'])
            st.metric("✅ Paid", paid_count, f"{(paid_count/len(df)*100):.1f}%")
        with col2:
            pending_count = len(df[df['stage3_status'] == 'Pending'])
            st.metric("⏳ Pending", pending_count, f"{(pending_count/len(df)*100):.1f}%")
        with col3:
            rejected_count = len(df[(df['stage1_status'] == 'Rejected') | (df['stage2_status'] == 'Rejected') | (df['stage3_status'] == 'Rejected')])
            st.metric("❌ Rejected", rejected_count, f"{(rejected_count/len(df)*100):.1f}%")
    else:
        st.info("📌 No expenses recorded yet.")

# Page 7: View All Expenses
elif page_clean == "All Expenses":
    st.markdown("### 📋 All Expenses")
    
    df = get_all_expenses()
    
    if not df.empty:
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💵 Total Amount", f"₹{df['amount'].sum():,.2f}")
        col2.metric("📝 Total Count", len(df))
        col3.metric("✅ Paid", len(df[df['stage3_status'] == 'Paid']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Filters
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                brand_filter = st.multiselect("Filter by Brand", options=df['brand'].unique())
            with col2:
                category_filter = st.multiselect("Filter by Category", options=df['category'].unique())
            with col3:
                status_filter = st.multiselect("Filter by Status", options=df['Overall_Status'].unique())
            
            # Apply filters
            filtered_df = df.copy()
            if brand_filter:
                filtered_df = filtered_df[filtered_df['brand'].isin(brand_filter)]
            if category_filter:
                filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
            if status_filter:
                filtered_df = filtered_df[filtered_df['Overall_Status'].isin(status_filter)]
        else:
            filtered_df = df
        
        display_df = filtered_df[[
            'id', 'date', 'brand', 'category', 'amount', 'description',
            'added_by', 'stage1_assigned_to', 'stage1_status', 'stage2_status', 'stage3_status', 'Overall_Status'
        ]].copy()
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            excel_data = to_excel(filtered_df)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("📌 No expenses recorded yet.")

# Page 8: User Management (Admin Only)
elif page_clean == "User Management":
    st.markdown("### 👥 User Management")
    
    tab1, tab2 = st.tabs(["➕ Create New User", "📋 Manage Users"])
    
    with tab1:
        st.markdown("#### Create New User Account")
        
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with
