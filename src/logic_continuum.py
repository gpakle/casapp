import datetime
from sqlalchemy.orm import Session
from src.database import MasterPayMatrix

def get_next_cell_basic(current_basic: int, level: str, db: Session):
    """
    Finds the next cell in the same level.
    """
    try:
        # Find current cell
        curr_cell = db.query(MasterPayMatrix)\
            .filter(MasterPayMatrix.pay_level == level)\
            .filter(MasterPayMatrix.basic_pay == current_basic)\
            .first()
            
        if not curr_cell:
            # Fallback: find closest <= current
            curr_cell = db.query(MasterPayMatrix)\
                .filter(MasterPayMatrix.pay_level == level)\
                .filter(MasterPayMatrix.basic_pay <= current_basic)\
                .order_by(MasterPayMatrix.basic_pay.desc())\
                .first()

        if curr_cell:
            # Get next cell
            next_cell = db.query(MasterPayMatrix)\
                .filter(MasterPayMatrix.pay_level == level)\
                .filter(MasterPayMatrix.cell_number == curr_cell.cell_number + 1)\
                .first()
            if next_cell:
                return next_cell.basic_pay
    except Exception:
        pass
    return current_basic # No change if max or error

def calculate_promotion_fixation(old_basic: int, old_level: str, target_level: str, db: Session):
    """
    Simulates fixation on promotion:
    1. Notional Increment in Old Level
    2. Find cell >= Notional in Target Level
    """
    # 1. Notional Increment
    notional_pay = get_next_cell_basic(old_basic, old_level, db)
    
    # 2. Find in Target
    target_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == target_level)\
        .filter(MasterPayMatrix.basic_pay >= notional_pay)\
        .order_by(MasterPayMatrix.basic_pay)\
        .first()
        
    if target_cell:
        return target_cell.basic_pay
    
    # Fallback to first cell of target if notional is lower than start
    first_cell = db.query(MasterPayMatrix)\
        .filter(MasterPayMatrix.pay_level == target_level)\
        .order_by(MasterPayMatrix.basic_pay)\
        .first()
    if first_cell:
        return first_cell.basic_pay
        
    return old_basic # Should not happen

def calculate_pay_at_current_joining(initial_doj: datetime.date, current_doj: datetime.date, entry_qual: str, db: Session):
    """
    Simulates promotions and increments from the first job to find the exact
    Pay Level and Cell on the day of joining the current institute.
    """
    # Base Starting Point (Lecturer / Asst Prof) -> Level 10, Cell 1
    current_level = "10"
    current_basic = 57700 
    
    # Determine years required for first promotion
    # PhD: 4 years, M.Tech/M.Phil: 5 years, Others: 6 years
    if entry_qual == "Ph.D.":
        years_to_lvl_11 = 4
    elif entry_qual in ["M.E./M.Tech", "M.Phil"]:
        years_to_lvl_11 = 5
    else:
        years_to_lvl_11 = 6
        
    # Validation
    if not initial_doj or not current_doj or initial_doj >= current_doj:
        return {
            "Joining_Level": current_level,
            "Joining_Basic": current_basic,
            "Total_Past_Years": 0,
            "Error": "Invalid Dates"
        }

    sim_date = initial_doj
    years_served = 0
    
    # We iterate year by year or event by event?
    # User requested month-by-month or event-based loop.
    # Let's iterate monthly to catch July 1st and Anniversary correctly.
    
    curr_date_pointer = initial_doj
    
    while curr_date_pointer < current_doj:
        # Move forward logic
        # Check if next July 1 is closer or Anniversary is closer?
        # Let's simple check "Next Month" approach as per user snippet
        
        # Advance 1 day to ensure we are seemingly moving
        # Actually user logic: sim_date += 32 days, then replace day=1.
        # This skips months.
        # Let's use robust date logic: 1st of next month.
        
        next_month = curr_date_pointer.replace(day=1) + datetime.timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        # BUT, we need to process events WITHIN the current month before moving?
        # User snippet checks: if sim_date.month == 7.
        # This implies checking the state AT specific months.
        
        check_date = next_month # The date we are simulating IS this new month.
        if check_date > current_doj:
            break
            
        curr_date_pointer = check_date
        
        # 1. Check for July Increment
        # Increment given on July 1st.
        if curr_date_pointer.month == 7:
             current_basic = get_next_cell_basic(current_basic, current_level, db)
             
        # 2. Check for Anniversary (Completion of Year)
        # Assuming Anniversary is same Month as joining?
        # "if sim_date.month == initial_doj.month" -> approximate year completion
        if curr_date_pointer.month == initial_doj.month:
            years_served += 1
            
            # Promote to Level 11 (Sr. Scale)
            if current_level == "10" and years_served == years_to_lvl_11:
                # Promotion Event
                new_basic = calculate_promotion_fixation(current_basic, "10", "11", db)
                current_level = "11"
                current_basic = new_basic
                
            # Promote to Level 12 (Sel. Grade)
            # 5 years service in Level 11 required for Level 12
            # Total service logic: years_served total vs years in level?
            # User snippet: "years_served == (years_to_level_11 + 5)"
            elif current_level == "11" and years_served == (years_to_lvl_11 + 5):
                new_basic = calculate_promotion_fixation(current_basic, "11", "12", db)
                current_level = "12"
                current_basic = new_basic
                
    return {
        "Joining_Level": current_level,
        "Joining_Basic": current_basic,
        "Total_Past_Years": years_served,
        "Log": f"Simulated {years_served} years."
    }
