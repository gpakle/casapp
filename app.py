import streamlit as st
from datetime import date
from src.database import init_db, SessionLocal
from views import profile, reports
from src.logic_eligibility import evaluate_cas_eligibility
from src.logic_fixation import calculate_fixation

# Config
st.set_page_config(
    page_title="CAS Promotion Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Modern UI
st.markdown("""
<style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Header Styling */
    h1, h2, h3 {
        color: #1e3a8a; /* Dark Blue */
        font-weight: 700;
    }
    
    /* Card-like Containers */
    div.block-container {
        padding-top: 2rem;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #e5e7eb;
        border-radius: 5px;
        color: #4b5563;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2563eb; /* Blue-600 */
        color: white;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .stSelectbox>div>div>div {
        border-radius: 5px;
    }
    
    /* Card Wrapper for Content */
    .css-card {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
</style>
""", unsafe_allow_html=True)

init_db()

# Session State for Defaults
if 'faculty_data' not in st.session_state:
    st.session_state['faculty_data'] = {
        "name": "",
        "institute_type": "Government",
        "city_class": "X (Metro)",
        "past_service_years": 0,
        "date_of_joining": date(2010, 1, 1),
        "entry_qualification": "M.E./M.Tech",
        "acquired_mtech_date": None,
        "acquired_phd_date": None,
        "promoted_level_11_date": None,
        "promoted_level_12_date": None,
        "current_level": "10",
        "current_basic": 57700
    }

# Main Layout
st.title("🎓 CAS Promotion & Arrears Dashboard")
st.markdown("Automated Eligibility Check, Pay Fixation & Arrears Calculation for Engineering Faculty.")

# Tabs System
tab1, tab2, tab3 = st.tabs(["👤 Profile Entry", "✅ Eligibility & Fixation", "💰 Arrears Report"])

with tab1:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    profile.render_profile_form()
    
    # Continuum Logic Integration
    if st.session_state['faculty_data'].get('name') and st.session_state['faculty_data'].get('initial_doj'):
        from src.logic_continuum import calculate_pay_at_current_joining
        from src.database import SessionLocal
        
        fd = st.session_state['faculty_data']
        db = SessionLocal()
        
        # Run Simulation
        continuum_res = calculate_pay_at_current_joining(
            initial_doj=fd['initial_doj'],
            current_doj=fd['date_of_joining'],
            entry_qual=fd['entry_qualification'],
            db=db
        )
        db.close()
        
        if "Error" not in continuum_res:
            st.info(f"ℹ️ **Continuum Simulation**: Based on your initial joining date of **{fd['initial_doj']}**, "
                    f"your calculated entry pay at this institute on **{fd['date_of_joining']}** should be "
                    f"**Level {continuum_res['Joining_Level']}** at **Basic Pay ₹{continuum_res['Joining_Basic']:,}**.")
            
            # Store Calculation for Tab 2 usage
            st.session_state['continuum_data'] = continuum_res
            # Update Total Past Years (Continuum Logic overrides manual input effectively)
            st.session_state['faculty_data']['past_service_years'] = continuum_res['Total_Past_Years']
            
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.header("Checking Eligibility & Pay Fixation")
    
    if 'faculty_data' in st.session_state and st.session_state['faculty_data'].get('name'):
        data = st.session_state['faculty_data'].copy()
        
        # OVERRIDE with Continuum Data if available
        # User requested: "pass this... as the new baseline"
        if 'continuum_data' in st.session_state:
            c_data = st.session_state['continuum_data']
            data['current_level'] = c_data['Joining_Level']
            data['current_basic'] = c_data['Joining_Basic']
            # Note: We are checking eligibility FROM the joining date now?
            # logic_eligibility uses data['current_level'] to find NEXT level.
            # If we pass Joining Level, we are checking "What is the Next Level after Joining?".
            st.caption(f"Using Calculated Baseline: Level {data['current_level']} | Basic {data['current_basic']}")
            
        st.info(f"Evaluating Profile for: **{data['name']}**")
        
        # Determine target level
        levels = ["10", "11", "12", "13A1", "14"]
        try:
            curr_idx = levels.index(str(data['current_level']))
            target = levels[min(curr_idx+1, len(levels)-1)]
        except:
            target = "11"
            
        res = evaluate_cas_eligibility(data, target)
        
        if res['eligible']:
            st.success(f"✅ Eligible for Promotion to Level {res['target_level']}")
            
            c1, c2 = st.columns(2)
            c1.metric(" Promotion Due Date", str(res['due_date']))
            
            # Store for Arrears View
            st.session_state['arrears_config'] = {
                'start_date': res['due_date'],
                'target_level': res['target_level']
            }
            
            if res['flags']:
                st.warning(f"Exemptions Applied: {', '.join(res['flags'])}")
                
            # Fixation Section
            st.divider()
            st.subheader("Indicative Pay Fixation")
            
            db = SessionLocal()
            fix = calculate_fixation(data['current_basic'], data['current_level'], res['target_level'], db)
            
            if "new_basic" in fix:
                fc1, fc2 = st.columns(2)
                fc1.metric("Present Pay", f"₹ {fix['old_basic']:,}")
                fc2.metric("Fixed Pay (On Due Date)", f"₹ {fix['new_basic']:,}", delta=f"Cell {fix['new_cell']}")
                
                # Projection Logic
                from src.logic_fixation import calculate_projected_pay
                proj = calculate_projected_pay(fix['new_basic'], res['target_level'], res['due_date'], db)
                
                st.divider()
                st.subheader("Projected Current Pay (Today)")
                st.caption(f"If promoted on {res['due_date']}, applying annual increments till today:")
                
                pc1, pc2 = st.columns([1, 2])
                pc1.metric("Projected Basic (Today)", f"₹ {proj['projected_basic']:,}")
                
                if proj['increments']:
                    with pc2.expander("View Increment History"):
                        st.table(proj['increments'])
            else:
                st.error(fix.get("error", "Fixation Calculation Failed"))
            
            db.close()
            
        else:
            st.error(f"❌ Pending Requirement: {res['reason']}")
            if res['due_date']:
                st.write(f"Projected Future Due Date: {res['due_date']}")
    
    # CUMULATIVE SIMULATION BLOCK (If applicable)
    if 'faculty_data' in st.session_state:
        fd = st.session_state['faculty_data']
        # If user explicitly said "No Past Promotions" (checkbox unchecked)
        # And we have initial DOJ
        if not fd.get('has_past_promotions', False) and fd.get('initial_doj'):
            st.divider()
            st.subheader("🔁 Cumulative CAS Simulation (Backlog)")
            st.info("Since you indicated no past promotions, we simulated your career path to identify pending backlog promotions.")
            
            from src.logic_cumulative import evaluate_cumulative_promotions
            from src.database import SessionLocal
            
            db = SessionLocal()
            try:
                events, final_lvl, final_basic = evaluate_cumulative_promotions(fd, db)
                
                if events:
                    st.write("### Identified Promotion Backlog")
                    st.table(events)
                    st.success(f"Based on simulation, your **Current Status** should be **Level {final_lvl}** with Basic **₹{final_basic:,}**.")
                else:
                    st.warning("Simulation ran but found no eligible promotions in the backlog period.")
            except Exception as e:
                st.error(f"Simulation Error: {e}")
            finally:
                db.close()
    else:
        st.warning("Please complete and save the Profile in the 'Profile Entry' tab first.")
    
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    # Wrapper for reports to look integrated
    if 'faculty_data' in st.session_state and st.session_state['faculty_data'].get('name'):
        # TEMPORARY CONTEXT OVERRIDE for Arrears Engine
        # User requested to pass Continuum Baseline to Logic Arrears
        original_data = st.session_state['faculty_data'].copy()
        
        if 'continuum_data' in st.session_state:
            c_data = st.session_state['continuum_data']
            # We inject the Joining Status as the "Current Status" for the calculator's baseline
            st.session_state['faculty_data']['current_level'] = c_data['Joining_Level']
            st.session_state['faculty_data']['current_basic'] = c_data['Joining_Basic']
            st.caption(f"ℹ️ Arrears Calculator using Continuum Baseline: Level {c_data['Joining_Level']} | Basic {c_data['Joining_Basic']}")
            
        try:
            reports.show()
        finally:
            # RESTORE original manual inputs so Profile Tab stays consistent
            st.session_state['faculty_data'] = original_data
    else:
        st.warning("Please complete the Profile Entry first.")
    st.markdown('</div>', unsafe_allow_html=True)
