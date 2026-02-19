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

## Key Features:
- **Career Continuum**: Simulate an entire career from First Service Date to Standardize Entry Pay.
- **Cumulative CAS Simulation**: For faculty with no past promotions, the system retroactively simulates all eligible promotions.
- **Arrears Calculation**: Accurate monthly arrears computation with 7th Pay Matrix rules (July Increment, HRA/DA Slabs).
- **Pay Fixation**: Standard 7th CPC Fixation Logic.
- **Profile Management**: Save/Load profiles with full history (stored as JSON in SQLite).

## Continuing Development on a New Machine

Yes! You can continue developing this app from any machine with Git and Python installed.

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/gpakle/casapp.git
    cd casapp
    ```

2.  **Set Up Environment**:
    ```bash
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install dependencies
    pip install -r requirements.txt
    ```

3.  **Initialize Database**:
    ```bash
    # Create and seed the database
    python3 src/database.py
    ```

4.  **Run the App**:
    ```bash
    streamlit run app.py
    ```

**Note for AI Assistants**: When opening this project on a new machine with an AI tool (like Cursor, Windsurf, or Antigravity), simply point the tool to the `casapp` folder. The presence of `src/` and `app.py` gives the AI full context to understand the architecture and continue development.
