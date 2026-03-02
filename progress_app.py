import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import os
from datetime import date

# --- PDF GENERATOR CLASS ---
class BG_Report(FPDF):
    def header(self):
        # Add Logo if it exists in GitHub
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        
        self.set_font('Arial', 'B', 15)
        self.cell(80) # Move to the right
        self.cell(110, 10, 'B&G ENGINEERING INDUSTRIES', ln=True, align='R')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'PROJECT PROGRESS REPORT', ln=True, align='R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | B&G Engineering Industries - Confidential', align='C')

# --- IMAGE COMPRESSION LOGIC (50-60KB Target) ---
def process_photo(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((1000, 1000)) # High res but optimized
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=55, optimize=True)
    return img_byte_arr

# --- APP UI ---
st.set_page_config(page_title="B&G Progress Hub", layout="wide")
st.title("🏗️ Professional Progress Dispatcher")

with st.form("report_form"):
    # Section 1: Project Identity
    st.subheader("📋 Project Identification")
    c1, c2, c3 = st.columns(3)
    with c1:
        customer = st.text_input("Customer Name")
        job_code = st.text_input("B&G Job Code")
    with c2:
        item_code = st.number_input("Customer Item Code (ERP No)", step=1, format="%d")
        po_no = st.text_input("PO Number")
    with c3:
        po_date = st.date_input("PO Date")
        exp_dispatch = st.date_input("Original Dispatch (per PO)")

    # Section 2: Schedule Alignment
    st.subheader("📅 Schedule Status")
    sc1, sc2 = st.columns(2)
    with sc1:
        rev_dispatch = st.date_input("Revised Forecasted Dispatch")
    with sc2:
        shift_reason = st.text_input("Reason for Schedule Shift (Leave blank if on schedule)")

    st.divider()

    # Section 3: The 9 Milestones + Remarks
    st.subheader("📊 Work Progress & Remarks")
    milestones = [
        "Drawing Submission", "Drawing Approval", "RM Status", 
        "Sub-deliveries Status", "Fabrication Status", 
        "Buffing/Finishing Status", "Testing", "QC/Dispatch Status", "FAT"
    ]
    
    ms_data = {}
    for m in milestones:
        col_s, col_r = st.columns([1, 2])
        with col_s:
            status = st.selectbox(f"{m} Status", ["Pending", "In-Progress", "Completed", "N/A"], key=f"s_{m}")
        with col_r:
            remark = st.text_input(f"{m} Remarks", placeholder="Enter specific details...", key=f"r_{m}")
        ms_data[m] = {"status": status, "remark": remark}

    st.divider()

    # Section 4: Photos
    st.subheader("📸 Progress Photos")
    uploaded_files = st.file_uploader("Upload up to 5 photos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    photo_caps = []
    if uploaded_files:
        for i, file in enumerate(uploaded_files):
            cap = st.text_input(f"Photo {i+1} Heading", value=f"Site Progress {i+1}")
            photo_caps.append(cap)

    submitted = st.form_submit_button("Generate Professional Report")

if submitted:
    pdf = BG_Report()
    pdf.add_page()
    
    # Header Grid
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    
    # Row 1
    pdf.cell(45, 10, "Customer", 1, 0, 'L', True)
    pdf.cell(50, 10, customer, 1, 0)
    pdf.cell(45, 10, "Job Code", 1, 0, 'L', True)
    pdf.cell(50, 10, job_code, 1, 1)
    
    # Row 2
    pdf.cell(45, 10, "Customer Item Code", 1, 0, 'L', True)
    pdf.cell(50, 10, str(item_code), 1, 0)
    pdf.cell(45, 10, "PO No & Date", 1, 0, 'L', True)
    pdf.cell(50, 10, f"{po_no} / {po_date}", 1, 1)

    # Row 3 (Schedule)
    pdf.cell(45, 10, "Original Dispatch", 1, 0, 'L', True)
    pdf.cell(50, 10, str(exp_dispatch), 1, 0)
    pdf.cell(45, 10, "Revised Dispatch", 1, 0, 'L', True)
    pdf.cell(50, 10, str(rev_dispatch), 1, 1)

    if shift_reason:
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(190, 8, f"Note on Schedule: {shift_reason}", 1, 1, 'L')

    # Status Table
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, "DETAILED PROGRESS BREAKDOWN", ln=True)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 8, "Milestone", 1, 0, 'C', True)
    pdf.cell(40, 8, "Status", 1, 0, 'C', True)
    pdf.cell(90, 8, "Remarks / Technical Notes", 1, 1, 'C', True)

    pdf.set_font('Arial', '', 9)
    for m, vals in ms_data.items():
        pdf.cell(60, 8, m, 1)
        pdf.cell(40, 8, vals['status'], 1)
        pdf.cell(90, 8, vals['remark'], 1, 1)

    # Photos on new pages
    if uploaded_files:
        for i, file in enumerate(uploaded_files):
            pdf.add_page()
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, photo_caps[i], ln=True, align='C')
            img_data = process_photo(file)
            temp_path = f"temp_img_{i}.jpg"
            with open(temp_path, "wb") as f: f.write(img_data.getvalue())
            pdf.image(temp_path, x=20, w=170)
            os.remove(temp_path)

    pdf_bytes = pdf.output(dest='S')
    st.download_button(label="📥 Download Saturday Dispatch PDF", data=pdf_bytes, file_name=f"Report_{job_code}.pdf", mime="application/pdf")
    st.success("Professional Report Ready for Dispatch!")
