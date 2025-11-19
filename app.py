import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker - Approval System",
    page_icon="💰",
    layout="wide"
)

# Database setup with WAL mode for better concurrency
def get_connection():
    """Get database connection with timeout and WAL mode"""
    conn = sqlite3.connect('expenses.db', timeout=30.0, check_same_thread=False, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for better concurrency
    return conn

def init_db():
    """Initialize database with proper error handling"""
    try:
        conn = get_connection()
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
                requested_by TEXT,
                status TEXT DEFAULT 'Pending',
                approved_by TEXT,
                approval_date TIMESTAMP,
                rejection_reason TEXT,
                invoice_number TEXT,
                invoice_date DATE,
                receipt_image BLOB,
                receipt_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        return False

# Initialize database once per session
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True
    else:
        st.error("Failed to initialize database. Please refresh the page.")
        st.stop()

# Brand list
BRANDS = [
    "Fundobaba",
    "Fastpaisa",
    "Snap Paisa",
    "Salary 4 Sure",
    "Duniya Finance",
    "Tejas",
    "BlinkR",
    "Salary Setu",
    "Salary Adda",
    "Paisa on Salary",
    "Zepto Finance",
    "Squid Loan",
    "Qua Loan",
    "Salary 4 You",
    "PaisaPop",
    "Jhatpat Cash",
    "Rupee Hype",
    "Minutes Loan"
]

# Expense categories
CATEGORIES = [
    "Marketing",
    "Operations",
    "Salaries",
    "Technology",
    "Office Rent",
    "Utilities",
    "Travel",
    "Professional Fees",
    "Commission",
    "Interest",
    "Other"
]

# Status types
STATUSES = ["Pending", "Approved", "Rejected", "Completed"]

# Helper functions with improved error handling
def add_quotation(date, brand, category, amount, description, requested_by):
    """Add new expense quotation (request)"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO expenses (date, brand, category, amount, description, requested_by, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        ''', (str(date), brand, category, float(amount), description, requested_by))
        
        expense_id = c.lastrowid
        conn.close()
        return expense_id, None
    except Exception as e:
        return None, str(e)

def get_all_expenses(status_filter=None):
    """Get all expenses with optional status filter"""
    try:
        conn = get_connection()
        if status_filter and status_filter != "All":
            df = pd.read_sql_query(
                "SELECT * FROM expenses WHERE status = ? ORDER BY created_at DESC", 
                conn, 
                params=(status_filter,)
            )
        else:
            df = pd.read_sql_query("SELECT * FROM expenses ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading expenses: {str(e)}")
        return pd.DataFrame()

def get_pending_approvals():
    """Get all pending approval requests"""
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM expenses WHERE status = 'Pending' ORDER BY created_at DESC", 
            conn
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading pending approvals: {str(e)}")
        return pd.DataFrame()

def get_approved_without_invoice():
    """Get approved expenses that need invoice"""
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM expenses WHERE status = 'Approved' ORDER BY approval_date DESC", 
            conn
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading approved expenses: {str(e)}")
        return pd.DataFrame()

def approve_expense(expense_id, approved_by):
    """Approve an expense request"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE expenses 
            SET status = 'Approved', 
                approved_by = ?, 
                approval_date = ?,
                updated_at = ?
            WHERE id = ?
        ''', (approved_by, datetime.now(), datetime.now(), expense_id))
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def reject_expense(expense_id, approved_by, reason):
    """Reject an expense request"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE expenses 
            SET status = 'Rejected', 
                approved_by = ?, 
                approval_date = ?,
                rejection_reason = ?,
                updated_at = ?
            WHERE id = ?
        ''', (approved_by, datetime.now(), reason, datetime.now(), expense_id))
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def add_invoice_and_receipt(expense_id, invoice_number, invoice_date, receipt_image, receipt_filename):
    """Add invoice details and receipt image to approved expense"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Convert image to binary
        if receipt_image:
            img_byte_arr = io.BytesIO()
            receipt_image.save(img_byte_arr, format=receipt_image.format)
            img_binary = img_byte_arr.getvalue()
        else:
            img_binary = None
        
        c.execute('''
            UPDATE expenses 
            SET status = 'Completed',
                invoice_number = ?,
                invoice_date = ?,
                receipt_image = ?,
                receipt_filename = ?,
                updated_at = ?
            WHERE id = ?
        ''', (invoice_number, str(invoice_date), img_binary, receipt_filename, datetime.now(), expense_id))
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def get_expense_by_id(expense_id):
    """Get single expense details"""
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM expenses WHERE id = ?", conn, params=(expense_id,))
        conn.close()
        if not df.empty:
            return df.iloc[0]
        return None
    except Exception as e:
        st.error(f"Error loading expense: {str(e)}")
        return None

def get_receipt_image(expense_id):
    """Get receipt image for an expense"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT receipt_image, receipt_filename FROM expenses WHERE id = ?", (expense_id,))
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        st.error(f"Error loading receipt: {str(e)}")
        return None

