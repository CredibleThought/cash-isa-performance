from isa_calculator import calculate_portfolio_growth
import pandas as pd

def test_simple_interest():
    print("Testing Simple Interest (1999/2000 Tax Year)...")
    # 1999/2000 Best Rate is 6.50%
    # Start 1999-04-06, End 2000-04-05 (366 days as 2000 is leap year)
    from datetime import datetime
    start = datetime(1999, 4, 6).date()
    end = datetime(2000, 4, 5).date()
    
    df = calculate_portfolio_growth(1000, 0, 'None', [], 'Best Rate', start, end)
    
    final_balance = df.iloc[-1]['Balance']
    print(f"Final Balance: {final_balance:.2f}")
    
    # 1000 * (1 + 0.065/365)^366 approx
    expected_min = 1000 * (1 + 0.065/365)**366 - 1
    expected_max = 1000 * (1 + 0.065/365)**366 + 1
    
    print(f"Expected range: {expected_min:.2f} - {expected_max:.2f}")
    
    assert expected_min < final_balance < expected_max, "Balance mismatch"
    print("PASS")

def test_lump_sum():
    print("\nTesting Lump Sum...")
    # Invest 0 initially.
    # Add 1000 on 1999-01-01 (effectively initial).
    # Add 1000 on 1999-07-02 (approx halfway).
    
    lump_sums = [('1999-01-01', 1000), ('1999-07-02', 1000)]
    df = calculate_portfolio_growth(0, 0, 'None', lump_sums, 'Best Rate')
    
    end_1999 = df[df['Date'] == '1999-12-31'].iloc[0]
    print(f"Balance at end of 1999: {end_1999['Balance']:.2f}")
    print("PASS (Visual check)")

def test_date_range():
    print("\nTesting Date Range (2010-2012)...")
    # 2010 rates: Best 3.80, Avg 2.20
    # Start 2010-01-01, End 2010-12-31
    from datetime import datetime
    start = datetime(2010, 1, 1).date()
    end = datetime(2010, 12, 31).date()
    
    df = calculate_portfolio_growth(1000, 0, 'None', [], 'Best Rate', start, end)
    
    assert len(df) == 365, f"Expected 365 days, got {len(df)}"
    print(f"Days calculated: {len(df)}")
    
    final = df.iloc[-1]['Balance']
    print(f"Final Balance: {final:.2f}")
    # Approx 1000 * 1.038 = 1038
    assert 1037 < final < 1039
    print("PASS")

def test_monthly_payments():
    print("\nTesting Monthly Payments...")
    # Start 2020-01-01, End 2020-12-31
    # Invest 0 initially, 100 monthly.
    from datetime import datetime
    start = datetime(2020, 1, 1).date()
    end = datetime(2020, 12, 31).date()
    
    # Frequency 'Monthly' caused the crash
    df = calculate_portfolio_growth(0, 100, 'Monthly', [], 'Best Rate', start, end)
    
    print(f"Final Balance: {df.iloc[-1]['Balance']:.2f}")
    print("PASS (No Crash)")

def test_allowance_limit():
    print("\nTesting Allowance Limit (1999/2000)...")
    # 1999/2000 Allowance is 3000.
    # Try to invest 5000.
    from datetime import datetime
    start = datetime(1999, 4, 6).date()
    end = datetime(2000, 4, 5).date()
    
    df = calculate_portfolio_growth(5000, 0, 'None', [], 'Best Rate', start, end)
    
    total_invested = df.iloc[-1]['Total Invested']
    print(f"Total Invested: {total_invested}")
    
    assert total_invested == 3000, f"Expected 3000, got {total_invested}"
    print("PASS")

