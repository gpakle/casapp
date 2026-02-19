import streamlit as st
import datetime
from src.database import SessionLocal, UserProfile, ServiceHistory

def save_to_db(data):
    """
    Helper to save faculty_data to SQLite for persistence.
    """
    db = SessionLocal()
    try:
        # Check if user exists (simplistic check by name)
        user = db.query(UserProfile).filter(UserProfile.name == data['name']).first()
        if not user:
            user = UserProfile()
            db.add(user)
        
        user.name = data['name']
        user.institute_type = data['institute_type']
        # Map UI City Class to DB format ("X (Metro)" -> "X")
        user.city_class = data['city_class'].split()[0] 
        user.joining_date = data['date_of_joining']
        
        # STORE FULL DATA JSON in qualifications to enable full restore
        import json
        # Convert date objects to string for JSON serialization
        json_data = data.copy()
        for k, v in json_data.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                json_data[k] = v.isoformat()
        
        user.qualifications = json.dumps(json_data)
        
        db.commit()
        db.refresh(user)
        
        # Clear old history
        db.query(ServiceHistory).filter(ServiceHistory.user_id == user.id).delete()
        
        # Add Current Status
        curr = ServiceHistory(
            user_id=user.id,
            designation="Current Designation", # Placeholder as field wasn't in new form
            from_date=datetime.date.today(), # Placeholder
            to_date=None,
            pay_level=str(data['current_level']),
            basic_pay=int(data['current_basic'])
        )
        db.add(curr)
        db.commit()
    except Exception as e:
        st.error(f"DB Save Error: {e}")
    finally:
        db.close()

def get_all_profiles():
    db = SessionLocal()
    profiles = []
    try:
        users = db.query(UserProfile.name).all()
        profiles = [u[0] for u in users]
    except Exception as e:
        st.error(f"DB Load Error: {e}")
    finally:
        db.close()
    return profiles

def load_profile_data(name):
    db = SessionLocal()
    data = None
    try:
        user = db.query(UserProfile).filter(UserProfile.name == name).first()
        if user:
            # Reconstruct faculty_data dict from UserProfile + ServiceHistory
            # Note: The current DB schema doesn't store ALL fields perfectly (e.g. past_service_years, qualification dates)
            # as separate columns in UserProfile. They might be lost if we didn't update UserProfile model.
            # WAIT: src/database.py UserProfile only has: name, joining_date, institute_type, city_class, qualifications.
            # It DOES NOT have past_service_years, promoted dates, etc.
            # REQUIRED: We need to update UserProfile model OR store specific data in a JSON column if allowed.
            # Given constraints, we can try to infer or we MUST update the DB schema.
            # User asked "Where do we store profiles?".
            # Let's start by just loading what we have, but to fully restore the form we need those fields.
            # I will use the 'qualifications' column to store a JSON string of the full extra data for now, 
            # or better, update the DB structure. 
            # Since I cannot easily run migration migrations in this env without alembic, 
            # I will piggyback on 'qualifications' as a JSON storage for extended attributes if possible, 
            # OR just update the schema using sqlite alter command logic if I can.
            # actually, 'qualifications' is String. I can dump the whole dict there for restoration purposes.
            
            import json
            try:
                # Try to parse qualifications as JSON if we stored it that way
                extra_data = json.loads(user.qualifications)
                # If it's just a string like "M.Tech", this will fail or be just string
                if isinstance(extra_data, dict):
                    data = extra_data
                    # Overwrite key fields from columns to ensure consistency
                    data['name'] = user.name
                    data['date_of_joining'] = user.joining_date
                    data['institute_type'] = user.institute_type
                    # city_class might allow "X" vs "X (Metro)" mismatch, handle it
                    # stored "X", UI needs "X (Metro)"
                    # We need a mapper logic or just store UI string in JSON
            except:
                 # Legacy or simple string
                 data = {
                     "name": user.name,
                     "institute_type": user.institute_type,
                     "city_class": user.city_class, # might need mapping
                     "date_of_joining": user.joining_date,
                     "entry_qualification": user.qualifications, # Fallback
                     # Defaults for missing
                     "past_service_years": 0,
                     "acquired_mtech_date": None,
                     "acquired_phd_date": None,
                     "promoted_level_11_date": None,
                     "promoted_level_12_date": None,
                     "current_level": "10",
                     "current_basic": 57700
                 }
                 
            # Fetch current status from ServiceHistory
            last_hist = db.query(ServiceHistory).filter(ServiceHistory.user_id == user.id).order_by(ServiceHistory.id.desc()).first()
            if last_hist:
                data['current_level'] = last_hist.pay_level
                data['current_basic'] = last_hist.basic_pay
                
    except Exception as e:
        st.error(f"Error Loading Profile: {e}")
    finally:
        db.close()
    return data

