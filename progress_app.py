import streamlit as st
import os
import io
from datetime import date
from PIL import Image

# 1. PAGE SETUP (Must be first)
st.set_page_config(page_title="B&G Progress Hub", layout="wide")

# 2. PDF LIBRARY CHECK
try:
    from fpdf import FPDF
except ImportError:
    st.error("Error: 'fpdf2' library not found. Please ensure 'fpdf2' is in requirements.txt")
    st.stop()

# --- PDF CLASS ---
class BG_Report(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font('Helvetica', 'B', 16)
        self.cell(80) 
        self.cell(110, 10, 'B&G ENGINEERING INDUSTRIES', ln=True, align='R')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 5, 'PROJECT PROGRESS REPORT', ln=True, align='R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | B&G Engineering Industries', align='C')

# --- PHOTO COMPRESSION ---
def process_photo(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((1000, 1000)) 
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=55, optimize=True)
    return img_byte_arr

# --- APP UI ---
st.title("🏗️ B&G Professional Progress Dispatcher")

with st.form("main_form"):
    st.subheader("📋 Project & Equipment Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        customer = st.text_input("Customer Name")
        equipment_name = st.text_input("Equipment Name", placeholder="e.g. 5KL Reactor")
        job_code = st.text_input("B&G Job Code")
    with c2:
        item_code = st.text_input("Customer Item Code (ERP No)")
        po_no = st.text_input("PO Number")
    with c3:
        po_date = st.date_input("PO Date", value=date.today())
        exp_dispatch = st.date_input("Original Dispatch Date")

    st.subheader("📅 Schedule Status")
    sc1, sc2 = st.columns(2)
    with sc1:
        rev_dispatch = st.date_input("Revised Forecasted Dispatch")
    with sc2:
        shift_reason = st.text_input("Reason for Schedule Shift (If any)")

    st.divider()

    st.subheader("📊 Work Progress & Remarks")
    milestones = ["Drawing Submission", "Drawing Approval", "RM Status", 
                  "Sub-deliveries Status", "Fabrication Status", 
                  "Buffing/Finishing Status", "Testing", "QC/Dispatch Status", "FAT"]
    
    ms_data = {}
    for m in milestones:
        col_s, col_r = st.columns([1, 2])
        with col_s:
            status = st.selectbox(f"{m}", ["In-Progress", "Completed", "Pending", "N/A"], key=f"s_{m}")
        with col_r:
            remark = st.text_input(f"Remarks for {m}", key=f"r_{m}")
        ms_data[m] = {"status": status, "remark": remark}

    st.divider()
    st.subheader("📸 Progress Photos")
    uploaded_files = st.file_uploader("Upload from Gallery", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    cam_photo = st.camera_input("Take a Shop Floor Photo")
    
    submitted = st.form_submit_button("🔨 Generate Professional PDF")

# --- PDF GENERATION ---
if submitted:
    if not customer or not equipment_name:
        st.error("Please enter Customer Name and Equipment Name.")
    else:
        try:
            pdf = BG_Report()
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            
            # Row 1
            pdf.cell(45, 10, "Customer", 1, 0, 'L', True)
            pdf.cell(50, 10, customer, 1, 0)
            pdf.cell(45, 10, "Equipment", 1, 0, 'L', True)
            pdf.cell(50, 10, equipment_name, 1, 1)
            
            # Row 2
            pdf.cell(45, 10, "Job Code", 1, 0, 'L', True)
            pdf.cell(50, 10, job_code, 1, 0)
            pdf.cell(45, 10, "Cust. Item Code", 1, 0, 'L', True)
            pdf.cell(50, 10, item_code, 1, 1)
            
            # Row 3
            pdf.cell(45, 10, "PO No & Date", 1, 0, 'L', True)
            pdf.cell(50, 10, f"{po_no} / {po_date}", 1, 0)
            pdf.cell(45, 10, "Original Dispatch", 1, 0, 'L', True)
            pdf.cell(50, 10, str(exp_dispatch), 1, 1)

            # Row 4 (Revised)
            pdf.cell(45, 10, "Revised Dispatch", 1, 0, 'L', True)
            pdf.cell(145, 10, str(rev_dispatch), 1, 1)

            if shift_reason:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.multi_cell(190, 8, f"Status Update: {shift_reason}", border=1)

            # Table Header
            pdf.ln(5)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(60, 8, "Milestone", 1, 0, 'C', True)
            pdf.cell(40, 8, "Status", 1, 0, 'C', True)
            pdf.cell(90, 8, "Remarks", 1, 1, 'C', True)

            # Table Body
            pdf.set_font('Helvetica', '', 9)
            for m, vals in ms_data.items():
                pdf.cell(60, 8, m, 1)
                pdf.cell(40, 8, vals['status'], 1)
                pdf.cell(90, 8, vals['remark'], 1, 1)

            # Combine photos
            photos = []
            if uploaded_files: photos.extend(uploaded_files)
            if cam_photo: photos.append(cam_photo)

            for i, p in enumerate(photos):
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 10, f"Progress Photo {i+1}", ln=True, align='C')
                img_proc = process_photo(p)
                temp_fn = f"temp_{i}.jpg"
                with open(temp_fn, "wb") as f: f.write(img_proc.getvalue())
                pdf.image(temp_fn, x=20, y=30, w=170)
                os.remove(temp_fn)

            # Generate Download
            pdf_out = pdf.output()
            st.download_button("📥 Download PDF Report", data=pdf_out, file_name=f"B&G_{job_code}.pdf", mime="application/pdf")
            st.success("PDF Ready!")

        except Exception as e:
            st.error(f"Something went wrong while making the PDF: {e}")
