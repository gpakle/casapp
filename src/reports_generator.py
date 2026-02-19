from fpdf import FPDF
from datetime import date
import pandas as pd

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'CAS Promotion Arrears Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, f'Generated on: {date.today().strftime("%Y-%m-%d")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_arrears_pdf(profile_data: dict, df: pd.DataFrame, due_date: date, target_level: str):
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # User Details
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Employee Details', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    # Infer designation if missing
    designation = profile_data.get('current_designation')
    if not designation:
        lvl = str(profile_data.get('current_level', ''))
        if lvl in ['10', '11', '12']: designation = "Assistant Professor"
        elif lvl == '13A1': designation = "Associate Professor"
        elif lvl == '14': designation = "Professor"
        else: designation = "Faculty"

    details = [
        f"Name: {profile_data.get('name', '')}",
        f"Designation: {designation}",
        f"Target Level: {target_level}",
        f"Promotion Effective Date: {due_date}",
        f"City Class: {profile_data.get('city_class', '')}"
    ]
    
    for d in details:
        pdf.cell(0, 6, d, 0, 1)
        
    pdf.ln(5)
    
    # Summary Metrics
    total_arrears = df['Total Arrears'].sum()
    months = len(df)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Summary', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 6, f"Total Arrears Payable:", 0, 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, f"Rs. {total_arrears:,.0f}", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 6, f"Period:", 0, 0)
    pdf.cell(0, 6, f"{months} Months ({df.iloc[0]['Month']} to {df.iloc[-1]['Month']})", 0, 1)
    
    pdf.ln(10)
    
    # Detailed Table
    pdf.set_font('Arial', 'B', 10)
    
    # Columns to show
    cols = ["Month", "Drawn Basic", "Due Basic", "Diff Basic", "Diff DA", "Diff HRA", "Total Arrears"]
    col_widths = [25, 25, 25, 25, 25, 25, 30]
    
    # Header Row
    for i, col in enumerate(cols):
        pdf.cell(col_widths[i], 8, col, 1, 0, 'C')
    pdf.ln()
    
    # Data Rows
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for i, col in enumerate(cols):
            val = row[col]
            if isinstance(val, (int, float)):
                txt = f"{val:,.0f}"
            else:
                txt = str(val)
            pdf.cell(col_widths[i], 7, txt, 1, 0, 'C')
        pdf.ln()

    # Output
    # In Streamlit, return bytes for download button
    return pdf.output(dest='S').encode('latin-1') # 'S' returns string, encode to bytes