def render_profile_form():
    # st.header("Faculty Comprehensive Profile") # Removed for cleaner UI in tabs
    
    # LOAD SECTION
    with st.expander("📂 Profile Management", expanded=False):
        profiles = get_all_profiles()
        
        c1, c2 = st.columns([3, 1])
        with c1:
            if profiles:
                selected_profile = st.selectbox("Select Existing Profile", profiles, label_visibility="collapsed")
            else:
                st.info("No profiles found.")
        
        with c2:
             if st.button("➕ New Profile"):
                 st.session_state['faculty_data'] = {}
                 st.rerun()

        if profiles:
            if st.button("Load Selected Profile"):
                loaded_data = load_profile_data(selected_profile)
                if loaded_data:
                    # Convert date strings back to objects if needed (from JSON load)
                    for k in ['date_of_joining', 'acquired_mtech_date', 'acquired_phd_date', 
                              'promoted_level_11_date', 'promoted_level_12_date']:
                        if k in loaded_data and isinstance(loaded_data[k], str):
                            try:
                                loaded_data[k] = datetime.date.fromisoformat(loaded_data[k])
                            except:
                                loaded_data[k] = None
                                
                    st.session_state['faculty_data'] = loaded_data
                    st.success(f"Loaded profile: {selected_profile}")
                    st.rerun()

    # Get values from session state if available
    defaults = st.session_state.get('faculty_data', {})
    
    with st.form("faculty_profile_form"):
        st.subheader("1. Core Attributes")
        name = st.text_input("Full Name", value=defaults.get('name', ''))
        
        # Indexes for selectboxes
        it_opts = ["Government", "Aided-BoG", "Unaided"]
        it_idx = it_opts.index(defaults.get('institute_type')) if defaults.get('institute_type') in it_opts else 0
        institute_type = st.selectbox("Institute Type", it_opts, index=it_idx)
        
        cc_opts = ["X (Metro)", "Y (Urban)", "Z (Rural)"]
        cc_idx = cc_opts.index(defaults.get('city_class')) if defaults.get('city_class') in cc_opts else 2
        city_class = st.selectbox("City Class (For HRA/TA)", cc_opts, index=cc_idx) 
        
        st.subheader("2. Past Service & Joining")
        past_service_years = st.number_input("Approved Past Service (Years)", min_value=0, value=defaults.get('past_service_years', 0))
        date_of_joining = st.date_input("Date of Joining Current Institute", min_value=datetime.date(1990, 1, 1), value=defaults.get('date_of_joining', datetime.date(2010, 1, 1)))
        
        st.subheader("3. Qualification Chronology")
        q_opts = ["B.E./B.Tech", "M.E./M.Tech", "Ph.D."]
        q_idx = q_opts.index(defaults.get('entry_qualification')) if defaults.get('entry_qualification') in q_opts else 1
        entry_qualification = st.selectbox("Qualification at Joining", q_opts, index=q_idx)
        
        acquired_mtech_date = st.date_input("Date of acquiring M.E./M.Tech (if acquired in-service)", value=defaults.get('acquired_mtech_date'), min_value=datetime.date(1995, 1, 1), max_value=datetime.date(2028, 12, 31))
        acquired_phd_date = st.date_input("Date of acquiring Ph.D. (if acquired in-service)", value=defaults.get('acquired_phd_date'), min_value=datetime.date(1995, 1, 1), max_value=datetime.date(2028, 12, 31))
        
        st.subheader("4. Promotion History (CAS)")
        promoted_level_11_date = st.date_input("Date Promoted to Sr. Scale (Level 11)", value=defaults.get('promoted_level_11_date'), min_value=datetime.date(1995, 1, 1), max_value=datetime.date(2028, 12, 31))
        promoted_level_12_date = st.date_input("Date Promoted to Sel. Grade (Level 12)", value=defaults.get('promoted_level_12_date'), min_value=datetime.date(1995, 1, 1), max_value=datetime.date(2028, 12, 31))
        
        st.subheader("5. Current Pay Status")
        l_opts = ["10", "11", "12", "13A1", "14"]
        l_idx = l_opts.index(str(defaults.get('current_level'))) if str(defaults.get('current_level')) in l_opts else 0
        current_level = st.selectbox("Current Pay Level", l_opts, index=l_idx)
        
        # Fetch Basic Pay Options from DB
        from src.database import MasterPayMatrix
        db = SessionLocal()
        pay_options = []
        try:
            # Query basic pay for selected level, ordered by cell (or basic pay)
            res = db.query(MasterPayMatrix.basic_pay)\
                    .filter(MasterPayMatrix.pay_level == current_level)\
                    .order_by(MasterPayMatrix.basic_pay).all()
            pay_options = [r[0] for r in res]
        except Exception as e:
            st.error(f"DB Error: {e}")
        finally:
            db.close()
            
        if not pay_options:
             # Fallback if DB empty or level not found
             st.warning(f"No pay matrix data found for Level {current_level}")
             current_basic = st.number_input("Current Basic Pay (₹)", min_value=50000, value=int(defaults.get('current_basic', 57700)), step=100)
        else:
             # Try to find index of loaded basic pay
             b_idx = 0
             loaded_basic = int(defaults.get('current_basic', 0))
             if loaded_basic in pay_options:
                 b_idx = pay_options.index(loaded_basic)
             current_basic = st.selectbox("Current Basic Pay (₹)", pay_options, index=b_idx)
        
        submit = st.form_submit_button("Save & Evaluate Eligibility")
        
        if submit:
            # Save all to st.session_state dictionary named 'faculty_data'
            faculty_data = {
                "name": name,
                "institute_type": institute_type,
                "city_class": city_class,
                "past_service_years": past_service_years,
                "date_of_joining": date_of_joining,
                "entry_qualification": entry_qualification,
                "acquired_mtech_date": acquired_mtech_date,
                "acquired_phd_date": acquired_phd_date,
                "promoted_level_11_date": promoted_level_11_date,
                "promoted_level_12_date": promoted_level_12_date,
                "current_level": current_level,
                "current_basic": current_basic
            }
            st.session_state['faculty_data'] = faculty_data
            
            # Also sync to DB for other modules
            save_to_db(faculty_data)
            
            st.success("Profile Saved Successfully!")
