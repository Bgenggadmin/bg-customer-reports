import streamlit as st
import os
import io
from datetime import date

# --- 1. MUST BE THE VERY FIRST LINE ---
st.set_page_config(page_title="B&G Progress Hub", layout="wide")

# --- 2. TRY-EXCEPT IMPORTS (Prevents Blank Screen) ---
try:
    from PIL import Image
    from fpdf import FPDF
except ImportError as e:
    st.error(f"Missing Library: {e}. Please check your requirements.txt")
    st.stop()

# --- 3. LOGO CHECK ---
# This looks for the logo and shows a warning instead of crashing if missing
LOGO_FILE = "logo.png"
if not os.path.exists(LOGO_FILE):
    st.warning(f"⚠️ {LOGO_FILE} not found in main folder. Report will generate without logo.")

# --- PDF CLASS ---
class BG_Report(FPDF):
    def header(self):
        if os.path.exists(LOGO_FILE):
            self.image(LOGO_FILE, 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(110, 10, 'B&G ENGINEERING INDUSTRIES', ln=True, align='R')
        self.ln(20)

# --- APP UI ---
st.title("🏗️ B&G Progress Dispatcher")

# Basic Test to see if app is alive
st.success("App is running! If you see this, the code is working.")

with st.form("input_form"):
    customer = st.text_input("Customer Name")
    job_code = st.text_input("Job Code")
    # Using a simple list for testing
    status = st.selectbox("Current Status", ["In-Progress", "Completed", "Pending"])
    
    submitted = st.form_submit_button("Generate Test PDF")

if submitted:
    if not customer:
        st.error("Please enter a customer name.")
    else:
        pdf = BG_Report()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Customer: {customer}", ln=True)
        pdf.cell(200, 10, txt=f"Job: {job_code}", ln=True)
        pdf.cell(200, 10, txt=f"Status: {status}", ln=True)
        
        pdf_output = pdf.output()
        st.download_button("📥 Download PDF", data=pdf_output, file_name="test.pdf")