def get_summary_by_status():
    """Get summary grouped by status"""
    try:
        conn = get_connection()
        query = """
            SELECT 
                status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM expenses
            GROUP BY status
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading summary: {str(e)}")
        return pd.DataFrame()

def get_brand_summary(status_filter="Completed"):
    """Get brand-wise summary for completed expenses"""
    try:
        conn = get_connection()
        query = """
            SELECT 
                brand,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count
            FROM expenses
            WHERE status = ?
            GROUP BY brand
            ORDER BY total_amount DESC
        """
        df = pd.read_sql_query(query, conn, params=(status_filter,))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading brand summary: {str(e)}")
        return pd.DataFrame()

def to_excel(df):
    """Convert dataframe to Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# Main App
st.title("💰 Brand Expense Tracker - Approval System")
st.markdown("---")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Navigation",
    [
        "📝 Submit Quotation",
        "⏳ Pending Approvals",
        "✅ Add Invoice & Receipt",
        "📊 All Expenses",
        "📈 Reports & Summary"
    ]
)

# Page 1: Submit Quotation (Request)
if page == "📝 Submit Quotation":
    st.header("📝 Submit Expense Quotation")
    st.info("👉 Submit your expense request. It will go to approval first.")
    
    with st.form("quotation_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Expense Date", value=date.today())
            brand = st.selectbox("Brand", BRANDS)
            category = st.selectbox("Category", CATEGORIES)
        
        with col2:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
            requested_by = st.text_input("Your Name", placeholder="Who is requesting?")
        
        description = st.text_area("Description / Justification", placeholder="Why is this expense needed?")
        
        submitted = st.form_submit_button("Submit for Approval", use_container_width=True, type="primary")
        
        if submitted:
            if amount > 0 and requested_by.strip():
                with st.spinner("Submitting quotation..."):
                    expense_id, error = add_quotation(expense_date, brand, category, amount, description, requested_by)
                    if expense_id:
                        st.success(f"✅ Quotation #{expense_id} submitted for approval!")
                        st.info(f"📋 Expense of ₹{amount:,.2f} for {brand} is now pending approval.")
                        st.balloons()
                    else:
                        st.error(f"❌ Error submitting quotation: {error}")
                        st.info("💡 Tip: Try refreshing the page or contact support if this persists.")
            else:
                st.error("⚠️ Please enter amount and your name!")

