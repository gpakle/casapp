import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Database Setup
DATABASE_URL = "sqlite:///cas_app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------------------------------------------------------
# MASTER DATA MODELS
# -------------------------------------------------------------------

class MasterPayMatrix(Base):
    __tablename__ = "master_pay_matrix"
    id = Column(Integer, primary_key=True, index=True)
    pay_level = Column(String, nullable=False) # Updated to String for '13A' support
    cell_number = Column(Integer, nullable=False)
    basic_pay = Column(Integer, nullable=False)

class MasterDARates(Base):
    __tablename__ = "master_da_rates"
    id = Column(Integer, primary_key=True, index=True)
    effective_date = Column(Date, nullable=False)
    da_rate = Column(Float, nullable=False) # Percentage e.g. 17.0
    pay_commission = Column(Integer, default=7)
    notes = Column(String, nullable=True)

class MasterTASlabs(Base):
    __tablename__ = "master_ta_slabs"
    id = Column(Integer, primary_key=True, index=True)
    min_pay_level = Column(Integer, nullable=False) # e.g. 9 means >= Level 9
    city_type = Column(String, nullable=False) # 'Metro' or 'Other'
    fixed_amount = Column(Integer, nullable=False)

# -------------------------------------------------------------------
# USER DATA MODELS
# -------------------------------------------------------------------

class UserProfile(Base):
    __tablename__ = "user_profile"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    joining_date = Column(Date, nullable=False)
    institute_type = Column(String, nullable=False) # 'Govt', 'Aided'
    city_class = Column(String, nullable=False) # 'X', 'Y', 'Z'
    qualifications = Column(String, nullable=True) # JSON or comma-separated

    history = relationship("ServiceHistory", back_populates="user")

class ServiceHistory(Base):
    __tablename__ = "service_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), nullable=False)
    designation = Column(String, nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=True) # Null means current
    pay_level = Column(String, nullable=False) # e.g., "10", "11", "13A" (AGP equavelent)
    basic_pay = Column(Integer, nullable=False)
    
    user = relationship("UserProfile", back_populates="history")


# -------------------------------------------------------------------
# DB INITIALIZATION & SEEDING
# -------------------------------------------------------------------

def init_db():
    Base.metadata.create_all(bind=engine)
    seed_data()

def seed_data():
    db = SessionLocal()
    
    # Check if data exists
    if db.query(MasterPayMatrix).first():
        db.close()
        return

    print("Seeding database from CSVs...")
    data_dir = os.path.join(os.getcwd(), "data") # Assumes running from root
    
    try:
        # Seed Pay Matrix
        pm_path = os.path.join(data_dir, "pay_matrix.csv")
        if os.path.exists(pm_path):
            df_pm = pd.read_csv(pm_path)
            # Assuming CSV: pay_level, cell_number, basic_pay
            for _, row in df_pm.iterrows():
                obj = MasterPayMatrix(
                    pay_level=str(row['pay_level']), # Converted to String
                    cell_number=int(row['cell_number']),
                    basic_pay=int(row['basic_pay'])
                )
                db.add(obj)

        # Seed DA Rates
        da_path = os.path.join(data_dir, "da_rates.csv")
        if os.path.exists(da_path):
            df_da = pd.read_csv(da_path)
            # CSV: effective_date, da_rate, pay_commission, notes
            for _, row in df_da.iterrows():
                obj = MasterDARates(
                    effective_date=datetime.strptime(str(row['effective_date']), "%Y-%m-%d").date(),
                    da_rate=float(row['da_rate']),
                    pay_commission=int(row['pay_commission']),
                    notes=str(row['notes']) if pd.notna(row['notes']) else None
                )
                db.add(obj)
        
        # Seed TA Slabs
        ta_path = os.path.join(data_dir, "ta_slabs.csv")
        if os.path.exists(ta_path):
            df_ta = pd.read_csv(ta_path)
            # CSV: min_pay_level, city_type, fixed_amount
            for _, row in df_ta.iterrows():
                # Map City Types if needed, assuming CSV matches model
                obj = MasterTASlabs(
                    min_pay_level=int(row['min_pay_level']),
                    city_type=row['city_type'],
                    fixed_amount=int(row['fixed_amount'])
                )
                db.add(obj)

        db.commit()
        print("Database seeded successfully.")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
