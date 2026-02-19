from sqlalchemy.orm import Session
from src.database import MasterPayMatrix
from datetime import date

def calculate_fixation(current_basic: int, current_level: str, target_level: str, db: Session):
    """
    Calculates 7th Pay Commission Fixation.
    
    Logic:
    1. Locate cell in current_level corresponding to current_basic.
    2. Add one increment (move one cell down in same level) -> Notional Pay.
    3. Locate cell in target_level immediately higher than Notional Pay.
    """
    
    # 1. Verify Current Level and Basic
    # Note: DB stores pay_level as String "10", "11", "13A"
    
    curr_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == str(current_level))\
        .filter(MasterPayMatrix.basic_pay == current_basic)\
        .first()
        
    if not curr_cell:
        # Fallback: finding closest cell or user might have entered wrong basic
        # For strictness, return None
        return {"error": "Current Basic Pay not found in Pay Matrix for this level."}

    # 2. Add Notional Increment
    # Next cell in same level
    notional_cell_num = curr_cell.cell_number + 1
    notional_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == str(current_level))\
        .filter(MasterPayMatrix.cell_number == notional_cell_num)\
        .first()
        
    # If no next cell (reached max), uses last cell (stagnation) logic? 
    # Usually 7th PC matrix is long enough. If not found, use current basic + 3%?
    # Let's assume matrix covers it for now or stick to current if maxed.
    notional_pay = notional_cell.basic_pay if notional_cell else current_basic

    # 3. Find in Target Level
    # Find smallest cell >= notional_pay
    target_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == str(target_level))\
        .filter(MasterPayMatrix.basic_pay >= notional_pay)\
        .order_by(MasterPayMatrix.basic_pay)\
        .first()
        
    if not target_cell:
         return {"error": "Target Pay Matrix cell not found (might be beyond matrix max)."}
         
    return {
        "old_basic": current_basic,
        "old_level": current_level,
        "notional_increment_pay": notional_pay,
        "new_level": target_level,
        "new_basic": target_cell.basic_pay,
        "new_cell": target_cell.cell_number
    }

def calculate_projected_pay(start_basic: int, level: str, start_date: date, db: Session):
    """
    Projects the current Basic Pay by applying annual July increments 
    from start_date (promotion date) to today.
    """
    current_basic = start_basic
    current_date = start_date
    today = date.today()
    
    # We iterate year by year
    # Logic: From start_date, find the next July 1st. 
    # If next July 1st <= today, increment. Repeat.
    
    # Logic refinements:
    # If start_date is before July 1st of that year (e.g. Jan 2018), 
    # first increment is July 1st 2018.
    # If start_date is after July 1st (e.g. Aug 2018),
    # first increment is July 1st 2019.
    
    # However, standard practice is just check every July 1st in the range.
    
    # Start checking from the year of start_date
    check_year = start_date.year
    
    increments = []
    
    while True:
        check_date = date(check_year, 7, 1)
        
        # Stop if check_date is in the future relative to today
        # User wants "current new basic" which implies "as of today"
        # BUT user example says: "July 2026 will be..." implying future projection too?
        # Let's project up to today + 1 year maybe? Or just today.
        # User said: "so current new basic after promotion will be on july 2025... July 2026 will be..."
        # It seems they want a schedule.
        # Let's return a list of increments up to today, or maybe slightly future.
        # Let's loop until check_date > today.
        
        if check_date > today:
            break
            
        if check_date > start_date:
            # Apply increment
            # Find next cell
            curr_cell = db.query(MasterPayMatrix)\
                .filter(MasterPayMatrix.pay_level == level)\
                .filter(MasterPayMatrix.basic_pay == current_basic)\
                .first()
                
            if curr_cell:
                next_cell = db.query(MasterPayMatrix)\
                    .filter(MasterPayMatrix.pay_level == level)\
                    .filter(MasterPayMatrix.cell_number == curr_cell.cell_number + 1)\
                    .first()
                
                if next_cell:
                    current_basic = next_cell.basic_pay
                    increments.append({
                        "date": check_date,
                        "basic": current_basic,
                        "cell": next_cell.cell_number
                    })
        
        check_year += 1
        
    return {
        "projected_basic": current_basic,
        "increments": increments
    }

def calculate_historical_basic(current_basic: int, level: str, years_back: int, db: Session):
    """
    Reverse calculates the Basic Pay 'years_back' ago.
    Assumes 1 cell = 1 year of increment.
    
    Logic:
    1. Find current cell.
    2. Subtract 'years_back' from cell_number.
    3. Return basic_pay of that previous cell.
    """
    # 1. Find Current Cell
    curr_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == level)\
        .filter(MasterPayMatrix.basic_pay == current_basic)\
        .first()
        
    if not curr_cell:
        return {"error": "Current Basic Pay not found in Matrix"}
        
    # 2. Calculate Past Cell Number
    past_cell_num = curr_cell.cell_number - years_back
    
    if past_cell_num < 1:
        # Before matrix start? Or should we clamp to 1?
        # Return cell 1 and warn
        past_cell_num = 1
        
    # 3. Fetch Past Cell
    past_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == level)\
        .filter(MasterPayMatrix.cell_number == past_cell_num)\
        .first()
        
    if past_cell:
        return {"historical_basic": past_cell.basic_pay, "cell": past_cell.cell_number}
    else:
        return {"error": "Historical cell not found"}
