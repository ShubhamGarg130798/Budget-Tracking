import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io

# Page configuration
st.set_page_config(
    page_title="Brand Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Database setup
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            added_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Brand list - Your 18 Lending Brands
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

def get_brand_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT 
            brand,
            SUM(amount) as total_amount,
            COUNT(*) as transaction_count
        FROM expenses
        GROUP BY brand
        ORDER BY total_amount DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_month_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(amount) as total_amount,
            COUNT(*) as transaction_count
        FROM expenses
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_brand_month_matrix():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT 
            brand,
            strftime('%Y-%m', date) as month,
            SUM(amount) as amount
        FROM expenses
        GROUP BY brand, strftime('%Y-%m', date)
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        pivot_df = df.pivot(index='brand', columns='month', values='amount')
        pivot_df = pivot_df.fillna(0)
        pivot_df['Total'] = pivot_df.sum(axis=1)
        return pivot_df
    return pd.DataFrame()

def get_category_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT 
            category,
            SUM(amount) as total_amount,
            COUNT(*) as transaction_count
        FROM expenses
        GROUP BY category
        ORDER BY total_amount DESC
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

# Main App
st.title("💰 Brand Expense Tracker")
st.markdown("---")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Add Expense", "View All Expenses", "Brand Summary", "Month Summary", "Brand-Month Matrix", "Category Summary"]
)

# Page 1: Add Expense
if page == "Add Expense":
    st.header("➕ Add New Expense")
    
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Date", value=date.today())
            brand = st.selectbox("Brand", BRANDS)
            category = st.selectbox("Category", CATEGORIES)
        
        with col2:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
            added_by = st.text_input("Added By", placeholder="Your name")
        
        description = st.text_area("Description", placeholder="Enter expense details...")
        
        submitted = st.form_submit_button("Add Expense", use_container_width=True, type="primary")
        
        if submitted:
            if amount > 0 and added_by:
                add_expense(expense_date, brand, category, amount, description, added_by)
                st.success(f"✅ Expense of ₹{amount:,.2f} added for {brand}!")
                st.balloons()
            else:
                st.error("Please enter amount and your name!")

# Page 2: View All Expenses
elif page == "View All Expenses":
    st.header("📋 All Expenses")
    
    df = get_all_expenses()
    
    if not df.empty:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            brand_filter = st.multiselect("Filter by Brand", options=df['brand'].unique(), default=None)
        with col2:
            category_filter = st.multiselect("Filter by Category", options=df['category'].unique(), default=None)
        with col3:
            date_range = st.date_input("Filter by Date Range", value=[], key="date_filter")
        
        # Apply filters
        filtered_df = df.copy()
        if brand_filter:
            filtered_df = filtered_df[filtered_df['brand'].isin(brand_filter)]
        if category_filter:
            filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
        if len(date_range) == 2:
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['date']).dt.date >= date_range[0]) &
                (pd.to_datetime(filtered_df['date']).dt.date <= date_range[1])
            ]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Expenses", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("Transaction Count", len(filtered_df))
        col3.metric("Average Amount", f"₹{filtered_df['amount'].mean():,.2f}")
        
        st.markdown("---")
        
        # Display data
        display_df = filtered_df[['date', 'brand', 'category', 'amount', 'description', 'added_by']].copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export button
        excel_data = to_excel(filtered_df)
        st.download_button(
            label="📥 Download as Excel",
            data=excel_data,
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Delete functionality
        st.markdown("---")
        with st.expander("🗑️ Delete Expense"):
            expense_to_delete = st.selectbox(
                "Select expense to delete",
                options=filtered_df['id'].tolist(),
                format_func=lambda x: f"ID: {x} - {filtered_df[filtered_df['id']==x]['brand'].values[0]} - ₹{filtered_df[filtered_df['id']==x]['amount'].values[0]:,.2f}"
            )
            if st.button("Delete Selected Expense", type="secondary"):
                delete_expense(expense_to_delete)
                st.success("Expense deleted!")
                st.rerun()
    else:
        st.info("No expenses recorded yet. Add your first expense!")

# Page 3: Brand Summary
elif page == "Brand Summary":
    st.header("🏢 Brand-wise Summary")
    
    df = get_brand_summary()
    
    if not df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Brand Expenses")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Total")
            total = df['total_amount'].sum()
            st.metric("Grand Total", f"₹{total:,.2f}")
            
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Brand Summary",
            data=excel_data,
            file_name=f"brand_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data available yet.")

# Page 4: Month Summary
elif page == "Month Summary":
    st.header("📅 Month-wise Summary")
    
    df = get_month_summary()
    
    if not df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Monthly Expenses")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Total")
            total = df['total_amount'].sum()
            st.metric("Grand Total", f"₹{total:,.2f}")
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Month Summary",
            data=excel_data,
            file_name=f"month_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data available yet.")

# Page 5: Brand-Month Matrix
elif page == "Brand-Month Matrix":
    st.header("📊 Brand vs Month Matrix")
    
    df = get_brand_month_matrix()
    
    if not df.empty:
        st.subheader("Consolidated View")
        
        # Format for display
        display_df = df.copy()
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.0f}")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Matrix",
            data=excel_data,
            file_name=f"brand_month_matrix_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data available yet.")

# Page 6: Category Summary
elif page == "Category Summary":
    st.header("📂 Category-wise Summary")
    
    df = get_category_summary()
    
    if not df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Category Expenses")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Total")
            total = df['total_amount'].sum()
            st.metric("Grand Total", f"₹{total:,.2f}")
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Category Summary",
            data=excel_data,
            file_name=f"category_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data available yet.")

# Footer
st.markdown("---")
st.markdown("💡 **Tip:** Use filters to analyze specific brands or time periods")
