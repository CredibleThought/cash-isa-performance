import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from isa_calculator import calculate_portfolio_growth

st.set_page_config(page_title="ISA Comparison Tool", layout="wide")



# Buy Me a Coffee Button
st.sidebar.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Cookie&display=swap" rel="stylesheet">
    <a href="https://buymeacoffee.com/stevefernandes" target="_blank" style="text-decoration: none;">
        <div style="
            background-color: #FFDD00;
            color: #000000;
            padding: 10px 20px;
            border-radius: 5px;
            text-align: center;
            font-family: 'Cookie', cursive;
            font-size: 28px;
            margin-bottom: 20px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            Buy me a coffee ☕
        </div>
    </a>
    """,
    unsafe_allow_html=True
)

# Sidebar Inputs
st.sidebar.header("Investment Settings")

# Date Range Selection
min_date = datetime(1999, 4, 6).date()
max_date = datetime(2026, 4, 5).date() # Updated to match data end

st.sidebar.subheader("Time Period")
start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)

today = datetime.now().date()
default_end = min(today, max_date)
end_date = st.sidebar.date_input("End Date", default_end, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.sidebar.error("Start Date must be before End Date.")

st.title(f"Cash ISA Performance Comparison ({start_date.year} - {end_date.year})")
st.markdown(f"""
Compare the performance of a **Best Rate Cash ISA** vs an **Average Rate Cash ISA** over time.
Data source: Historical interest rates from {start_date.year} to {end_date.year}.
""")

initial_investment = st.sidebar.number_input("Initial Investment (£)", min_value=0.0, value=1000.0, step=100.0)

st.sidebar.subheader("Recurring Payments")
recurring_amount = st.sidebar.number_input("Recurring Amount (£)", min_value=0.0, value=0.0, step=50.0)
frequency = st.sidebar.selectbox("Payment Frequency", ["None", "Weekly", "Monthly", "Annually"])

st.sidebar.subheader("Interest Settings")
interest_freq = st.sidebar.selectbox("Interest Paid", ["Daily", "Monthly", "Quarterly", "Annually (Tax Year End)"], index=3)

st.sidebar.subheader("Lump Sums")
st.sidebar.markdown("Add irregular lump sums below.")
# Use a simple text area for lump sums
lump_sum_text = st.sidebar.text_area("Format: YYYY-MM-DD, Amount (one per line)", height=100, help="Example:\n2005-01-01, 1000\n2010-06-30, 500")

# Parse Lump Sums
lump_sums = []
if lump_sum_text:
    for line in lump_sum_text.split('\n'):
        parts = line.split(',')
        if len(parts) == 2:
            try:
                date_str = parts[0].strip()
                amount = float(parts[1].strip())
                lump_sums.append((date_str, amount))
            except ValueError:
                pass

# Inflation Settings
st.sidebar.subheader("Inflation Adjustment")
inflation_type = st.sidebar.radio("Adjust for Inflation", ["None", "RPI", "CPI"], index=0)

# Calculations
if st.button("Calculate Performance", type="primary"):
    with st.spinner("Calculating..."):
        # Calculate for Best Rate
        df_best = calculate_portfolio_growth(
            initial_investment, recurring_amount, frequency, lump_sums, 'Best Rate', start_date, end_date, inflation_type, interest_freq
        )
        
        # Calculate for Average Rate
        df_avg = calculate_portfolio_growth(
            initial_investment, recurring_amount, frequency, lump_sums, 'Average Rate', start_date, end_date, inflation_type, interest_freq
        )

        # Calculate for Lowest Rate
        df_low = calculate_portfolio_growth(
            initial_investment, recurring_amount, frequency, lump_sums, 'Lowest Rate', start_date, end_date, inflation_type, interest_freq
        )
        
        # Metrics
        # Use 'Real Balance' if inflation is selected, otherwise 'Balance' (which are same if None)
        # Actually, let's always use 'Real Balance' column as it defaults to Balance if None
        final_best = df_best['Real Balance'].iloc[-1]
        final_avg = df_avg['Real Balance'].iloc[-1]
        final_low = df_low['Real Balance'].iloc[-1]
        total_invested = df_best['Total Invested'].iloc[-1]
        
        # If inflation adjusted, Total Invested should probably also be real? 
        # For now, let's keep Total Invested as Nominal Cash Put In, but show Final Value in Real Terms.
        # This shows "Buying Power" vs "Cash Put In".
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invested (Nominal)", f"£{total_invested:,.2f}")
        
        val_label = "Value" if inflation_type == "None" else f"Real Value ({inflation_type})"
        
        def format_delta(val):
            return f"-£{abs(val):,.2f}" if val < 0 else f"£{val:,.2f}"

        col2.metric(f"Best Rate {val_label}", f"£{final_best:,.2f}", delta=format_delta(final_best - total_invested))
        col3.metric(f"Avg Rate {val_label}", f"£{final_avg:,.2f}", delta=format_delta(final_avg - total_invested))
        col4.metric(f"Lowest Rate {val_label}", f"£{final_low:,.2f}", delta=format_delta(final_low - total_invested))
        
        # Plotting
        # Set style to dark background for this plot
        plt.style.use('dark_background')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Ensure figure and axes background are black (though style.use should handle most)
        fig.patch.set_facecolor('black')
        ax.set_facecolor('black')
        
        ax.plot(df_best['Date'], df_best['Real Balance'], label=f'Best Rate ({val_label})', color='#00ff00', linewidth=2) # Bright green
        ax.plot(df_avg['Date'], df_avg['Real Balance'], label=f'Average Rate ({val_label})', color='#00ccff', linewidth=2) # Bright blue
        ax.plot(df_low['Date'], df_low['Real Balance'], label=f'Lowest Rate ({val_label})', color='#ff3333', linewidth=2) # Red
        ax.plot(df_best['Date'], df_best['Total Invested'], label='Total Invested (Nominal)', color='#CCCCCC', linestyle='--', alpha=0.7)
        
        ax.set_title(f"Portfolio {val_label} Over Time", color='white')
        ax.set_xlabel("Year", color='white')
        ax.set_ylabel(f"{val_label} (£)", color='white')
        
        # Tick colors
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        # Spines
        for spine in ax.spines.values():
            spine.set_color('white')
            
        legend = ax.legend(facecolor='black', edgecolor='white')
        plt.setp(legend.get_texts(), color='white')
        
        ax.grid(True, alpha=0.3, color='gray')
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter('£{x:1.0f}')
        
        st.pyplot(fig)
        
        # Data Table
        st.subheader("Yearly Breakdown (Tax Year)")
        
        def get_tax_year(d):
            if d.month < 4 or (d.month == 4 and d.day < 6):
                return f"{d.year-1}/{d.year}"
            else:
                return f"{d.year}/{d.year+1}"

        # Apply Tax Year grouping
        for df in [df_best, df_avg, df_low]:
            df['Tax Year'] = df['Date'].apply(get_tax_year)

        yearly_best = df_best.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Best Balance', 'Rate': 'Best Rate %'})
        yearly_avg = df_avg.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Avg Balance', 'Rate': 'Avg Rate %'})
        yearly_low = df_low.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Low Balance', 'Rate': 'Low Rate %'})
        
        # Get Inflation Rate from one of the DFs (e.g., df_best)
        yearly_inflation = df_best.groupby('Tax Year').last()[['Inflation Rate']].rename(columns={'Inflation Rate': f'{inflation_type} %'})
        
        # Get Total Invested for comparison
        yearly_invested = df_best.groupby('Tax Year').last()[['Total Invested']]
        
        if inflation_type != 'None':
            yearly_summary = pd.concat([yearly_best, yearly_avg, yearly_low, yearly_inflation, yearly_invested], axis=1)
            format_dict = {
                'Best Balance': '£{:,.2f}',
                'Avg Balance': '£{:,.2f}',
                'Low Balance': '£{:,.2f}',
                'Best Rate %': '{:.2f}%',
                'Avg Rate %': '{:.2f}%',
                'Low Rate %': '{:.2f}%',
                f'{inflation_type} %': '{:.2f}%',
                'Total Invested': '£{:,.2f}'
            }
        else:
            yearly_summary = pd.concat([yearly_best, yearly_avg, yearly_low, yearly_invested], axis=1)
            format_dict = {
                'Best Balance': '£{:,.2f}',
                'Avg Balance': '£{:,.2f}',
                'Low Balance': '£{:,.2f}',
                'Best Rate %': '{:.2f}%',
                'Avg Rate %': '{:.2f}%',
                'Low Rate %': '{:.2f}%',
                'Total Invested': '£{:,.2f}'
            }
        
        # Center headers
        styles = [
            dict(selector="th", props=[("text-align", "center")]),
            dict(selector="td", props=[("text-align", "center")])
        ]
        
        def color_negative_performance(row):
            invested = row['Total Invested']
            colors = [''] * len(row)
            
            # Helper to set color
            def set_color(val, threshold):
                if val < threshold:
                    return 'color: red'
                return ''
            
            # Map column names to indices
            col_indices = {name: i for i, name in enumerate(row.index)}
            
            # Balance checks
            if 'Best Balance' in col_indices:
                colors[col_indices['Best Balance']] = set_color(row['Best Balance'], invested)
            if 'Avg Balance' in col_indices:
                colors[col_indices['Avg Balance']] = set_color(row['Avg Balance'], invested)
            if 'Low Balance' in col_indices:
                colors[col_indices['Low Balance']] = set_color(row['Low Balance'], invested)
            
            # Rate checks
            inflation_col = f'{inflation_type} %'
            if inflation_type != 'None' and inflation_col in col_indices:
                inflation_val = row[inflation_col]
                if 'Best Rate %' in col_indices:
                    colors[col_indices['Best Rate %']] = set_color(row['Best Rate %'], inflation_val)
                if 'Avg Rate %' in col_indices:
                    colors[col_indices['Avg Rate %']] = set_color(row['Avg Rate %'], inflation_val)
                if 'Low Rate %' in col_indices:
                    colors[col_indices['Low Rate %']] = set_color(row['Low Rate %'], inflation_val)
                
            return colors

        st.dataframe(yearly_summary.style.format(format_dict).set_table_styles(styles).apply(color_negative_performance, axis=1), height=450)

else:
    st.info("Adjust settings in the sidebar and click 'Calculate Performance' to see the results.")
