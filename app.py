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
    </style>
""", unsafe_allow_html=True)

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

# Brand list (customize this with your 18 brands)
BRANDS = [
    "FundoBaBa", "Salary Adda", "FastPaise", "Brand 4", "Brand 5", "Brand 6",
    "Brand 7", "Brand 8", "Brand 9", "Brand 10", "Brand 11", "Brand 12",
    "Brand 13", "Brand 14", "Brand 15", "Brand 16", "Brand 17", "Brand 18"
]

# Expense categories
CATEGORIES = [
    "Marketing", "Operations", "Salaries", "Technology", "Office Rent",
    "Utilities", "Travel", "Professional Fees", "Commission", "Interest", "Other"
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

def get_month_summary():
    conn = sqlite3.connect('expenses.db')
    query = """
        SELECT strftime('%Y-%m', date) as month,
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
        SELECT brand,
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

# Main App
st.title("💰 Brand Expense Tracker")
st.markdown("---")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "📌 Navigation",
    ["➕ Add Expense", "📊 Dashboard", "📋 View All Expenses", "🏢 Brand Summary", 
     "📅 Month Summary", "🔥 Brand-Month Matrix", "📂 Category Summary"]
)

# Remove emoji from page name for comparison
page_clean = page.split(" ", 1)[1] if " " in page else page

# Page 0: Dashboard
if page_clean == "Dashboard":
    st.header("📊 Dashboard Overview")
    
    df = get_all_expenses()
    
    if not df.empty:
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = df['amount'].sum()
        total_transactions = len(df)
        avg_transaction = df['amount'].mean()
        unique_brands = df['brand'].nunique()
        
        col1.metric("💵 Total Expenses", f"₹{total_expenses:,.2f}")
        col2.metric("📝 Total Transactions", f"{total_transactions:,}")
        col3.metric("📊 Average Transaction", f"₹{avg_transaction:,.2f}")
        col4.metric("🏢 Active Brands", f"{unique_brands}")
        
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
        
        st.markdown("---")
        
        # Row 3: Top Expenses Table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("💎 Top 10 Highest Expenses")
            top_expenses = get_top_expenses(10)
            if not top_expenses.empty:
                display_top = top_expenses.copy()
                display_top['amount'] = display_top['amount'].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(display_top, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("📊 Quick Stats")
            if not df.empty:
                max_expense = df['amount'].max()
                min_expense = df['amount'].min()
                median_expense = df['amount'].median()
                
                st.metric("Highest Expense", f"₹{max_expense:,.2f}")
                st.metric("Lowest Expense", f"₹{min_expense:,.2f}")
                st.metric("Median Expense", f"₹{median_expense:,.2f}")
        
    else:
        st.info("📌 No expenses recorded yet. Add your first expense to see the dashboard!")
        st.markdown("### 🚀 Quick Start Guide:")
        st.markdown("1. Navigate to **➕ Add Expense** to record your first expense")
        st.markdown("2. Add expenses for different brands and categories")
        st.markdown("3. Return to this dashboard to see visualizations")

# Page 1: Add Expense
elif page_clean == "Add Expense":
    st.header("➕ Add New Expense")
    
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("📅 Date", value=date.today())
            brand = st.selectbox("🏢 Brand", BRANDS)
            category = st.selectbox("📂 Category", CATEGORIES)
        
        with col2:
            amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
            added_by = st.text_input("👤 Added By", placeholder="Your name")
        
        description = st.text_area("📝 Description", placeholder="Enter expense details...")
        
        submitted = st.form_submit_button("✅ Add Expense", use_container_width=True, type="primary")
        
        if submitted:
            if amount > 0 and added_by:
                add_expense(expense_date, brand, category, amount, description, added_by)
                st.toast(f"✅ Expense of ₹{amount:,.2f} added successfully for {brand}!", icon="✅")
            else:
                st.error("⚠️ Please enter amount and your name!")

# Page 2: View All Expenses
elif page_clean == "View All Expenses":
    st.header("📋 All Expenses")
    
    df = get_all_expenses()
    
    if not df.empty:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            brand_filter = st.multiselect("🏢 Filter by Brand", options=df['brand'].unique(), default=None)
        with col2:
            category_filter = st.multiselect("📂 Filter by Category", options=df['category'].unique(), default=None)
        with col3:
            date_range = st.date_input("📅 Filter by Date Range", value=[], key="date_filter")
        
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
        col1.metric("💵 Total Expenses", f"₹{filtered_df['amount'].sum():,.2f}")
        col2.metric("📝 Transaction Count", len(filtered_df))
        col3.metric("📊 Average Amount", f"₹{filtered_df['amount'].mean():,.2f}")
        
        st.markdown("---")
        
        # Charts for filtered data
        if len(filtered_df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                # Brand distribution
                brand_dist = filtered_df.groupby('brand')['amount'].sum().reset_index()
                fig_brand = px.pie(
                    brand_dist,
                    values='amount',
                    names='brand',
                    title='📊 Expense Distribution by Brand'
                )
                fig_brand.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_brand, use_container_width=True)
            
            with col2:
                # Category distribution
                cat_dist = filtered_df.groupby('category')['amount'].sum().reset_index()
                fig_cat = px.pie(
                    cat_dist,
                    values='amount',
                    names='category',
                    title='📂 Expense Distribution by Category'
                )
                fig_cat.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_cat, use_container_width=True)
        
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
            if st.button("🗑️ Delete Selected Expense", type="secondary"):
                delete_expense(expense_to_delete)
                st.success("✅ Expense deleted successfully!")
                st.rerun()
    
    else:
        st.info("📌 No expenses recorded yet. Add your first expense!")

