import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from src.database import SessionLocal, MasterPayMatrix
from sqlalchemy.orm import Session

def get_next_cell_basic(current_basic: int, level: str, db: Session):
    """Finds the next cell in the matrix for a specific Pay Level."""
    cell = db.query(MasterPayMatrix).filter(
        MasterPayMatrix.basic_pay == current_basic,
        MasterPayMatrix.pay_level == level
    ).first()
    
    if cell:
        next_cell = db.query(MasterPayMatrix)\
            .filter(MasterPayMatrix.pay_level == level)\
            .filter(MasterPayMatrix.cell_number == cell.cell_number + 1)\
            .first()
        return next_cell.basic_pay if next_cell else current_basic
    return current_basic

def calculate_monthly_arrears(start_date, end_date, initial_drawn_basic, initial_due_basic, drawn_level, target_level, city_class, da_history_df, ta_slab):
    """
    drawn_level: The pay level for the 'Drawn' calculation (e.g. 13A1)
    target_level: The pay level for the 'Due' calculation (e.g. 14)
    """
    records = []
    current_date = start_date.replace(day=1)
    
    drawn_basic = int(initial_drawn_basic)
    due_basic = int(initial_due_basic)
    
    # DB Session for Increments
    db = SessionLocal()
    
    while current_date <= end_date:
        # 1. APPLY JULY INCREMENT
        if current_date.month == 7 and current_date > start_date:
            # Increment both using their respective levels
            drawn_basic = get_next_cell_basic(drawn_basic, drawn_level, db)
            due_basic = get_next_cell_basic(due_basic, target_level, db)
            
        # 2. FETCH DA RATE
        # Fetch the applicable DA rate for 'current_date' from da_history_df
        # da_history_df has 'effective_date' (date object) and 'da_rate' (float or int)
        # Filter for dates <= current_date and take max
        eff_rates = da_history_df[da_history_df['effective_date'] <= current_date]
        if not eff_rates.empty:
            # Sort by effective date desc
            current_da_rate = eff_rates.sort_values('effective_date', ascending=False).iloc[0]['da_rate'] / 100.0
        else:
            current_da_rate = 0.0
        
        # 3. CALCULATE HRA (Maharashtra Rules)
        # base_hra logic
        # Clean city_class string "X (Metro)" -> "X"
        c_code = city_class.split()[0]
        
        # Apply DA triggers
        if current_da_rate >= 0.50:
             hra_rate = 0.30 if c_code == "X" else (0.20 if c_code == "Y" else 0.10)
        elif current_da_rate >= 0.25:
             hra_rate = 0.27 if c_code == "X" else (0.18 if c_code == "Y" else 0.09)
        else:
             hra_rate = 0.24 if c_code == "X" else (0.16 if c_code == "Y" else 0.08)
             
        # 4. COMPUTE MONTHLY FINANCIALS
        # Drawn
        drawn_da = round(drawn_basic * current_da_rate)
        drawn_hra = round(drawn_basic * hra_rate)
        drawn_gross = drawn_basic + drawn_da + drawn_hra + ta_slab # NO DA ON TA
        
        # Due
        due_da = round(due_basic * current_da_rate)
        due_hra = round(due_basic * hra_rate)
        due_gross = due_basic + due_da + due_hra + ta_slab
        
        diff_total = due_gross - drawn_gross
        
        records.append({
            "Month": current_date.strftime("%b-%Y"),
            "Drawn Basic": drawn_basic,
            "Due Basic": due_basic,
            "DA Rate %": int(current_da_rate * 100),
            "Diff Basic": due_basic - drawn_basic,
            "Diff DA": due_da - drawn_da,
            "Diff HRA": due_hra - drawn_hra,
            "Total Arrears": diff_total
        })
        
        current_date += relativedelta(months=1)
    
    db.close()
    return pd.DataFrame(records)
