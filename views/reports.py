import streamlit as st
import pandas as pd
from datetime import date
from src.database import SessionLocal, MasterDARates, MasterTASlabs, MasterPayMatrix
from src.logic_arrears import calculate_monthly_arrears
from src.logic_fixation import calculate_fixation
from sqlalchemy import desc

def get_da_history_df(db):
    rates = db.query(MasterDARates).all()
    return pd.DataFrame([{
        'effective_date': r.effective_date,
        'da_rate': r.da_rate
    } for r in rates])

def get_ta_slab_amount(pay_level, city_class, db):
    # Parse level "13A1" -> 13
    import re
    m = re.match(r"(\d+)", str(pay_level))
    num_level = int(m.group(1)) if m else 0
    
    # Map City Class 'X (Metro)' -> 'Metro'
    c_type = "Metro" if "X" in city_class else "Other"
    
    slab = db.query(MasterTASlabs)\
        .filter(MasterTASlabs.min_pay_level <= num_level)\
        .filter(MasterTASlabs.city_type == c_type)\
        .order_by(desc(MasterTASlabs.min_pay_level))\
        .first()
    return slab.fixed_amount if slab else 0

def get_pay_options(level, db):
    res = db.query(MasterPayMatrix.basic_pay)\
            .filter(MasterPayMatrix.pay_level == level)\
            .order_by(MasterPayMatrix.basic_pay).all()
    return [r[0] for r in res]

def show():
    st.header("Arrears Calculator 💰")
    
    if 'faculty_data' not in st.session_state:
        st.warning("Please fill out the 'Faculty Comprehensive Profile' first.")
        return

    prof = st.session_state['faculty_data']
    config = st.session_state.get('arrears_config', {})
    
    with st.expander("Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        # Start Date: Use Config > Profile
        default_start = config.get('start_date') or prof.get('promoted_level_12_date') or prof.get('date_of_joining')
        start_date = col1.date_input("Arrears Start Date", value=default_start)
        end_date = col2.date_input("Arrears End Date", value=date.today())
        
        # Target Level logic
        levels = ["10", "11", "12", "13A1", "14"]
        curr_lvl = prof['current_level']
        
        # Default target calculated or from config
        default_target_idx = 0
        if config.get('target_level') and config['target_level'] in levels:
             default_target_idx = levels.index(config['target_level'])
        else:
             try:
                 default_target_idx = min(levels.index(curr_lvl) + 1, len(levels)-1)
             except: pass
            
        target_level = col2.selectbox("Target Level (Due Level)", levels, index=default_target_idx)
        
        # Drawn Level is assumed to be Current Level in Profile
        drawn_level = curr_lvl
        col1.info(f"Drawn Level: {drawn_level} (From Profile)")
        
        c3, c4 = st.columns(2)
        
        # Drawn Basic Inputs - Dynamic Dropdown
        db = SessionLocal()
        pay_opts = get_pay_options(drawn_level, db)
        
        # LOGIC CHANGE: AUTO-CALCULATE HISTORICAL DRAWN BASIC
        # If start_date is in past, try to find what the basic was THEN.
        suggested_historical_basic = 0
        try:
             # Calculate years elapsed (approx)
             # Start date vs Today. "Reverse Fixation".
             # Actually, we need to know what the basic IS TODAY to reverse it.
             # profile has 'current_basic'.
             today = date.today()
             # Only if start_date is significantly in past (> 1 year)
             if start_date < today:
                 # Simple year diff for cell countdown
                 # logic: July 1st count between start and today
                 # If today is after July 1st, and start is before, count is diff.
                 years_back = 0
                 # Count how many July 1sts passed between start_date and today
                 # This equals number of increments to rollback
                 curr_year = today.year
                 d_year = start_date.year
                 
                 # Loop years
                 for y in range(d_year, curr_year + 1):
                     july1 = date(y, 7, 1)
                     if start_date < july1 <= today:
                         years_back += 1
                 
                 if years_back > 0:
                     from src.logic_fixation import calculate_historical_basic
                     hist_res = calculate_historical_basic(
                         current_basic=int(prof.get('current_basic', 0)),
                         level=drawn_level,
                         years_back=years_back,
                         db=db
                     )
                     if "historical_basic" in hist_res:
                         suggested_historical_basic = hist_res['historical_basic']
                         col1.success(f"History: Rolling back {years_back} increments from Current Basic ({prof.get('current_basic')}). Suggested: {suggested_historical_basic}")
        except Exception as e:
            col1.warning(f"History Calc Error: {e}")

        # Default drawn basic logic
        # Priority: Suggested Historical > Profile Current (fallback)
        def_drawn_idx = 0
        target_default = suggested_historical_basic if suggested_historical_basic > 0 else int(prof.get('current_basic', 0))
        
        if target_default in pay_opts:
            def_drawn_idx = pay_opts.index(target_default)
            
        if pay_opts:
            initial_drawn_basic = c3.selectbox("Basic Pay DRAWN at Start Date", pay_opts, index=def_drawn_idx)
        else:
            c3.warning(f"No matrix data for {drawn_level}")
            initial_drawn_basic = c3.number_input("Basic Pay DRAWN at Start Date", value=target_default, step=100)
        
        # Calculate suggested fix as Due
        fix_val = 0
        try:
            fix_res = calculate_fixation(initial_drawn_basic, drawn_level, target_level, db)
            if "new_basic" in fix_res: fix_val = fix_res['new_basic']
        except: pass
        
        initial_due_basic = c4.number_input("Basic Pay DUE at Start Date", value=fix_val, step=100)
        db.close()

    if st.button("Calculate Arrears"):
        db = SessionLocal()
        try:
            # Prepare Inputs
            da_df = get_da_history_df(db)
            ta_amt = get_ta_slab_amount(target_level, prof['city_class'], db)
            
            # Execute Engine
            df = calculate_monthly_arrears(
                start_date=start_date,
                end_date=end_date,
                initial_drawn_basic=initial_drawn_basic,
                initial_due_basic=initial_due_basic,
                drawn_level=drawn_level,   # Pass Explicitly
                target_level=target_level, # Pass Explicitly
                city_class=prof['city_class'],
                da_history_df=da_df,
                ta_slab=ta_amt
            )
            
            # Summary
            total = df['Total Arrears'].sum()
            st.metric("Total Arrears Payable", f"₹ {total:,.0f}")
            
            st.dataframe(df)
            
            # Downloads
            csv = df.to_csv(index=False).encode('utf-8')
            col_d1, col_d2 = st.columns(2)
            
            col_d1.download_button(
                "📥 Download CSV",
                csv,
                f"arrears_{prof['name']}.csv",
                "text/csv"
            )
            
            # Download PDF
            try:
                from src.reports_generator import generate_arrears_pdf
                pdf_bytes = generate_arrears_pdf(prof, df, start_date, target_level) # Pass correct start_date as due date
                col_d2.download_button(
                    "📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Arrears_Statement_{prof['name']}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                col_d2.error(f"PDF Error: {e}")
            
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            db.close()
