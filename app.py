import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
from PIL import Image
import base64

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker - Approval System",
    page_icon="💰",
    layout="wide"
)

# Database setup with proper connection handling
def get_connection():
    """Get database connection with timeout"""
    return sqlite3.connect('expenses.db', timeout=10.0, check_same_thread=False)

def init_db():
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

# Initialize database
init_db()

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

# Helper functions
def add_quotation(date, brand, category, amount, description, requested_by):
    """Add new expense quotation (request)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO expenses (date, brand, category, amount, description, requested_by, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        ''', (date, brand, category, amount, description, requested_by))
        conn.commit()
        expense_id = c.lastrowid
        return expense_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_expenses(status_filter=None):
    """Get all expenses with optional status filter"""
    conn = get_connection()
    try:
        if status_filter and status_filter != "All":
            df = pd.read_sql_query(
                "SELECT * FROM expenses WHERE status = ? ORDER BY created_at DESC", 
                conn, 
                params=(status_filter,)
            )
        else:
            df = pd.read_sql_query("SELECT * FROM expenses ORDER BY created_at DESC", conn)
        return df
    finally:
        conn.close()

def get_pending_approvals():
    """Get all pending approval requests"""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM expenses WHERE status = 'Pending' ORDER BY created_at DESC", 
            conn
        )
        return df
    finally:
        conn.close()

def get_approved_without_invoice():
    """Get approved expenses that need invoice"""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM expenses WHERE status = 'Approved' ORDER BY approval_date DESC", 
            conn
        )
        return df
    finally:
        conn.close()

def approve_expense(expense_id, approved_by):
    """Approve an expense request"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE expenses 
            SET status = 'Approved', 
                approved_by = ?, 
                approval_date = ?,
                updated_at = ?
            WHERE id = ?
        ''', (approved_by, datetime.now(), datetime.now(), expense_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def reject_expense(expense_id, approved_by, reason):
    """Reject an expense request"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE expenses 
            SET status = 'Rejected', 
                approved_by = ?, 
                approval_date = ?,
                rejection_reason = ?,
                updated_at = ?
            WHERE id = ?
        ''', (approved_by, datetime.now(), reason, datetime.now(), expense_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_invoice_and_receipt(expense_id, invoice_number, invoice_date, receipt_image, receipt_filename):
    """Add invoice details and receipt image to approved expense"""
    conn = get_connection()
    c = conn.cursor()
    
    try:
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
        ''', (invoice_number, invoice_date, img_binary, receipt_filename, datetime.now(), expense_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_expense_by_id(expense_id):
    """Get single expense details"""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM expenses WHERE id = ?", conn, params=(expense_id,))
        if not df.empty:
            return df.iloc[0]
        return None
    finally:
        conn.close()

def get_receipt_image(expense_id):
    """Get receipt image for an expense"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT receipt_image, receipt_filename FROM expenses WHERE id = ?", (expense_id,))
        result = c.fetchone()
        return result
    finally:
        conn.close()

def get_summary_by_status():
    """Get summary grouped by status"""
    conn = get_connection()
    try:
        query = """
            SELECT 
                status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM expenses
            GROUP BY status
        """
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

def get_brand_summary(status_filter="Completed"):
    """Get brand-wise summary for completed expenses"""
    conn = get_connection()
    try:
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
        return df
    finally:
        conn.close()

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
            if amount > 0 and requested_by:
                expense_id = add_quotation(expense_date, brand, category, amount, description, requested_by)
                st.success(f"✅ Quotation #{expense_id} submitted for approval!")
                st.info(f"📋 Expense of ₹{amount:,.2f} for {brand} is now pending approval.")
                st.balloons()
            else:
                st.error("Please enter amount and your name!")

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
                        if approver_name:
                            approve_expense(row['id'], approver_name)
                            st.success(f"✅ Approved! Expense #{row['id']} can now proceed to invoice.")
                            st.rerun()
                        else:
                            st.error("Please enter your name")
                
                with col_reject:
                    rejection_reason = st.text_input(f"Rejection Reason", key=f"reason_{row['id']}")
                    if st.button(f"❌ Reject", key=f"reject_{row['id']}", type="secondary"):
                        if approver_name and rejection_reason:
                            reject_expense(row['id'], approver_name, rejection_reason)
                            st.warning(f"❌ Rejected! Expense #{row['id']} has been declined.")
                            st.rerun()
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
                    type=['png', 'jpg', 'jpeg', 'pdf'],
                    help="Upload a photo or PDF of the receipt/invoice"
                )
                
                submit_invoice = st.form_submit_button("✅ Submit Invoice & Complete", type="primary")
                
                if submit_invoice:
                    if invoice_number and receipt_file:
                        # Process image
                        if receipt_file.type in ['image/png', 'image/jpeg', 'image/jpg']:
                            receipt_image = Image.open(receipt_file)
                            add_invoice_and_receipt(
                                expense_id, 
                                invoice_number, 
                                invoice_date, 
                                receipt_image, 
                                receipt_file.name
                            )
                            st.success(f"✅ Invoice added! Expense #{expense_id} is now COMPLETED!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Please upload an image file (PNG/JPG)")
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
