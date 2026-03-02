import streamlit as st
import os
import io
from datetime import date
from PIL import Image

st.set_page_config(page_title="B&G Progress Hub", layout="wide")

try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing 'fpdf2' in requirements.txt")
    st.stop()

class BG_Report(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font("Helvetica", "B", 16)
        self.cell(80) 
        self.cell(110, 10, "B&G ENGINEERING INDUSTRIES", align='R', new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 5, "PROJECT PROGRESS REPORT", align='R', new_x="LMARGIN", new_y="NEXT")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Engineering Industries", align="C")

def process_photo(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=60)
    return img_byte_arr

st.title("🏗️ B&G Professional Dispatcher")

with st.form("main_form"):
    st.subheader("📋 Project & Equipment Details")
    c1, c2 = st.columns(2)
    with c1:
        customer = st.text_input("Customer Name")
        equipment_name = st.text_input("Equipment Name")
    with c2:
        job_code = st.text_input("B&G Job Code")
        item_code = st.text_input("Customer Item Code / ERP No.")

    st.subheader("📅 PO & Schedule")
    p1, p2, p3 = st.columns(3)
    with p1: po_no = st.text_input("PO Number")
    with p2: po_date = st.date_input("PO Date", value=date.today())
    with p3: exp_dispatch = st.date_input("Target Dispatch")

    st.divider()
    st.subheader("📊 Work Progress (9 Milestones)")
    milestones = ["Drawing Submission", "Drawing Approval", "RM Status", "Sub-deliveries Status", "Fabrication Status", "Buffing/Finishing Status", "Testing", "QC/Dispatch Status", "FAT"]
    ms_results = {}
    for m in milestones:
        col_s, col_r = st.columns([1, 2])
        with col_s: s = st.selectbox(f"{m}", ["In-Progress", "Completed", "Pending", "N/A"], key=f"s_{m}")
        with col_r: r = st.text_input(f"Remarks for {m}", key=f"r_{m}")
        ms_results[m] = {"status": s, "remark": r}

    st.divider()
    st.subheader("📸 Progress Photos")
    cam_photo = st.camera_input("📷 Take Photo")
    uploaded_files = st.file_uploader("📁 Upload Gallery", accept_multiple_files=True)
    submitted = st.form_submit_button("🔨 Generate Report")

if submitted:
    if not customer or not equipment_name:
        st.warning("⚠️ Customer and Equipment Name are required.")
    else:
        try:
            pdf = BG_Report()
            pdf.add_page()
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Helvetica", "B", 10)
            
            def draw_row(l1, v1, l2, v2):
                pdf.cell(45, 10, l1, 1, 0, 'L', True)
                pdf.cell(50, 10, str(v1), 1, 0)
                pdf.cell(45, 10, l2, 1, 0, 'L', True)
                pdf.cell(50, 10, str(v2), 1, 1)

            draw_row("Customer", customer, "Equipment", equipment_name)
            draw_row("Job Code", job_code, "ERP Item Code", item_code)
            draw_row("PO No.", po_no, "PO Date", po_date)
            draw_row("Target Dispatch", exp_dispatch, "Report Date", date.today())

            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(60, 8, "Milestone", 1, 0, 'C', True)
            pdf.cell(40, 8, "Status", 1, 0, 'C', True)
            pdf.cell(90, 8, "Remarks", 1, 1, 'C', True)
            pdf.set_font("Helvetica", "", 9)
            for m, data in ms_results.items():
                pdf.cell(60, 8, m, 1); pdf.cell(40, 8, data['status'], 1); pdf.cell(90, 8, data['remark'], 1, 1)

            all_pics = []
            if cam_photo: all_pics.append(cam_photo)
            if uploaded_files: all_pics.extend(uploaded_files)

            for i, p in enumerate(all_pics):
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 10, f"Progress Photo {i+1}", align='C', new_x="LMARGIN", new_y="NEXT")
                img_proc = process_photo(p)
                temp_name = f"temp_{i}.jpg"
                with open(temp_name, "wb") as f: f.write(img_proc.getvalue())
                pdf.image(temp_name, x=20, y=35, w=170)
                os.remove(temp_name)

            # THE FIX: Convert to bytes
            pdf_bytes = bytes(pdf.output())
            st.download_button("📥 Download Final PDF", data=pdf_bytes, file_name=f"BG_Report_{job_code}.pdf", mime="application/pdf")
            st.success("Report generated successfully!")
            
        except Exception as e:
            st.error(f"Error during PDF creation: {e}")
