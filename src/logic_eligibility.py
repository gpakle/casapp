from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def evaluate_cas_eligibility(faculty_data: dict, target_level: str):
    """
    Evaluates CAS Eligibility based on AICTE 2018 + Maharashtra Rules.
    """
    
    # Unpack Data
    doj = faculty_data['date_of_joining']
    past_service = faculty_data['past_service_years']
    current_level = faculty_data['current_level']
    last_promo = faculty_data['promoted_level_12_date'] if current_level == "12" else \
                 (faculty_data['promoted_level_11_date'] if current_level == "11" else doj)
                 
    # 1. Effective Joining Date
    # Effective DOJ = DOJ - Past Service Years
    effective_doj = doj - relativedelta(years=past_service)
    
    # 2. Base Requirements
    req_years = 0
    phd_required = False
    
    if current_level == "10": 
        # L10 -> L11
        # 4 years (Ph.D), 5 years (M.Tech), 6 years (B.Tech) - AICTE 2018
        # User prompt earlier said 5(MTech)/6(BTech). Sticking to general logic or prompting user?
        # Let's use standard logic inferred from context.
        degree = faculty_data['entry_qualification']
        if degree == "Ph.D." or faculty_data['acquired_phd_date']: req_years = 4
        elif degree == "M.E./M.Tech" or faculty_data['acquired_mtech_date']: req_years = 5
        else: req_years = 6
        target = "11"
        
    elif current_level == "11":
        # L11 -> L12: 5 years
        req_years = 5
        target = "12"
        
    elif current_level == "12":
        # L12 -> L13A1: 3 years
        req_years = 3
        phd_required = True
        target = "13A1"
        
    elif current_level == "13A1":
        req_years = 3
        phd_required = True
        target = "14"
        
    else:
        return {"eligible": False, "reason": "Unknown Level"}

    # Calculate Due Date
    # Due date is relative to Last Promotion
    # BUT wait, the prompt asks for specific waivers based on dates.
    # Let's calculate the theoretical due date first.
    
    # If last_promo is None, handle...
    if not last_promo:
        last_promo = effective_doj
        
    base_due_date = last_promo + relativedelta(years=req_years)
    
    # JULY ALIGNMENT RULE (User Request)
    # Effect from July 1st of the eligibility year
    # Example: Eligible Sept 2016 -> Due July 1, 2016
    base_due_date = date(base_due_date.year, 7, 1)
    
    flags = []
    
    # 3. Pre-2010 Ph.D. Waiver
    # "phd_waived = True if effective_doj < datetime.date(2010, 3, 5) else False"
    phd_waived = False
    cutoff_2010 = date(2010, 3, 5)
    if effective_doj < cutoff_2010:
        phd_waived = True
        flags.append("Pre-2010 PhD Waiver")
        
    # Check PhD Requirement
    is_eligible = True
    reason = "Requirements Met"
    
    if phd_required and not phd_waived:
        # Check if PhD acquired
        phd_date = faculty_data['acquired_phd_date']
        if not phd_date:
            is_eligible = False
            reason = "Ph.D. Required and not acquired."
        elif phd_date > base_due_date:
            # Eligibility deferred
            base_due_date = phd_date
            reason = "Eligibility deferred to PhD completion."

    # 4. MAT Order API Waiver
    # "If the calculated promotion_due_date is >= 2015-10-17 AND <= 2019-09-10, set api_exempt = True."
    api_exempt = False
    mat_start = date(2015, 10, 17)
    mat_end = date(2019, 9, 10)
    
    if mat_start <= base_due_date <= mat_end:
        api_exempt = True
        flags.append("MAT Order API Waiver (Exempt)")

    return {
        "eligible": is_eligible,
        "due_date": base_due_date,
        "target_level": target,
        "phd_waived": phd_waived,
        "api_exempt": api_exempt,
        "flags": flags,
        "reason": reason
    }
