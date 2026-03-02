import streamlit as st
import os
import io
from datetime import date
from PIL import Image

# 1. PAGE SETUP
st.set_page_config(page_title="B&G Progress Hub", layout="wide")

# --- CUSTOMER & JOB DROPDOWNS (Edit these lists as needed) ---
CUSTOMER_LIST = ["Divis Laboratories", "Dr. Reddy's", "Aurobindo Pharma", "Hetero Drugs", "Other"]
EQUIPMENT_LIST = ["Reactor", "Receiver", "Heat Exchanger", "Storage Tank", "Agitator", "Other"]
JOB_CODE_LIST = ["BG-234", "BG-235", "BG-500", "BG-501", "New Entry"]

try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing 'fpdf2' in requirements.txt")
    st.stop()

# Memory for multiple equipment entries
if 'all_jobs' not in st.session_state:
    st.session_state.all_jobs = []

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

st.title("🏗️ B&G Multi-Equipment Dispatcher")

# Global Customer Selection
selected_customer = st.selectbox("Select Customer Name", CUSTOMER_LIST)
if selected_customer == "Other":
    selected_customer = st.text_input("Enter New Customer Name")

with st.expander("➕ Add New Equipment / Job to Report", expanded=True):
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📋 Project & Equipment Identity")
        c1, c2 = st.columns(2)
        with c1:
            equipment_name = st.selectbox("Equipment Name", EQUIPMENT_LIST)
            if equipment_name == "Other":
                equipment_name = st.text_input("Enter Equipment Name")
            job_code = st.selectbox("B&G Job Code", JOB_CODE_LIST)
            if job_code == "New Entry":
                job_code = st.text_input("Enter New Job Code")
        with c2:
            item_code = st.text_input("Customer Item Code / ERP No.")
            po_no = st.text_input("PO Number")

        st.subheader("📅 PO & Schedule")
        p1, p2, p3 = st.columns(3)
        with p1: po_date = st.date_input("PO Date", value=date.today())
        with p2: target_dispatch = st.date_input("Target Dispatch")
        with p3: revised_dispatch = st.date_input("Revised Dispatch (If any)")

        st.divider()
        st.subheader("📊 Work Progress (9 Milestones)")
        milestones = ["Drawing Submission", "Drawing Approval", "RM Status", "Sub-deliveries Status", "Fabrication Status", "Buffing/Finishing Status", "Testing", "QC/Dispatch Status", "FAT"]
        ms_results = {}
        
        m_col1, m_col2 = st.columns(2)
        for i, m in enumerate(milestones):
            target_col = m_col1 if i < 5 else m_col2
            with target_col:
                s = st.selectbox(f"{m} Status", ["In-Progress", "Completed", "Pending", "N/A"], key=f"s_{m}")
                r = st.text_input(f"{m} Remarks", key=f"r_{m}")
                ms_results[m] = {"status": s, "remark": r}

        st.divider()
        st.subheader("📸 Progress Photos")
        cam_photo = st.camera_input("📷 Take Photo")
        uploaded_files = st.file_uploader("📁 Upload Gallery", accept_multiple_files=True)
        
        add_item = st.form_submit_button("✅ Add This Equipment to Report")

        if add_item:
            all_pics = []
            if cam_photo: all_pics.append(cam_photo)
            if uploaded_files: all_pics.extend(uploaded_files)
            
            st.session_state.all_jobs.append({
                "eq": equipment_name, "job": job_code, "item": item_code,
                "po": po_no, "po_date": po_date, "target": target_dispatch, "revised": revised_dispatch,
                "milestones": ms_results, "photos": all_pics
            })
            st.success(f"Added {equipment_name} to the list!")

# Review and Generate
if st.session_state.all_jobs:
    st.subheader(f"Current Report Items for {selected_customer}")
    for i, item in enumerate(st.session_state.all_jobs):
        st.write(f"{i+1}. {item['eq']} (Job: {item['job']})")

    if st.button("🗑️ Clear All Items"):
        st.session_state.all_jobs = []
        st.rerun()

    if st.button("🔨 Generate Combined PDF Report"):
        try:
            pdf = BG_Report()
            for item in st.session_state.all_jobs:
                pdf.add_page()
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Helvetica", "B", 10)
                
                def draw_row(l1, v1, l2, v2):
                    pdf.cell(45, 10, l1, 1, 0, 'L', True)
                    pdf.cell(50, 10, str(v1), 1, 0)
                    pdf.cell(45, 10, l2, 1, 0, 'L', True)
                    pdf.cell(50, 10, str(v2), 1, 1)

                draw_row("Customer", selected_customer, "Equipment", item['eq'])
                draw_row("Job Code", item['job'], "ERP Item Code", item['item'])
                draw_row("PO No.", item['po'], "PO Date", item['po_date'])
                draw_row("Target Dispatch", item['target'], "Revised Dispatch", item['revised'])

                pdf.ln(5)
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(60, 8, "Milestone", 1, 0, 'C', True)
                pdf.cell(40, 8, "Status", 1, 0, 'C', True)
                pdf.cell(90, 8, "Remarks", 1, 1, 'C', True)
                pdf.set_font("Helvetica", "", 9)
                for m, data in item['milestones'].items():
                    pdf.cell(60, 8, m, 1); pdf.cell(40, 8, data['status'], 1); pdf.cell(90, 8, data['remark'], 1, 1)

                for i, p in enumerate(item['photos']):
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(0, 10, f"Photo: {item['eq']} - {i+1}", align='C', new_x="LMARGIN", new_y="NEXT")
                    img_proc = process_photo(p)
                    temp_name = f"temp_{item['job']}_{i}.jpg"
                    with open(temp_name, "wb") as f: f.write(img_proc.getvalue())
                    pdf.image(temp_name, x=20, y=35, w=170)
                    os.remove(temp_name)

            pdf_bytes = bytes(pdf.output())
            st.download_button("📥 Download Combined PDF", data=pdf_bytes, file_name=f"BG_Combined_Report.pdf", mime="application/pdf")
            st.success("PDF Ready!")
        except Exception as e:
            st.error(f"Error: {e}")