# Page 2: Pending Approvals (For Managers)
elif page == "⏳ Pending Approvals":
    st.header("⏳ Pending Approvals")
    st.info("👉 Review and approve/reject expense requests")
    
    df = get_pending_approvals()
    
    if not df.empty:
        st.subheader(f"📋 {len(df)} Pending Request(s)")
        
        for idx, row in df.iterrows():
            with st.expander(f"🆔 #{row['id']} - {row['brand']} - ₹{row['amount']:,.2f} - {row['requested_by']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Details:**")
                    st.write(f"**Date:** {row['date']}")
                    st.write(f"**Brand:** {row['brand']}")
                    st.write(f"**Category:** {row['category']}")
                    st.write(f"**Amount:** ₹{row['amount']:,.2f}")
                    st.write(f"**Requested By:** {row['requested_by']}")
                    st.write(f"**Submitted:** {row['created_at']}")
                
                with col2:
                    st.write("**Description:**")
                    st.write(row['description'] if row['description'] else "No description provided")
                
                st.markdown("---")
                
                # Approval actions
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    approver_name = st.text_input(f"Your Name (Approver)", key=f"approver_{row['id']}")
                    if st.button(f"✅ Approve", key=f"approve_{row['id']}", type="primary"):
                        if approver_name.strip():
                            success, error = approve_expense(row['id'], approver_name)
                            if success:
                                st.success(f"✅ Approved! Expense #{row['id']} can now proceed to invoice.")
                                st.rerun()
                            else:
                                st.error(f"Error approving: {error}")
                        else:
                            st.error("Please enter your name")
                
                with col_reject:
                    rejection_reason = st.text_input(f"Rejection Reason", key=f"reason_{row['id']}")
                    if st.button(f"❌ Reject", key=f"reject_{row['id']}", type="secondary"):
                        if approver_name.strip() and rejection_reason.strip():
                            success, error = reject_expense(row['id'], approver_name, rejection_reason)
                            if success:
                                st.warning(f"❌ Rejected! Expense #{row['id']} has been declined.")
                                st.rerun()
                            else:
                                st.error(f"Error rejecting: {error}")
                        else:
                            st.error("Please enter your name and rejection reason")
    else:
        st.success("🎉 No pending approvals! All caught up.")

