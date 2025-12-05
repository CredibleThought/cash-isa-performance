import pandas as pd
from datetime import datetime, timedelta
from rates_data import ISA_RATES
from inflation_data import INFLATION_RATES
from decimal import Decimal


def get_rates_df():
    """Converts the rates list to a DataFrame and parses dates."""
    df = pd.DataFrame(ISA_RATES)
    df['Start Date'] = pd.to_datetime(df['Start Date'])
    df['End Date'] = pd.to_datetime(df['End Date'])
    return df

def get_inflation_df():
    """Converts inflation rates to DataFrame."""
    return pd.DataFrame(INFLATION_RATES)

def calculate_portfolio_growth(initial_investment:Decimal, recurring_amount:Decimal, frequency:str, lump_sums:list, rate_type:str, start_date=None, end_date=None, inflation_type='None', interest_freq='Daily', custom_rates_df=None):
    """
    Calculates the daily balance of the portfolio, respecting ISA allowances.
    Optionally adjusts for inflation (Real Value).
    Handles different interest payment frequencies.
    """
    if custom_rates_df is not None:
        rates_df = custom_rates_df
    else:
        rates_df = get_rates_df()
        
    inflation_df = get_inflation_df()
    
    # Define date range
    if start_date is None:
        start_date = rates_df['Start Date'].min().date()
    if end_date is None:
        end_date = rates_df['End Date'].max().date()
        
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    
    date_range = pd.date_range(start=start_ts, end=end_ts, freq='D')
    
    # Build Inflation Index
    inflation_map = inflation_df.set_index('Year')[inflation_type].to_dict() if inflation_type != 'None' else {}
    
    # Initialize variables
    balance = Decimal(0.0)
    total_invested = Decimal(0.0)
    pending_interest = Decimal(0.0)
    
    # Inflation Index tracking
    current_inflation_index = Decimal(1.0)
    
    records = []
    
    # Pre-process lump sums
    lump_sum_map = {}
    for date_str, amount in lump_sums:
        try:
            d = pd.to_datetime(date_str).date()
            lump_sum_map[d] = lump_sum_map.get(d, 0) + amount
        except:
            pass

    # Payment scheduling
    next_payment_date = start_ts
    if frequency == 'Weekly':
        next_payment_date += timedelta(weeks=1)
    elif frequency == 'Monthly':
        next_payment_date += pd.DateOffset(months=1)
    elif frequency == 'Annually':
        next_payment_date += pd.DateOffset(years=1)
        
    # Current tax year state
    current_tax_year_idx = -1
    current_allowance = Decimal(0.0)
    current_contributed = Decimal(0.0)
    current_rate_daily = Decimal(0.0)
    current_tax_year_end = pd.Timestamp.min
    
    # Initial Investment
    if initial_investment > 0:
        lump_sum_map[start_date] = lump_sum_map.get(start_date, 0) + initial_investment

    for date in date_range:
        year = date.year
        
        # 1. Determine Tax Year & Interest Rate
        if date > current_tax_year_end or current_tax_year_idx == -1:
            mask = (rates_df['Start Date'] <= date) & (rates_df['End Date'] >= date)
            if mask.any():
                row = rates_df[mask].iloc[0]
                current_allowance = Decimal(int(row['Allowance']))
                current_rate_daily = Decimal(float(row[rate_type])) / 100 / 365
                current_tax_year_end = row['End Date']
                current_contributed = Decimal(0) 
                current_tax_year_idx = 1
            else:
                current_allowance = Decimal(0)
                current_rate_daily = Decimal(0.0)
                current_tax_year_end = date
                current_contributed = Decimal(0)

        # 2. Update Inflation Index
        annual_inflation = Decimal(0.0)
        if inflation_type != 'None':
            # inflation_map values are likely floats from pandas, so cast to float first
            val = inflation_map.get(year, 0.0)
            annual_inflation = Decimal(float(val))
            # Fix TypeError: Decimal ** float is not supported. Use Decimal for exponent.
            daily_inflation_factor = (1 + annual_inflation / 100) ** (Decimal(1)/Decimal(365))
            current_inflation_index *= daily_inflation_factor

        # 3. Apply Interest (Accumulate Pending)
        daily_interest = balance * current_rate_daily
        pending_interest += daily_interest
        
        # Check if interest should be paid (compounded)
        pay_interest = False
        if interest_freq == 'Daily':
            pay_interest = True
        elif interest_freq == 'Monthly' and date.is_month_end:
            pay_interest = True
        elif interest_freq == 'Quarterly' and date.is_quarter_end:
            pay_interest = True
        elif 'Annually' in interest_freq:
            # Tax Year End (April 5)
            if date.month == 4 and date.day == 5:
                pay_interest = True
        
        # Always pay on the very last day of simulation to capture accrued interest
        if date == end_ts:
            pay_interest = True
            
        if pay_interest:
            balance += pending_interest
            pending_interest = Decimal(0.0)
        
        # 4. Determine potential contribution
        potential_contribution = Decimal(0.0)
        
        # Recurring
        if frequency != 'None' and date.date() == next_payment_date.date():
            potential_contribution += recurring_amount
            if frequency == 'Weekly':
                next_payment_date += timedelta(weeks=1)
            elif frequency == 'Monthly':
                next_payment_date = pd.Timestamp(next_payment_date) + pd.DateOffset(months=1)
            elif frequency == 'Annually':
                next_payment_date = pd.Timestamp(next_payment_date) + pd.DateOffset(years=1)
                
        # Lump Sums
        if date.date() in lump_sum_map:
            potential_contribution += lump_sum_map[date.date()]
            
        # 5. Check Allowance and Deposit
        if potential_contribution > 0:
            remaining_allowance = max(Decimal(0.0), current_allowance - current_contributed)
            actual_deposit = min(potential_contribution, remaining_allowance)
            
            balance += actual_deposit
            total_invested += actual_deposit
            current_contributed += actual_deposit
            
        # 6. Calculate Real Values
        # Real Value = Nominal Value / Index
        # This gives value in "Start Date Money" terms (if index started at 1.0)
        # Or we can just store the index and let the UI decide how to present?
        # Let's store 'Real Balance' as Balance / Index.
        
        real_balance = balance / current_inflation_index
        real_invested = total_invested / current_inflation_index # This is debatable. Usually "Real Invested" is sum of (deposit / index_at_deposit).
        # But for simplicity, let's just deflate the current total. 
        # Actually, "Real Invested" is better calculated by accumulating deflated deposits.
        # But for now, let's just deflate the final balance to show "Buying Power of Portfolio".
        
        records.append({
            'Date': date,
            'Balance': balance,
            'Real Balance': real_balance,
            'Total Invested': total_invested,
            'Interest Earned': balance - total_invested,
            'Rate': current_rate_daily * 365 * 100,
            'Inflation Index': current_inflation_index,
            'Inflation Rate': annual_inflation if inflation_type != 'None' else Decimal(0.0)
        })
        
    return pd.DataFrame(records)
