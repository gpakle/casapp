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
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.header("Checking Eligibility & Pay Fixation")
    
    if 'faculty_data' in st.session_state and st.session_state['faculty_data'].get('name'):
        data = st.session_state['faculty_data']
        st.info(f"Evaluating Profile for: **{data['name']}** | Current Level: **{data['current_level']}**")
        
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
            st.error(f"❌ Not Eligible for Promotion: {res['reason']}")
            if res['due_date']:
                st.write(f"Projected Future Due Date: {res['due_date']}")
    else:
        st.warning("Please complete and save the Profile in the 'Profile Entry' tab first.")
    
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    # Wrapper for reports to look integrated
    if 'faculty_data' in st.session_state and st.session_state['faculty_data'].get('name'):
        reports.show()
    else:
        st.warning("Please complete the Profile Entry first.")
    st.markdown('</div>', unsafe_allow_html=True)
