import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from isa_calculator import calculate_portfolio_growth, get_rates_df
from decimal import Decimal
import os


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

# Custom Rates
st.sidebar.subheader("Custom Rates")
use_custom_rates = st.sidebar.checkbox("Show Custom Scenario", value=False)
custom_rates_df_final = None

if use_custom_rates:
    with st.sidebar.expander("Edit Custom Rates"):
        default_rates_df = get_rates_df()
        # Create a simplified view for editing: Tax Year and a Rate column initialized with Best Rate
        edit_df = default_rates_df[['Tax Year', 'Best Rate']].copy()
        edit_df = edit_df.rename(columns={'Best Rate': 'Custom Rate'})
        
        # File Uploader
        uploaded_file = st.file_uploader("Upload Custom Rates (CSV)", type="csv")
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                if 'Tax Year' in uploaded_df.columns and 'Custom Rate' in uploaded_df.columns:
                    # Merge or replace. Since we want strict tax years, let's merge on Tax Year or just replace values
                    # Ideally, we ensure the Tax Years match our default list.
                    # Simple approach: Merge uploaded 'Custom Rate' into clean `edit_df`
                    
                    # Ensure matching types/format if possible, or just merge
                    temp_df = pd.merge(edit_df[['Tax Year']], uploaded_df[['Tax Year', 'Custom Rate']], on='Tax Year', how='left')
                    
                    # Fill missing with default best rate if any tax years missing in upload?
                    # Or just use the defaults from edit_df where missing. 
                    # Let's check for missing values after merge
                    
                    # Actually, let's just use update if we set index
                    edit_df.set_index('Tax Year', inplace=True)
                    uploaded_df_indexed = uploaded_df.set_index('Tax Year')
                    edit_df.update(uploaded_df_indexed)
                    edit_df.reset_index(inplace=True)
                    
                    st.success("Custom Rates loaded successfully!")
                else:
                    st.error("CSV must contain 'Tax Year' and 'Custom Rate' columns.")
            except Exception as e:
                st.error(f"Error loading CSV: {e}")
        
        edited_df = st.data_editor(
            edit_df, 
            num_rows="fixed",
            hide_index=True,
            column_config={
                "Tax Year": st.column_config.TextColumn(
                    "Tax Year",
                    disabled=True
                ),
                "Custom Rate": st.column_config.NumberColumn(
                    "Custom Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    format="%.2f%%"
                )
            },
            key="custom_rates_editor"
        )
        
        # Save to Disk (Local Path)
        st.write("---")
        st.write("**Save to Local Disk**")
        default_filename = os.path.join(os.getcwd(), "custom_rates.csv")
        save_path = st.text_input("File Path (e.g. C:/data/my_rates.csv)", value=default_filename)
        if st.button("Save to Disk"):
            if save_path:
                try:
                    # Ensure directory exists or let pandas/OS handle error if not
                    # For simplicity, just try to save
                    edited_df.to_csv(save_path, index=False)
                    st.success(f"Successfully saved to {save_path}")
                except Exception as e:
                    st.error(f"Error saving file: {e}")
            else:
                st.error("Please enter a file path.")
        
        # Merge back into the full rates structure to pass to calculator
        # We need the other columns (Dates, Allowance) from default_rates_df
        # We will map the edited 'Custom Rate' back to a 'Custom Rate' column in the full df
        custom_rates_df_final = default_rates_df.copy()
        # Join on Tax Year to get the updated rates
        custom_rates_df_final['Custom Rate'] = edited_df['Custom Rate']