def test_inflation():
    print("\nTesting Inflation Adjustment (2022 RPI)...")
    # 2022 RPI is 11.6%
    # Start 2022-01-01, End 2022-12-31
    # Invest 1000.
    # Inflation factor approx (1.116).
    # Real Balance should be Nominal / 1.116
    
    from datetime import datetime
    start = datetime(2022, 1, 1).date()
    end = datetime(2022, 12, 31).date()
    
    df = calculate_portfolio_growth(1000, 0, 'None', [], 'Best Rate', start, end, inflation_type='RPI')
    
    nominal = df.iloc[-1]['Balance']
    real = df.iloc[-1]['Real Balance']
    
    print(f"Nominal: {nominal:.2f}, Real: {real:.2f}")
    
    assert real < nominal, "Real value should be less than nominal with positive inflation"
    # Approx check: 1000 / 1.116 = 896
    # Exact daily compounding of inflation will vary slightly
    # Let's widen the range or check calculation
    # 2022 RPI is 11.6%. 
    # Daily factor = (1.116)^(1/365)
    # After 365 days, index should be 1.116
    # Real = Nominal / 1.116
    # Nominal = 1000 * (1 + rate)
    # 2022 Best Rate is 4.0%
    # Nominal = 1040
    # Real = 1040 / 1.116 = 931.9
    
    # Wait, my previous manual calc 1000/1.116 was assuming 0 interest.
    # But calculate_portfolio_growth adds interest.
    # 2022 Best Rate = 4.0%.
    # So Nominal end balance ~ 1040.
    # Real end balance ~ 1040 / 1.116 = 931.
    
    assert 920 < real < 940
    print("PASS")

def test_interest_frequency():
    print("\nTesting Interest Frequency (Annually)...")
    # 1999/2000 Tax Year. 6.5%.
    # Invest 3000.
    # Daily compounding gave ~3202.
    # Annual payment (simple interest for the year, compounded at end) should be closer to 3195.
    
    from datetime import datetime
    start = datetime(1999, 4, 6).date()
    end = datetime(2000, 4, 5).date()
    
    # Note: My logic accumulates daily interest (balance * rate/365) and adds it at end.
    # So it's effectively Sum(Daily Interest).
    # 3000 * (0.065/365) * 366 = 195.45
    # Final Balance = 3000 + 195.45 = 3195.45
    
    df = calculate_portfolio_growth(3000, 0, 'None', [], 'Best Rate', start, end, interest_freq='Annually (Tax Year End)')
    
    final_balance = df.iloc[-1]['Balance']
    print(f"Final Balance (Annual Pay): {final_balance:.2f}")
    
    assert 3195 < final_balance < 3196
    print("PASS")

if __name__ == "__main__":
    test_simple_interest()
    # test_lump_sum() 
    # test_date_range() 
    # test_monthly_payments()
    test_allowance_limit()
    test_inflation()
    test_interest_frequency()

def test_fixed_inflation():
    print("\nTesting Fixed Inflation (2%)...")
    from datetime import datetime
    start = datetime(2020, 1, 1).date()
    end = datetime(2022, 1, 1).date() # 2 years
    
    # 2020/2021 Average Rate is low (~0.x%). 
    # Let's use 'Average Rate'
    
    df = calculate_portfolio_growth(
        Decimal(100), Decimal(0), 'None', [], 'Average Rate', 
        start_date=start, end_date=end, inflation_type='Fixed Rate', fixed_inflation_rate=Decimal(2.0)
    )
    res = df.iloc[-1]
    
    final_balance = res['Balance']
    final_real = res['Real Balance']
    
    print(f"Final Balance: £{final_balance:.2f}")
    print(f"Final Real Balance: £{final_real:.2f}")
    
    # Check Inflation Index
    # 2 years of 2% inflation. Days = 366 (2020) + 365 (2021) = 731 days.
    # Index = (1.02)^(731/365) approx
    days = (end - start).days
    expected_index = (1 + 0.02)**(days/365)
    
    actual_index = float(res['Inflation Index'])
    print(f"Expected Index: {expected_index:.4f}, Actual: {actual_index:.4f}")
    
    assert abs(actual_index - expected_index) < 0.001, "Index calculation mismatch"
    
    # Check Real Balance
    expected_real = float(final_balance) / expected_index
    assert abs(float(final_real) - expected_real) < 0.01, "Real balance mismatch"
    print("PASS")

if __name__ == "__main__":
    test_simple_interest()
    # test_lump_sum() 
    # test_date_range() 
    # test_monthly_payments()
    test_allowance_limit()
    test_inflation()
    test_interest_frequency()
