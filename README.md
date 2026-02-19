# CAS Promotion & Arrears Dashboard

Streamlit application to calculate promotion eligibility, pay fixation, and salary arrears for Engineering Faculty in Maharashtra State.

## Setup

1.  **Install Expectations**
    Ensure Python 3.8+ is installed.

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Setup**
    The application uses SQLite (`cas_app.db`). To initialize and seed the database with CSV data:
    ```bash
    python3 src/database.py
    ```
    *Note: Ensure `casapp/data/` contains all required CSV files.*

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

## Project Structure

- `src/database.py`: Database models and seeding logic.
- `src/logic_arrears.py`: Arrears calculation engine handling Pay, DA, HRA, and TA rules.
- `views/`: Streamlit UI modules for different sections.
- `app.py`: Main entry point.

## Features (Current Status)

- **Database**: Models defined for Pay Matrix, DA Rates, TA Slabs. Seeding logic implemented.
- **Arrears Engine**: Implemented Monthly Arrears Calculation with Maharashtra-specific rules (HRA slabs, Fixed TA).
- **UI**: Skeleton with Navigation, Profile Entry form, and Arrears Report view.