# Calculations
if st.button("Calculate Performance", type="primary"):
    with st.spinner("Calculating..."):
        # Calculate for Best Rate
        df_best = calculate_portfolio_growth(
            Decimal(initial_investment), Decimal(recurring_amount), frequency, lump_sums, 'Best Rate', start_date, end_date, inflation_type, interest_freq
        )
        
        # Calculate for Average Rate
        df_avg = calculate_portfolio_growth(
            Decimal(initial_investment), Decimal(recurring_amount), frequency, lump_sums, 'Average Rate', start_date, end_date, inflation_type, interest_freq
        )

        # Calculate for Lowest Rate
        df_low = calculate_portfolio_growth(
            Decimal(initial_investment), Decimal(recurring_amount), frequency, lump_sums, 'Lowest Rate', start_date, end_date, inflation_type, interest_freq
        )
        
        df_custom = None
        if use_custom_rates and custom_rates_df_final is not None:
             df_custom = calculate_portfolio_growth(
                Decimal(initial_investment), Decimal(recurring_amount), frequency, lump_sums, 'Custom Rate', start_date, end_date, inflation_type, interest_freq, custom_rates_df=custom_rates_df_final
            )
        
        # Metrics
        # Use 'Real Balance' if inflation is selected, otherwise 'Balance' (which are same if None)
        # Actually, let's always use 'Real Balance' column as it defaults to Balance if None
        final_best = df_best['Real Balance'].iloc[-1]
        final_avg = df_avg['Real Balance'].iloc[-1]
        final_low = df_low['Real Balance'].iloc[-1]
        
        final_custom = df_custom['Real Balance'].iloc[-1] if df_custom is not None else None
        
        total_invested = df_best['Total Invested'].iloc[-1]
        
        # If inflation adjusted, Total Invested should probably also be real? 
        # For now, let's keep Total Invested as Nominal Cash Put In, but show Final Value in Real Terms.
        # This shows "Buying Power" vs "Cash Put In".
        
        cols = st.columns(5) if df_custom is not None else st.columns(4)
        cols[0].metric("Total Invested (Nominal)", f"£{total_invested:,.2f}")
        
        val_label = "Value" if inflation_type == "None" else f"Real Value ({inflation_type})"
        
        def format_delta(val):
            return f"-£{abs(val):,.2f}" if val < 0 else f"£{val:,.2f}"

        cols[1].metric(f"Best Rate {val_label}", f"£{final_best:,.2f}", delta=format_delta(final_best - total_invested))
        cols[2].metric(f"Avg Rate {val_label}", f"£{final_avg:,.2f}", delta=format_delta(final_avg - total_invested))
        cols[3].metric(f"Lowest Rate {val_label}", f"£{final_low:,.2f}", delta=format_delta(final_low - total_invested))
        
        if df_custom is not None:
             cols[4].metric(f"Custom Rate {val_label}", f"£{final_custom:,.2f}", delta=format_delta(final_custom - total_invested))
        
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
        
        if df_custom is not None:
             ax.plot(df_custom['Date'], df_custom['Real Balance'], label=f'Custom Rate ({val_label})', color='#ffff00', linewidth=2, linestyle='--') # Yellow dashed

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
        ax.yaxis.set_major_formatter('£{x:1.2f}')
        
        st.pyplot(fig)
        
        # Data Table
        st.subheader("Yearly Breakdown (Tax Year)")
        
        def get_tax_year(d):
            if d.month < 4 or (d.month == 4 and d.day < 6):
                return f"{d.year-1}/{d.year}"
            else:
                return f"{d.year}/{d.year+1}"

        # Apply Tax Year grouping
        # Apply Tax Year grouping
        dfs_to_process = [df_best, df_avg, df_low]
        if df_custom is not None:
            dfs_to_process.append(df_custom)
            
        for df in dfs_to_process:
            df['Tax Year'] = df['Date'].apply(get_tax_year)

        yearly_best = df_best.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Best Balance', 'Rate': 'Best Rate %'})
        yearly_avg = df_avg.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Avg Balance', 'Rate': 'Avg Rate %'})
        yearly_low = df_low.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Low Balance', 'Rate': 'Low Rate %'})
        
        try:
             yearly_custom = df_custom.groupby('Tax Year').last()[['Real Balance', 'Rate']].rename(columns={'Real Balance': 'Cust Balance', 'Rate': 'Cust Rate %'}) if df_custom is not None else None
        except Exception:
             # Fallback if something goes wrong with custom grouping
             yearly_custom = None

        # Get Inflation Rate from one of the DFs (e.g., df_best)
        # Instead of just taking the last value, we want the "Effective Rate" for the period.
        # Effective Rate = (EndIndex / StartIndex) - 1
        def calculate_effective_inflation(group):
            if group.empty:
                return 0.0
            start_idx = group.iloc[0]['Inflation Index']
            end_idx = group.iloc[-1]['Inflation Index']
            
            # If start_idx is 0 (shouldn't be), handle it
            if start_idx == 0:
                return 0.0
                
            # The group is daily records.
            # However, start_idx is the index AFTER the first day's inflation? 
            # Ideally we want index at START of period vs END of period.
            # But the 'Inflation Index' column is the accumulated index at that day.
            # So (End / Start) gives growth during the period EXCLUDING the very first day's previous state?
            # Actually, `Inflation Index` starts at 1.0.
            # If we take (Last / First), we get growth from Day 1 to Day N.
            # But we might miss the inflation applied ON Day 1 if First is Day 1 End.
            # But given daily compounding is tiny, (Last / First) is a decent approximation of "growth during this window".
            
            # To be more precise: 
            # Growth = Index_Last / Index_Day_Before_Group
            # But we don't have Day_Before easily.
            # Let's use (Last / First) * (1 + daily_rate_of_first)? No too complex.
            # Let's just use (Last / First) and normalize to annual if needed, but Tax Year is ~1 year.
            # So (Last / First - 1) * 100 should be close to the blended rate.
            
            ratio = float(end_idx / start_idx)
            return (ratio - 1) * 100

        # We need to map this calculation to the Tax Year groups
        yearly_inflation = df_best.groupby('Tax Year').apply(calculate_effective_inflation).to_frame(name=f'{inflation_type} %')
        
        # Get Total Invested for comparison
        yearly_invested = df_best.groupby('Tax Year').last()[['Total Invested']]
        
        dfs_to_concat = [yearly_best, yearly_avg, yearly_low]
        if yearly_custom is not None:
            dfs_to_concat.append(yearly_custom)
            
        if inflation_type != 'None':
            dfs_to_concat.append(yearly_inflation)
        
        dfs_to_concat.append(yearly_invested)
        
        yearly_summary = pd.concat(dfs_to_concat, axis=1)
        
        format_dict = {
            'Best Balance': '£{:,.2f}',
            'Avg Balance': '£{:,.2f}',
            'Low Balance': '£{:,.2f}',
            'Cust Balance': '£{:,.2f}',
            'Best Rate %': '{:.2f}%',
            'Avg Rate %': '{:.2f}%',
            'Low Rate %': '{:.2f}%',
            'Cust Rate %': '{:.2f}%',
            f'{inflation_type} %': '{:.2f}%',
            'Total Invested': '£{:,.2f}'
        }
        
        # Ensure all values are floats for consistent rounding and display
        for col in yearly_summary.columns:
            yearly_summary[col] = yearly_summary[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
            
        # Explicitly round to 2 decimal places for CSV export
        yearly_summary = yearly_summary.round(2)
        
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
            if 'Cust Balance' in col_indices:
                colors[col_indices['Cust Balance']] = set_color(row['Cust Balance'], invested)
            
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
                if 'Cust Rate %' in col_indices:
                    colors[col_indices['Cust Rate %']] = set_color(row['Cust Rate %'], inflation_val)
                
            return colors

        st.dataframe(yearly_summary.style.format(format_dict).set_table_styles(styles).apply(color_negative_performance, axis=1), height=450)

else:
    st.info("Adjust settings in the sidebar and click 'Calculate Performance' to see the results.")