# Page 3: Brand Summary
elif page_clean == "Brand Summary":
    st.header("🏢 Brand-wise Summary")
    
    df = get_brand_summary()
    
    if not df.empty:
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Brand Expenses - Bar Chart")
            fig_bar = px.bar(
                df,
                x='brand',
                y='total_amount',
                color='total_amount',
                labels={'total_amount': 'Total Amount (₹)', 'brand': 'Brand'},
                color_continuous_scale='Viridis',
                text='total_amount'
            )
            fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            st.subheader("🍰 Brand Expenses - Pie Chart")
            fig_pie = px.pie(
                df,
                values='total_amount',
                names='brand',
                hole=0.3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        
        # Data table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Brand Expenses Data")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df['percentage'] = (df['total_amount'] / df['total_amount'].sum() * 100).apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("💰 Total")
            total = df['total_amount'].sum()
            st.metric("Grand Total", f"₹{total:,.2f}")
            st.metric("Number of Brands", len(df))
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Brand Summary",
            data=excel_data,
            file_name=f"brand_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📌 No data available yet.")

# Page 4: Month Summary
elif page_clean == "Month Summary":
    st.header("📅 Month-wise Summary")
    
    df = get_month_summary()
    
    if not df.empty:
        df_sorted = df.sort_values('month')
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Monthly Trend - Line Chart")
            fig_line = px.line(
                df_sorted,
                x='month',
                y='total_amount',
                markers=True,
                labels={'total_amount': 'Total Amount (₹)', 'month': 'Month'}
            )
            fig_line.update_traces(
                line_color='#2ecc71', 
                line_width=3, 
                marker=dict(size=10, color='#2ecc71')
            )
            fig_line.update_layout(height=400)
            st.plotly_chart(fig_line, use_container_width=True)
        
        with col2:
            st.subheader("📊 Monthly Trend - Bar Chart")
            fig_bar = px.bar(
                df_sorted,
                x='month',
                y='total_amount',
                color='total_amount',
                labels={'total_amount': 'Total Amount (₹)', 'month': 'Month'},
                color_continuous_scale='Blues',
                text='total_amount'
            )
            fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("---")
        
        # Area chart
        st.subheader("📉 Cumulative Monthly Expenses")
        df_sorted['cumulative_amount'] = df_sorted['total_amount'].cumsum()
        fig_area = px.area(
            df_sorted,
            x='month',
            y='cumulative_amount',
            labels={'cumulative_amount': 'Cumulative Amount (₹)', 'month': 'Month'}
        )
        fig_area.update_traces(line_color='#e74c3c', fillcolor='rgba(231,76,60,0.3)')
        st.plotly_chart(fig_area, use_container_width=True)
        
        st.markdown("---")
        
        # Data table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Monthly Expenses Data")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("💰 Statistics")
            total = df['total_amount'].sum()
            avg = df['total_amount'].mean()
            max_month = df.loc[df['total_amount'].idxmax()]
            
            st.metric("Grand Total", f"₹{total:,.2f}")
            st.metric("Monthly Average", f"₹{avg:,.2f}")
            st.metric("Highest Month", max_month['month'])
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Month Summary",
            data=excel_data,
            file_name=f"month_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📌 No data available yet.")

