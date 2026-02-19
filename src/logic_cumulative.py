import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from src.database import MasterPayMatrix
from src.logic_continuum import get_next_cell_basic, calculate_promotion_fixation

def evaluate_cumulative_promotions(faculty_data, db: Session):
    """
    faculty_data dict must contain: initial_doj, entry_qualification, acquired_phd_date
    """
    initial_doj = faculty_data['initial_doj']
    sim_date = initial_doj
    end_date = datetime.date.today()
    
    current_level = "10"
    current_basic = 57700 # Entry pay for Level 10 (Cell 1)
    
    # Trackers
    promotion_events = [] 
    level_entry_date = initial_doj
    
    # Pre-2010 Waiver Rule (Maharashtra GR 18 Feb 2026 / 8 March 2019 reference)
    # User specified: "needs Ph.d. as per Feb 18, 2026" for 13A1.
    # We will enforce PhD strictness for 13A1.
    
    # Loop month by month
    while sim_date <= end_date:
        
        # 1. APPLY JULY INCREMENT (On July 1st)
        if sim_date.month == 7 and sim_date.day == 1:
            # Check if joining date / promotion date was < 6 months ago?
            # Standard rule: complete 6 months to get increment.
            # If joined Jan 1st -> July 1st (6 months) -> Increment YES.
            # If joined Feb 1st -> July 1st (5 months) -> Increment NO.
            
            # Simple check: 
            months_since_entry = relativedelta(sim_date, level_entry_date).months + (relativedelta(sim_date, level_entry_date).years * 12)
            
            if months_since_entry >= 6:
                current_basic = get_next_cell_basic(current_basic, current_level, db)
            
        # 2. CHECK PROMOTIONS (Any day, but alignment logic below)
        
        # Calculate Service in Current Level
        rel = relativedelta(sim_date, level_entry_date)
        years_served_in_level = rel.years
        
        # --- LEVEL 10 -> 11 (Sr. Scale) ---
        if current_level == "10":
            # Duration based on Entry Qual
            eq = faculty_data.get('entry_qualification', '')
            req_years_11 = 4 if eq == "Ph.D." else (5 if eq in ["M.E./M.Tech", "M.Phil"] else 6)
            
            if years_served_in_level >= req_years_11:
                # Eligibility Date (Raw)
                raw_date = sim_date
                
                # USER LOGIC: "Joined Sept 2010 -> Level 11 in July 2016"
                # Sept 2010 + 6 years = Sept 2016.
                # User wants July 2016.
                # This implies: If eligible in Year Y, align to July 1st of Year Y?
                # Or July 1st of Academic Year?
                # Let's align to: datetime.date(raw_date.year, 7, 1) if raw_date >= July?
                # Sept 2016 > July 2016.
                # If we align to July 2016, we are pre-dating.
                
                # Let's try: Effective Date = July 1st of the Completion Year.
                effective_date = datetime.date(raw_date.year, 7, 1)
                
                # Ensure effective date is not before joining (unlikely with 6 years)
                if effective_date < level_entry_date: effective_date = raw_date # Fallback
                
                # Only promote if sim_date reached this effective_date (or we overwrite history?)
                # We are simulating forward. If sim_date reached raw_date (Sept), we can say "Effective from July".
                # But we missed July in the loop?
                
                # Actually, if we want July 2016 and we are at Sept 2016, we can "backdate" the event.
                # But for financial logic, we should have applied it in July.
                
                # REVISED LOOP LOGIC:
                # We should check eligibility based on "Year Completion" logic primarily.
                # If we reach Sept 2016, and say "It was due July 2016", we need to correct the basic from July.
                
                # SIMPLIFICATION:
                # Use the Effective Date for the Event.
                # Fixation happens on Effective Date.
                
                new_basic = calculate_promotion_fixation(current_basic, "10", "11", db)
                
                promotion_events.append({
                    "Promotion": "Level 10 -> 11",
                    "Due Date": effective_date,
                    "Eligibility": "Served Required Years",
                    "Fixed Basic": new_basic
                })
                
                current_level = "11"
                current_basic = new_basic
                level_entry_date = effective_date # Reset clock to July 2016
                years_served_in_level = 0
                
                # Adjust sim_date to effective_date to restart increments correctly?
                # If we are at Sept, and we say effective July, we should technically go back?
                # Simplest: Just set sim_date = effective_date and continue.
                sim_date = effective_date
            
        # --- LEVEL 11 -> 12 (Sel. Grade) ---
        elif current_level == "11":
            # 5 Years Fixed
            if years_served_in_level >= 5:
                raw_date = sim_date
                # July Alignment
                effective_date = datetime.date(raw_date.year, 7, 1)
                
                new_basic = calculate_promotion_fixation(current_basic, "11", "12", db)
                
                promotion_events.append({
                    "Promotion": "Level 11 -> 12",
                    "Due Date": effective_date,
                    "Fixed Basic": new_basic
                })
                
                current_level = "12"
                current_basic = new_basic
                level_entry_date = effective_date
                years_served_in_level = 0
                sim_date = effective_date
                
        # --- LEVEL 12 -> 13A1 (Associate Prof) ---
        elif current_level == "12":
            # 3 Years Fixed
            if years_served_in_level >= 3:
                 # STRICT PHD CHECK (User Ref: Feb 18 2026 Rule)
                 # Assumption: Must have PhD on this date.
                 has_phd = False
                 phd_date = faculty_data.get('acquired_phd_date')
                 
                 effective_date = datetime.date(sim_date.year, 7, 1)
                 
                 if phd_date:
                     if isinstance(phd_date, str):
                         phd_date = datetime.date.fromisoformat(phd_date)
                     if phd_date <= effective_date:
                         has_phd = True
                 
                 if has_phd:
                    new_basic = calculate_promotion_fixation(current_basic, "12", "13A1", db)
                    
                    promotion_events.append({
                        "Promotion": "Level 12 -> 13A1",
                        "Due Date": effective_date,
                        "Note": "PhD Requirement Met",
                        "Fixed Basic": new_basic
                    })
                    current_level = "13A1"
                    current_basic = new_basic
                    level_entry_date = effective_date
                    years_served_in_level = 0
                    sim_date = effective_date
                 else:
                     # Log rejection or wait?
                     # If they get PhD later, they might get promoted later.
                     # We continue loop. Ideally, we check if they get PhD in future loops.
                     pass
        
        # Move forward 1 month
        sim_date += relativedelta(months=1)
                    
    return promotion_events, current_level, current_basic