# Page 3: Add Invoice & Receipt
elif page == "✅ Add Invoice & Receipt":
    st.header("✅ Add Invoice & Receipt")
    st.info("👉 Add invoice details and upload receipt for approved expenses")
    
    df = get_approved_without_invoice()
    
    if not df.empty:
        st.subheader(f"📋 {len(df)} Approved Expense(s) Awaiting Invoice")
        
        # Select expense
        expense_options = {
            f"#{row['id']} - {row['brand']} - ₹{row['amount']:,.2f} - {row['requested_by']}": row['id'] 
            for idx, row in df.iterrows()
        }
        
        selected_expense = st.selectbox("Select Approved Expense", options=list(expense_options.keys()))
        
        if selected_expense:
            expense_id = expense_options[selected_expense]
            expense = get_expense_by_id(expense_id)
            
            if expense is not None:
                # Show expense details
                with st.expander("📄 Expense Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Date:** {expense['date']}")
                        st.write(f"**Brand:** {expense['brand']}")
                        st.write(f"**Category:** {expense['category']}")
                        st.write(f"**Amount:** ₹{expense['amount']:,.2f}")
                    
                    with col2:
                        st.write(f"**Requested By:** {expense['requested_by']}")
                        st.write(f"**Approved By:** {expense['approved_by']}")
                        st.write(f"**Approval Date:** {expense['approval_date']}")
                    
                    st.write(f"**Description:** {expense['description']}")
                
                # Invoice form
                st.markdown("---")
                with st.form(f"invoice_form_{expense_id}"):
                    st.subheader("📝 Add Invoice Details")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        invoice_number = st.text_input("Invoice Number", placeholder="INV-2024-001")
                    with col2:
                        invoice_date = st.date_input("Invoice Date", value=date.today())
                    
                    receipt_file = st.file_uploader(
                        "Upload Receipt/Invoice Image", 
                        type=['png', 'jpg', 'jpeg'],
                        help="Upload a photo of the receipt/invoice"
                    )
                    
                    submit_invoice = st.form_submit_button("✅ Submit Invoice & Complete", type="primary")
                    
                    if submit_invoice:
                        if invoice_number.strip() and receipt_file:
                            try:
                                receipt_image = Image.open(receipt_file)
                                success, error = add_invoice_and_receipt(
                                    expense_id, 
                                    invoice_number, 
                                    invoice_date, 
                                    receipt_image, 
                                    receipt_file.name
                                )
                                if success:
                                    st.success(f"✅ Invoice added! Expense #{expense_id} is now COMPLETED!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(f"Error adding invoice: {error}")
                            except Exception as e:
                                st.error(f"Error processing image: {str(e)}")
                        else:
                            st.error("Please provide invoice number and upload receipt image")
    else:
        st.info("📭 No approved expenses awaiting invoice. All completed!")

# Page 4: All Expenses
elif page == "📊 All Expenses":
    st.header("📊 All Expenses")
    
    # Status filter
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All"] + STATUSES)
    
    df = get_all_expenses(status_filter)
    
    if not df.empty:
        # Additional filters
        with col2:
            brand_filter = st.multiselect("Filter by Brand", options=df['brand'].unique())
        with col3:
            category_filter = st.multiselect("Filter by Category", options=df['category'].unique())
        
        # Apply filters
        filtered_df = df.copy()
        if brand_filter:
            filtered_df = filtered_df[filtered_df['brand'].isin(brand_filter)]
        if category_filter:
            filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Expenses", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("Total Count", len(filtered_df))
        col3.metric("Completed", len(filtered_df[filtered_df['status'] == 'Completed']))
        col4.metric("Pending", len(filtered_df[filtered_df['status'] == 'Pending']))
        
        st.markdown("---")
        
        # Display data
        display_df = filtered_df[[
            'id', 'date', 'brand', 'category', 'amount', 'status', 
            'requested_by', 'approved_by', 'invoice_number'
        ]].copy()
        
        # Color code status
        def highlight_status(row):
            if row['status'] == 'Completed':
                return ['background-color: #d4edda'] * len(row)
            elif row['status'] == 'Approved':
                return ['background-color: #d1ecf1'] * len(row)
            elif row['status'] == 'Pending':
                return ['background-color: #fff3cd'] * len(row)
            elif row['status'] == 'Rejected':
                return ['background-color: #f8d7da'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            display_df.style.apply(highlight_status, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # View receipt
        st.markdown("---")
        st.subheader("🖼️ View Receipt")
        receipt_ids = filtered_df[filtered_df['status'] == 'Completed']['id'].tolist()
        if receipt_ids:
            selected_id = st.selectbox("Select Expense to View Receipt", receipt_ids)
            if selected_id:
                receipt_data = get_receipt_image(selected_id)
                if receipt_data and receipt_data[0]:
                    st.image(receipt_data[0], caption=f"Receipt: {receipt_data[1]}", use_container_width=True)
                else:
                    st.info("No receipt image available")
        
        # Export
        excel_data = to_excel(filtered_df)
        st.download_button(
            label="📥 Download as Excel",
            data=excel_data,
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No expenses found")

# Page 5: Reports & Summary
elif page == "📈 Reports & Summary":
    st.header("📈 Reports & Summary")
    
    # Status summary
    st.subheader("📊 Summary by Status")
    status_df = get_summary_by_status()
    if not status_df.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            display_status_df = status_df.copy()
            display_status_df['total_amount'] = display_status_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_status_df, use_container_width=True, hide_index=True)
        with col2:
            total = status_df['total_amount'].sum()
            st.metric("Grand Total", f"₹{total:,.2f}")
    
    st.markdown("---")
    
    # Brand summary (Completed only)
    st.subheader("🏢 Brand-wise Summary (Completed Expenses)")
    brand_df = get_brand_summary("Completed")
    if not brand_df.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            display_brand_df = brand_df.copy()
            display_brand_df['total_amount'] = display_brand_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_brand_df, use_container_width=True, hide_index=True)
        with col2:
            total = brand_df['total_amount'].sum()
            st.metric("Total Completed", f"₹{total:,.2f}")

# Footer
st.markdown("---")
st.markdown("💡 **Workflow:** Submit Quotation → Approval → Add Invoice & Receipt → Completed")
