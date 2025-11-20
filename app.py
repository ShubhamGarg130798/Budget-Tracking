import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .stMetric label {
        font-size: 16px !important;
    }
    .stMetric .metric-value {
        font-size: 28px !important;
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-approved {
        background-color: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-rejected {
        background-color: #f8d7da;
        color: #721c24;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-paid {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# USER ROLES AND ACCESS CONTROL
# Configure access for different roles
USER_ROLES = {
    # HR - Can only add expenses
    "hr": {
        "users": ["HR", "HR Team", "Rahul", "Priya", "Neha"],  # Add your HR staff names here
        "stage": 0,
        "title": "HR - Brand Staff"
    },
    # Brand Heads - Stage 1 Approvers
    "brand_heads": {
        "users": ["Swati", "Ashutosh"],
        "stage": 1,
        "title": "Brand Head"
    },
    # Stage 2 Approver - Shruti Ma'am
    "stage2_approver": {
        "users": ["Shruti", "Shruti Mam", "Shruti Ma'am"],
        "stage": 2,
        "title": "Senior Manager"
    },
    # Accounts Team - Stage 3 (Payment)
    "accounts_team": {
        "users": ["Hansi", "Accounts", "Shubham", "Finance Team"],
        "stage": 3,
        "title": "Accounts Team"
    },
    # Admin - Full access
    "admin": {
        "users": ["Admin", "Shubham"],
        "stage": 99,
        "title": "Administrator"
    }
}

def get_user_role(username):
    """Determine user role based on username"""
    if not username:
        return None, None
    
    username_lower = username.lower().strip()
    
    for role, config in USER_ROLES.items():
        if any(user.lower() == username_lower for user in config["users"]):
            return role, config["stage"]
    
    return None, None

# Database setup
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
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
    
    # Check if columns exist and add them if they don't (for existing databases)
    c.execute("PRAGMA table_info(expenses)")
    columns = [col[1] for col in c.fetchall()]
    
    new_columns = [
        ("stage1_status", "TEXT DEFAULT 'Pending'"),
        ("stage1_approved_by", "TEXT"),
        ("stage1_approved_date", "TIMESTAMP"),
        ("stage1_remarks", "TEXT"),
        ("stage2_status", "TEXT DEFAULT 'Pending'"),
        ("stage2_approved_by", "TEXT"),
        ("stage2_approved_date", "TIMESTAMP"),
        ("stage2_remarks", "TEXT"),
        ("stage3_status", "TEXT DEFAULT 'Pending'"),
        ("stage3_paid_by", "TEXT"),
        ("stage3_paid_date", "TIMESTAMP"),
        ("stage3_payment_mode", "TEXT"),
        ("stage3_transaction_ref", "TEXT"),
        ("stage3_remarks", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            try:
                c.execute(f"ALTER TABLE expenses ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists
    
    # Update existing records to have default status if NULL
    c.execute("""
        UPDATE expenses 
        SET stage1_status = 'Pending' 
        WHERE stage1_status IS NULL
    """)
    c.execute("""
        UPDATE expenses 
        SET stage2_status = 'Pending' 
        WHERE stage2_status IS NULL
    """)
    c.execute("""
        UPDATE expenses 
        SET stage3_status = 'Pending' 
        WHERE stage3_status IS NULL
    """)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Brand list
BRANDS = [
    "FundoBaBa", "Salary Adda", "FastPaise", "SnapPaisa", "Salary 4 Sure", "Duniya Finance",
    "Tejas", "BlinkR", "Salary Setu", "Qua Loans", "Paisa Pop", "Salary 4 You",
    "Rupee Hype", "Minutes Loan", "Squid Loan", "Zepto", "Paisa on Salary", "Jhatpat"
]

# Expense categories
CATEGORIES = [
    "Marketing", "Operations", "Salaries", "Technology", "Office Rent",
    "Utilities", "Travel", "Professional Fees", "Commission", "Interest", "Petty Cash", "Other"
]

PAYMENT_MODES = ["Cash", "Bank Transfer", "Cheque", "UPI", "Card", "Other"]

# Helper functions
def add_expense(date, brand, category, amount, description, added_by):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO expenses (date, brand, category, amount, description, added_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, brand, category, amount, description, added_by))
    conn.commit()
    conn.close()

def get_all_expenses():
    conn = sqlite3.connect('expenses.db')
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC", conn)
    conn.close()
    return df

def get_expenses_for_approval(stage):
    """Get expenses pending at specific approval stage"""
    conn = sqlite3.connect('expenses.db')
    
    if stage == 1:
        query = """
            SELECT id, date, brand, category, amount, description, added_by, 
                   stage1_status, stage2_status, stage3_status, created_at
            FROM expenses
            WHERE stage1_status = 'Pending'
            ORDER BY created_at ASC
        """
    elif stage == 2:
        query = """
            SELECT id, date, brand, category, amount, description, added_by,
                   stage1_status, stage1_approved_by, stage1_approved_date,
                   stage2_status, stage3_status, created_at
            FROM expenses
            WHERE stage1_status = 'Approved' AND stage2_status = 'Pending'
            ORDER BY created_at ASC
        """
    elif stage == 3:
        query = """
            SELECT id, date, brand, category, amount, description, added_by,
                   stage1_status, stage2_status, stage3_status, created_at
            FROM expenses
            WHERE stage1_status = 'Approved' AND stage2_status = 'Approved' 
                  AND stage3_status = 'Pending'
            ORDER BY created_at ASC
        """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_approved_expenses_by_user(username, stage):
    """Get all expenses approved by a specific user at a given stage"""
    conn = sqlite3.connect('expenses.db')
    
    if stage == 1:
        query = """
            SELECT id, date, brand, category, amount, description, added_by,
                   stage1_status, stage1_approved_date, stage1_remarks,
                   stage2_status, stage3_status
            FROM expenses
            WHERE stage1_approved_by = ? AND stage1_status IN ('Approved', 'Rejected')
            ORDER BY stage1_approved_date DESC
        """
    elif stage == 2:
        query = """
            SELECT id, date, brand, category, amount, description, added_by,
                   stage1_status, stage2_status, stage2_approved_date, stage2_remarks,
                   stage3_status
            FROM expenses
            WHERE stage2_approved_by = ? AND stage2_status IN ('Approved', 'Rejected')
            ORDER BY stage2_approved_date DESC
        """
    elif stage == 3:
        query = """
            SELECT id, date, brand, category, amount, description, added_by,
                   stage1_status, stage2_status, stage3_status, stage3_paid_date,
                   stage3_payment_mode, stage3_transaction_ref, stage3_remarks
            FROM expenses
            WHERE stage3_paid_by = ? AND stage3_status IN ('Paid', 'Rejected')
            ORDER BY stage3_paid_date DESC
        """
    
    df = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return df

def get_expenses_by_user(username):
    """Get all expenses added by a specific user (for HR view)"""
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT id, date, brand, category, amount, description, added_by,
               stage1_status, stage2_status, stage3_status, created_at
        FROM expenses
        WHERE added_by = ?
        ORDER BY created_at DESC
    """
    df = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return df

def approve_expense_stage1(expense_id, approved_by, status, remarks):
    """Approve/Reject at Stage 1 (Brand Head)"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses
        SET stage1_status = ?,
            stage1_approved_by = ?,
            stage1_approved_date = ?,
            stage1_remarks = ?
        WHERE id = ?
    ''', (status, approved_by, datetime.now(), remarks, expense_id))
    conn.commit()
    conn.close()

def approve_expense_stage2(expense_id, approved_by, status, remarks):
    """Approve/Reject at Stage 2 (Shruti Ma'am)"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses
        SET stage2_status = ?,
            stage2_approved_by = ?,
            stage2_approved_date = ?,
            stage2_remarks = ?
        WHERE id = ?
    ''', (status, approved_by, datetime.now(), remarks, expense_id))
    conn.commit()
    conn.close()

def approve_expense_stage3(expense_id, paid_by, status, payment_mode, transaction_ref, remarks):
    """Mark as Paid at Stage 3 (Accounts)"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        UPDATE expenses
        SET stage3_status = ?,
            stage3_paid_by = ?,
            stage3_paid_date = ?,
            stage3_payment_mode = ?,
            stage3_transaction_ref = ?,
            stage3_remarks = ?
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

def get_brand_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT brand, 
               SUM(amount) as total_amount, 
               COUNT(*) as transaction_count
        FROM expenses
        GROUP BY brand
        ORDER BY total_amount DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_category_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT category,
               SUM(amount) as total_amount,
               COUNT(*) as transaction_count
        FROM expenses
        GROUP BY category
        ORDER BY total_amount DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_daily_expenses():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT date,
               SUM(amount) as total_amount
        FROM expenses
        GROUP BY date
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_top_expenses(limit=10):
    conn = sqlite3.connect('expenses.db')
    query = f"""
        SELECT date, brand, category, amount, description
        FROM expenses
        ORDER BY amount DESC
        LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_expense(expense_id):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# User Authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_stage = None

if not st.session_state.logged_in:
    st.title("🔐 Login - Brand Expense Tracker")
    st.markdown("---")
    
    username = st.text_input("👤 Enter Your Name", placeholder="e.g., Rahul, Shruti, Shubham")
    
    if st.button("🚀 Login", use_container_width=True, type="primary"):
        if username:
            role, stage = get_user_role(username)
            if role:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_role = role
                st.session_state.user_stage = stage
                st.success(f"✅ Welcome {username}!")
                st.rerun()
            else:
                st.error("❌ Access Denied! Your name is not registered in the system.")
        else:
            st.warning("⚠️ Please enter your name")
    
    st.markdown("---")
    st.info("""
    **👥 Registered Users:**
    - **HR - Brand Staff:** HR, HR Team, Rahul, Priya, Neha
    - **Brand Heads:** Swati, Ashutosh
    - **Senior Manager:** Shruti Ma'am
    - **Accounts Team:** Hansi, Shubham, Accounts, Finance Team
    - **Admin:** Admin, Shubham
    """)
    st.stop()

# Main App (After Login)
st.title("💰 Brand Expense Tracker")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"**Logged in as:** {st.session_state.username} ({USER_ROLES[st.session_state.user_role]['title']})")
with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_stage = None
        st.rerun()

st.markdown("---")

# Sidebar for navigation based on role
# Start with Add Expense as the first option for everyone
page_options = ["➕ Add Expense"]

# HR users only get Add Expense and My Expenses
if st.session_state.user_role == "hr":
    page_options.append("📝 My Expenses")
else:
    # Add approval pages based on role
    if st.session_state.user_role == "brand_heads" or st.session_state.user_role == "admin":
        page_options.append("✅ Approval Stage 1 (Brand Head)")

    if st.session_state.user_role == "stage2_approver" or st.session_state.user_role == "admin":
        page_options.append("✅ Approval Stage 2 (Shruti Ma'am)")

    if st.session_state.user_role == "accounts_team" or st.session_state.user_role == "admin":
        page_options.append("💳 Approval Stage 3 (Accounts Payment)")

    # Everyone except HR can see dashboard and all expenses
    page_options.extend(["📊 Dashboard", "📋 View All Expenses"])

page = st.sidebar.selectbox("📌 Navigation", page_options)

# Remove emoji from page name for comparison
page_clean = page.split(" ", 1)[1] if " " in page else page

# Page 1: Add Expense
if page_clean == "Add Expense":
    st.header("➕ Add New Expense")
    
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("📅 Date", value=date.today())
            brand = st.selectbox("🏢 Brand", BRANDS)
            category = st.selectbox("📂 Category", CATEGORIES)
        
        with col2:
            amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
            added_by = st.text_input("👤 Added By", value=st.session_state.username)
        
        description = st.text_area("📝 Description", placeholder="Enter expense details...")
        
        submitted = st.form_submit_button("✅ Add Expense", use_container_width=True, type="primary")
        
        if submitted:
            if amount > 0 and added_by:
                add_expense(expense_date, brand, category, amount, description, added_by)
                st.toast(f"✅ Expense of ₹{amount:,.2f} added successfully for {brand}!", icon="✅")
                st.success("🎉 Expense submitted successfully! It will now go through the approval workflow.")
            else:
                st.error("⚠️ Please enter amount and your name!")

# Page: My Expenses (HR View)
elif page_clean == "My Expenses":
    st.header("📝 My Submitted Expenses")
    
    my_expenses = get_expenses_by_user(st.session_state.username)
    
    if not my_expenses.empty:
        # Add overall status column
        my_expenses['Overall_Status'] = my_expenses.apply(get_overall_status, axis=1)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = my_expenses['amount'].sum()
        total_count = len(my_expenses)
        pending_count = len(my_expenses[my_expenses['stage1_status'] == 'Pending'])
        paid_count = len(my_expenses[my_expenses['stage3_status'] == 'Paid'])
        
        col1.metric("💰 Total Amount", f"₹{total_expenses:,.2f}")
        col2.metric("📝 Total Expenses", total_count)
        col3.metric("⏳ Pending", pending_count)
        col4.metric("✅ Paid", paid_count)
        
        st.markdown("---")
        
        # Display table
        display_df = my_expenses[[
            'id', 'date', 'brand', 'category', 'amount', 'description',
            'stage1_status', 'stage2_status', 'stage3_status', 
            'Overall_Status', 'created_at'
        ]].copy()
        
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        display_df = display_df.rename(columns={
            'stage1_status': 'Stage 1',
            'stage2_status': 'Stage 2',
            'stage3_status': 'Payment',
            'Overall_Status': 'Status',
            'created_at': 'Submitted On'
        })
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export option
        excel_data = to_excel(my_expenses)
        st.download_button(
            label="📥 Download My Expenses",
            data=excel_data,
            file_name=f"my_expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📌 You haven't submitted any expenses yet.")

# Page: Approval Stage 1 (Brand Head)
elif "Approval Stage 1" in page_clean:
    st.header("✅ Approval Stage 1 - Brand Head Review")
    
    tab1, tab2 = st.tabs(["📝 Pending Approvals", "📊 My Approval History"])
    
    with tab1:
        st.subheader("Expenses Pending Your Approval")
        pending_expenses = get_expenses_for_approval(1)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending approval")
            
            for idx, row in pending_expenses.iterrows():
                with st.expander(f"🆔 ID: {row['id']} | {row['brand']} | ₹{row['amount']:,.2f} | {row['date']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['category'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Date:** {row['date']}")
                    st.markdown(f"**🕐 Submitted On:** {row['created_at']}")
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        remarks = st.text_area(f"💬 Remarks (Optional)", key=f"remarks_s1_{row['id']}")
                    
                    with col2:
                        st.write("**Action:**")
                        if st.button(f"✅ Approve", key=f"approve_s1_{row['id']}", type="primary"):
                            approve_expense_stage1(row['id'], st.session_state.username, 'Approved', remarks)
                            st.success(f"✅ Expense ID {row['id']} approved!")
                            st.rerun()
                        
                        if st.button(f"❌ Reject", key=f"reject_s1_{row['id']}", type="secondary"):
                            if remarks:
                                approve_expense_stage1(row['id'], st.session_state.username, 'Rejected', remarks)
                                st.error(f"❌ Expense ID {row['id']} rejected!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals! All expenses have been reviewed.")
    
    with tab2:
        st.subheader("My Approval History")
        approved_expenses = get_approved_expenses_by_user(st.session_state.username, 1)
        
        if not approved_expenses.empty:
            # Add overall status column
            approved_expenses['Overall Status'] = approved_expenses.apply(get_overall_status, axis=1)
            
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
            display_df = approved_expenses[[
                'id', 'date', 'brand', 'category', 'amount', 'description',
                'stage1_status', 'stage1_approved_date', 'stage1_remarks',
                'stage2_status', 'stage3_status', 'Overall Status'
            ]].copy()
            
            display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df = display_df.rename(columns={
                'stage1_status': 'My Decision',
                'stage1_approved_date': 'My Approval Date',
                'stage1_remarks': 'My Remarks',
                'stage2_status': 'Stage 2 Status',
                'stage3_status': 'Payment Status'
            })
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("📌 You haven't approved any expenses yet.")

# Page: Approval Stage 2 (Shruti Ma'am)
elif "Approval Stage 2" in page_clean:
    st.header("✅ Approval Stage 2 - Senior Manager Review (Shruti Ma'am)")
    
    tab1, tab2 = st.tabs(["📝 Pending Approvals", "📊 My Approval History"])
    
    with tab1:
        st.subheader("Expenses Pending Your Approval")
        pending_expenses = get_expenses_for_approval(2)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) pending approval")
            
            for idx, row in pending_expenses.iterrows():
                with st.expander(f"🆔 ID: {row['id']} | {row['brand']} | ₹{row['amount']:,.2f} | {row['date']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric("💰 Amount", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['category'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Date:** {row['date']}")
                    
                    st.markdown("**Stage 1 Approval:**")
                    st.markdown(f"- ✅ Approved by: {row['stage1_approved_by']}")
                    st.markdown(f"- 📅 Approved on: {row['stage1_approved_date']}")
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        remarks = st.text_area(f"💬 Remarks (Optional)", key=f"remarks_s2_{row['id']}")
                    
                    with col2:
                        st.write("**Action:**")
                        if st.button(f"✅ Approve", key=f"approve_s2_{row['id']}", type="primary"):
                            approve_expense_stage2(row['id'], st.session_state.username, 'Approved', remarks)
                            st.success(f"✅ Expense ID {row['id']} approved!")
                            st.rerun()
                        
                        if st.button(f"❌ Reject", key=f"reject_s2_{row['id']}", type="secondary"):
                            if remarks:
                                approve_expense_stage2(row['id'], st.session_state.username, 'Rejected', remarks)
                                st.error(f"❌ Expense ID {row['id']} rejected!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending approvals! All expenses have been reviewed.")
    
    with tab2:
        st.subheader("My Approval History")
        approved_expenses = get_approved_expenses_by_user(st.session_state.username, 2)
        
        if not approved_expenses.empty:
            # Add overall status column
            approved_expenses['Overall Status'] = approved_expenses.apply(get_overall_status, axis=1)
            
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
            display_df = approved_expenses[[
                'id', 'date', 'brand', 'category', 'amount', 'description',
                'stage2_status', 'stage2_approved_date', 'stage2_remarks',
                'stage3_status', 'Overall Status'
            ]].copy()
            
            display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df = display_df.rename(columns={
                'stage2_status': 'My Decision',
                'stage2_approved_date': 'My Approval Date',
                'stage2_remarks': 'My Remarks',
                'stage3_status': 'Payment Status'
            })
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("📌 You haven't approved any expenses yet.")

# Page: Approval Stage 3 (Accounts Payment)
elif "Approval Stage 3" in page_clean:
    st.header("💳 Approval Stage 3 - Accounts Payment Processing")
    
    tab1, tab2 = st.tabs(["📝 Pending Payments", "📊 Payment History"])
    
    with tab1:
        st.subheader("Expenses Ready for Payment")
        pending_expenses = get_expenses_for_approval(3)
        
        if not pending_expenses.empty:
            st.info(f"📌 You have **{len(pending_expenses)}** expense(s) ready for payment")
            
            for idx, row in pending_expenses.iterrows():
                with st.expander(f"🆔 ID: {row['id']} | {row['brand']} | ₹{row['amount']:,.2f} | {row['date']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric("💰 Amount to Pay", f"₹{row['amount']:,.2f}")
                    col2.metric("🏢 Brand", row['brand'])
                    col3.metric("📂 Category", row['category'])
                    
                    st.markdown(f"**📝 Description:** {row['description']}")
                    st.markdown(f"**👤 Submitted By:** {row['added_by']}")
                    st.markdown(f"**📅 Expense Date:** {row['date']}")
                    
                    st.markdown("**✅ Approval Status:**")
                    st.markdown(f"- Stage 1: ✅ Approved")
                    st.markdown(f"- Stage 2: ✅ Approved")
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        payment_mode = st.selectbox(
                            "💳 Payment Mode", 
                            PAYMENT_MODES, 
                            key=f"payment_mode_{row['id']}"
                        )
                        transaction_ref = st.text_input(
                            "🔢 Transaction Reference/Cheque No.", 
                            key=f"trans_ref_{row['id']}"
                        )
                    
                    with col2:
                        remarks = st.text_area(
                            f"💬 Payment Remarks", 
                            key=f"remarks_s3_{row['id']}"
                        )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"💰 Mark as Paid", key=f"paid_s3_{row['id']}", type="primary"):
                            if transaction_ref:
                                approve_expense_stage3(
                                    row['id'], 
                                    st.session_state.username, 
                                    'Paid', 
                                    payment_mode, 
                                    transaction_ref, 
                                    remarks
                                )
                                st.success(f"✅ Payment processed for Expense ID {row['id']}!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide transaction reference")
                    
                    with col2:
                        if st.button(f"❌ Reject Payment", key=f"reject_s3_{row['id']}", type="secondary"):
                            if remarks:
                                approve_expense_stage3(
                                    row['id'], 
                                    st.session_state.username, 
                                    'Rejected', 
                                    None, 
                                    None, 
                                    remarks
                                )
                                st.error(f"❌ Payment rejected for Expense ID {row['id']}!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Please provide remarks for rejection")
        else:
            st.success("✅ No pending payments! All approved expenses have been processed.")
    
    with tab2:
        st.subheader("Payment History")
        payment_history = get_approved_expenses_by_user(st.session_state.username, 3)
        
        if not payment_history.empty:
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
            display_df = payment_history[[
                'id', 'date', 'brand', 'category', 'amount', 'description',
                'stage3_status', 'stage3_paid_date', 'stage3_payment_mode',
                'stage3_transaction_ref', 'stage3_remarks'
            ]].copy()
            
            display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df = display_df.rename(columns={
                'stage3_status': 'Payment Status',
                'stage3_paid_date': 'Payment Date',
                'stage3_payment_mode': 'Payment Mode',
                'stage3_transaction_ref': 'Transaction Ref',
                'stage3_remarks': 'Remarks'
            })
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("📌 You haven't processed any payments yet.")

# Page 2: Dashboard
elif page_clean == "Dashboard":
    st.header("📊 Dashboard Overview")
    
    df = get_all_expenses()
    
    if not df.empty:
        # Add overall status
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = df['amount'].sum()
        total_transactions = len(df)
        total_paid = len(df[df['stage3_status'] == 'Paid'])
        amount_paid = df[df['stage3_status'] == 'Paid']['amount'].sum()
        
        col1.metric("💵 Total Expenses", f"₹{total_expenses:,.2f}")
        col2.metric("📝 Total Transactions", f"{total_transactions:,}")
        col3.metric("✅ Paid Transactions", f"{total_paid}")
        col4.metric("💰 Amount Paid", f"₹{amount_paid:,.2f}")
        
        st.markdown("---")
        
        # Approval Status Summary
        st.subheader("📊 Approval Status Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        pending_s1 = len(df[df['stage1_status'] == 'Pending'])
        pending_s2 = len(df[(df['stage1_status'] == 'Approved') & (df['stage2_status'] == 'Pending')])
        pending_s3 = len(df[(df['stage2_status'] == 'Approved') & (df['stage3_status'] == 'Pending')])
        rejected = len(df[(df['stage1_status'] == 'Rejected') | (df['stage2_status'] == 'Rejected') | (df['stage3_status'] == 'Rejected')])
        
        col1.metric("⏳ Pending Stage 1", pending_s1)
        col2.metric("⏳ Pending Stage 2", pending_s2)
        col3.metric("⏳ Pending Payment", pending_s3)
        col4.metric("❌ Rejected", rejected)
        
        st.markdown("---")
        
        # Row 1: Brand and Category Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 10 Brands by Expense")
            brand_summary = get_brand_summary().head(10)
            fig_brand = px.bar(
                brand_summary,
                x='brand',
                y='total_amount',
                title='',
                labels={'total_amount': 'Total Amount (₹)', 'brand': 'Brand'},
                color='total_amount',
                color_continuous_scale='Blues',
                text='total_amount'
            )
            fig_brand.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_brand.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_brand, use_container_width=True)
        
        with col2:
            st.subheader("📂 Expenses by Category")
            category_summary = get_category_summary()
            fig_category = px.pie(
                category_summary,
                values='total_amount',
                names='category',
                title='',
                hole=0.4
            )
            fig_category.update_traces(textposition='inside', textinfo='percent+label')
            fig_category.update_layout(height=400)
            st.plotly_chart(fig_category, use_container_width=True)
        
        st.markdown("---")
        
        # Row 2: Daily Expense Pattern
        st.subheader("📉 Daily Expense Pattern")
        daily_summary = get_daily_expenses()
        if not daily_summary.empty:
            fig_daily = px.area(
                daily_summary,
                x='date',
                y='total_amount',
                title='',
                labels={'total_amount': 'Total Amount (₹)', 'date': 'Date'}
            )
            fig_daily.update_traces(line_color='#ff7f0e', fillcolor='rgba(255,127,14,0.3)')
            fig_daily.update_layout(height=400)
            st.plotly_chart(fig_daily, use_container_width=True)
        
    else:
        st.info("📌 No expenses recorded yet. Add your first expense to see the dashboard!")

# Page 3: View All Expenses
elif page_clean == "View All Expenses":
    st.header("📋 All Expenses")
    
    df = get_all_expenses()
    
    if not df.empty:
        # Add overall status
        df['Overall_Status'] = df.apply(get_overall_status, axis=1)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            brand_filter = st.multiselect("🏢 Filter by Brand", options=df['brand'].unique(), default=None)
        with col2:
            category_filter = st.multiselect("📂 Filter by Category", options=df['category'].unique(), default=None)
        with col3:
            status_filter = st.multiselect(
                "📊 Filter by Status",
                options=df['Overall_Status'].unique(),
                default=None
            )
        
        # Apply filters
        filtered_df = df.copy()
        if brand_filter:
            filtered_df = filtered_df[filtered_df['brand'].isin(brand_filter)]
        if category_filter:
            filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
        if status_filter:
            filtered_df = filtered_df[filtered_df['Overall_Status'].isin(status_filter)]
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Total Expenses", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("📝 Transaction Count", len(filtered_df))
        col3.metric("📊 Average Amount", f"₹{filtered_df['amount'].mean():,.2f}")
        col4.metric("✅ Paid Count", len(filtered_df[filtered_df['stage3_status'] == 'Paid']))
        
        st.markdown("---")
        
        # Display data with approval status
        display_df = filtered_df[[
            'id', 'date', 'brand', 'category', 'amount', 'description', 'added_by',
            'stage1_status', 'stage2_status', 'stage3_status', 'Overall_Status'
        ]].copy()
        
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        display_df = display_df.rename(columns={
            'stage1_status': 'Stage 1',
            'stage2_status': 'Stage 2',
            'stage3_status': 'Payment',
            'Overall_Status': 'Overall Status'
        })
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export button
        excel_data = to_excel(filtered_df)
        st.download_button(
            label="📥 Download as Excel",
            data=excel_data,
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Delete functionality (admin only)
        if st.session_state.user_role == "admin":
            st.markdown("---")
            with st.expander("🗑️ Delete Expense (Admin Only)"):
                expense_to_delete = st.selectbox(
                    "Select expense to delete",
                    options=filtered_df['id'].tolist(),
                    format_func=lambda x: f"ID: {x} - {filtered_df[filtered_df['id']==x]['brand'].values[0]} - ₹{filtered_df[filtered_df['id']==x]['amount'].values[0]:,.2f}"
                )
                if st.button("🗑️ Delete Selected Expense", type="secondary"):
                    delete_expense(expense_to_delete)
                    st.success("✅ Expense deleted successfully!")
                    st.rerun()
    
    else:
        st.info("📌 No expenses recorded yet. Add your first expense!")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        💡 <b>Multi-Stage Approval System:</b> HR Entry → Stage 1 (Brand Head) → Stage 2 (Shruti Ma'am) → Stage 3 (Accounts Payment) | 
        🔐 Role-based access control enabled
    </div>
""", unsafe_allow_html=True)
