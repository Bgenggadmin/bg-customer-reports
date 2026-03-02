import streamlit as st
import os
import io
from datetime import date
from PIL import Image

st.set_page_config(page_title="B&G Project Hub", layout="wide")

# --- CONFIGURATION (Add new Customers/Jobs here) ---
CUSTOMERS = ["Divis Laboratories", "Dr. Reddy's", "Aurobindo Pharma", "Hetero Drugs", "Other"]
JOB_CODES = ["BG-234", "BG-235", "BG-500", "BG-501", "New Job"]

try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing 'fpdf2' in requirements.txt")
    st.stop()

if 'all_jobs' not in st.session_state:
    st.session_state.all_jobs = []

class BG_Summary_Report(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES", align='R', new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        # Indian Date Format in Header
        indian_today = date.today().strftime("%d-%m-%Y")
        self.cell(0, 5, f"PROJECT STATUS REPORT - {indian_today}", align='R', new_x="LMARGIN", new_y="NEXT")
        self.ln(15)

st.title("📑 B&G Multi-Equipment Reporter (India Edition)")

# 1. Selection
c_col1, c_col2 = st.columns(2)
with c_col1:
    customer = st.selectbox("Select Customer", CUSTOMERS)
    if customer == "Other":
        customer = st.text_input("Enter Customer Name")

with st.expander("➕ Add Equipment to this Project", expanded=True):
    with st.form("item_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            eq_name = st.text_input("Equipment Name (e.g. 5KL Reactor)")
            j_code = st.selectbox("Job Code", JOB_CODES)
        with f2:
            i_code = st.text_input("ERP Item Code")
            p_no = st.text_input("PO Number")
        with f3:
            # Date Input (Standard UI)
            d_date = st.date_input("Target Dispatch Date")
            status = st.selectbox("Overall Status", ["In-Progress", "Completed", "Ready for QC", "N/A"])
        
        remarks = st.text_area("Status Remarks")
        pics = st.file_uploader("Upload Photos (2-3 pics)", accept_multiple_files=True)
        
        add_btn = st.form_submit_button("✅ Add Item")
        
        if add_btn:
            st.session_state.all_jobs.append({
                "eq": eq_name, "job": j_code, "item": i_code,
                "po": p_no, "dispatch": d_date, "status": status,
                "remarks": remarks, "photos": pics
            })
            st.success(f"Added {eq_name} to list.")

if st.session_state.all_jobs:
    st.subheader("📋 Current Items List")
    for i, item in enumerate(st.session_state.all_jobs):
        st.write(f"{i+1}. **{item['eq']}** ({item['job']}) - {item['status']}")
    
    if st.button("🗑️ Clear List"):
        st.session_state.all_jobs = []
        st.rerun()

    if st.button("🔨 Generate Final PDF"):
        pdf = BG_Summary_Report()
        pdf.add_page()
        
        # Summary Table Header
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(40, 10, "Equipment", 1, 0, 'C', True)
        pdf.cell(25, 10, "Job Code", 1, 0, 'C', True)
        pdf.cell(30, 10, "Target Date", 1, 0, 'C', True)
        pdf.cell(95, 10, "Status Remarks", 1, 1, 'C', True)
        
        pdf.set_font("Helvetica", "", 8)
        photo_list = []

        for item in st.session_state.all_jobs:
            # Change Date Format to DD-MM-YYYY for the table
            formatted_date = item['dispatch'].strftime("%d-%m-%Y")
            
            pdf.cell(40, 10, item['eq'], 1)
            pdf.cell(25, 10, item['job'], 1)
            pdf.cell(30, 10, formatted_date, 1)
            pdf.multi_cell(95, 10, f"[{item['status']}] {item['remarks']}", border=1)
            
            if item['photos']:
                photo_list.append({"name": item['eq'], "pics": item['photos']})

        # Photos Pages
        for group in photo_list:
            for p in group['pics']:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 10, f"Photo: {group['name']}", align='C', new_x="LMARGIN", new_y="NEXT")
                img = Image.open(p)
                if img.mode != 'RGB': img = img.convert('RGB')
                img.thumbnail((800, 800))
                temp_io = io.BytesIO()
                img.save(temp_io, format="JPEG", quality=60)
                pdf.image(temp_io, x=20, y=30, w=170)

        pdf_bytes = bytes(pdf.output())
        st.download_button("📥 Download Final PDF", data=pdf_bytes, file_name=f"B&G_Report_{customer}.pdf")