# Page 5: Brand-Month Matrix
elif page_clean == "Brand-Month Matrix":
    st.header("🔥 Brand vs Month Matrix")
    
    df = get_brand_month_matrix()
    
    if not df.empty:
        # Data table only
        st.subheader("📋 Consolidated View")
        display_df = df.copy()
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(display_df, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_all = df['Total'].sum()
            st.metric("Grand Total", f"₹{total_all:,.2f}")
        with col2:
            avg_brand = df['Total'].mean()
            st.metric("Average per Brand", f"₹{avg_brand:,.2f}")
        with col3:
            top_brand = df['Total'].idxmax()
            st.metric("Top Brand", top_brand)
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Matrix",
            data=excel_data,
            file_name=f"brand_month_matrix_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📌 No data available yet.")

# Page 6: Category Summary
elif page_clean == "Category Summary":
    st.header("📂 Category-wise Summary")
    
    df = get_category_summary()
    
    if not df.empty:
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Category Expenses - Bar Chart")
            fig_bar = px.bar(
                df,
                x='category',
                y='total_amount',
                color='total_amount',
                labels={'total_amount': 'Total Amount (₹)', 'category': 'Category'},
                color_continuous_scale='Oranges',
                text='total_amount'
            )
            fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            st.subheader("🍩 Category Expenses - Donut Chart")
            fig_donut = px.pie(
                df,
                values='total_amount',
                names='category',
                hole=0.5
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)
        
        st.markdown("---")
        
        # Horizontal bar chart
        st.subheader("📈 Category Expenses - Horizontal View")
        fig_h_bar = px.bar(
            df.sort_values('total_amount'),
            x='total_amount',
            y='category',
            orientation='h',
            color='total_amount',
            labels={'total_amount': 'Total Amount (₹)', 'category': 'Category'},
            color_continuous_scale='Teal',
            text='total_amount'
        )
        fig_h_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
        fig_h_bar.update_layout(showlegend=False, height=500)
        st.plotly_chart(fig_h_bar, use_container_width=True)
        
        st.markdown("---")
        
        # Data table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Category Expenses Data")
            display_df = df.copy()
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df['percentage'] = (df['total_amount'] / df['total_amount'].sum() * 100).apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("💰 Statistics")
            total = df['total_amount'].sum()
            top_category = df.iloc[0]
            
            st.metric("Grand Total", f"₹{total:,.2f}")
            st.metric("Categories", len(df))
            st.metric("Top Category", top_category['category'])
            st.metric("Top Amount", f"₹{top_category['total_amount']:,.2f}")
        
        # Export
        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download Category Summary",
            data=excel_data,
            file_name=f"category_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("📌 No data available yet.")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        💡 <b>Tip:</b> Use filters to analyze specific brands or time periods | 
        📊 Dashboard shows comprehensive visualizations | 
        📥 Export data to Excel from any page
    </div>
""", unsafe_allow_html=True)
