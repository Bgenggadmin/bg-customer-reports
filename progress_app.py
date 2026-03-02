import streamlit as st
import os
import io
from datetime import date
from PIL import Image

st.set_page_config(page_title="B&G Project Hub", layout="wide")

# --- CUSTOMER & JOB DROPDOWNS ---
CUSTOMERS = ["Divis Laboratories", "Dr. Reddy's", "Aurobindo Pharma", "Hetero Drugs", "Other"]
JOB_CODES = ["BG-234", "BG-235", "BG-500", "BG-501", "New Job"]

try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing 'fpdf2' in requirements.txt")
    st.stop()

# Persistent memory for multiple equipments
if 'all_jobs' not in st.session_state:
    st.session_state.all_jobs = []

class BG_Summary_Report(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES", align='R', new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        indian_today = date.today().strftime("%d-%m-%Y")
        self.cell(0, 5, f"PROJECT STATUS REPORT - {indian_today}", align='R', new_x="LMARGIN", new_y="NEXT")
        self.ln(15)

def process_photo(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=60)
    return img_byte_arr

st.title("🏗️ B&G Multi-Equipment Summary Hub")

# 1. Global Project Info
customer_selection = st.selectbox("Select Customer", CUSTOMERS)
if customer_selection == "Other":
    customer_selection = st.text_input("Type Customer Name")

with st.expander("➕ Add Equipment to this Report", expanded=True):
    with st.form("item_form", clear_on_submit=True):
        st.subheader("📋 Equipment Identity")
        c1, c2, c3 = st.columns(3)
        with c1:
            eq_name = st.text_input("Equipment Name (e.g. 5KL Reactor)")
            j_code = st.selectbox("Job Code", JOB_CODES)
        with c2:
            i_code = st.text_input("ERP Item Code")
            p_no = st.text_input("PO Number")
        with c3:
            p_date = st.date_input("PO Date")
            d_date = st.date_input("Target Dispatch Date")

        st.divider()
        st.subheader("📊 Detailed Milestones (9 Points)")
        milestones = ["Drawing Submission", "Drawing Approval", "RM Status", "Sub-deliveries Status", "Fabrication Status", "Buffing/Finishing Status", "Testing", "QC/Dispatch Status", "FAT"]
        
        current_ms_data = {}
        # Creating two columns for the 9 milestones to keep it compact
        m_col1, m_col2 = st.columns(2)
        for idx, m in enumerate(milestones):
            target_col = m_col1 if idx < 5 else m_col2
            with target_col:
                s = st.selectbox(f"{m} Status", ["In-Progress", "Completed", "Pending", "N/A"], key=f"s_{m}")
                r = st.text_input(f"{m} Remarks", key=f"r_{m}")
                current_ms_data[m] = {"status": s, "remark": r}

        st.divider()
        pics = st.file_uploader("Upload 2-3 Photos for this Equipment", accept_multiple_files=True)
        cam = st.camera_input("Or Take Shop Floor Photo")
        
        add_btn = st.form_submit_button("✅ Save this Equipment")
        
        if add_btn:
            # Combine Camera and Uploaded pics
            all_current_pics = []
            if cam: all_current_pics.append(cam)
            if pics: all_current_pics.extend(pics)
            
            st.session_state.all_jobs.append({
                "eq": eq_name, "job": j_code, "item": i_code, "po": p_no, "po_date": p_date,
                "dispatch": d_date, "milestones": current_ms_data, "photos": all_current_pics
            })
            st.success(f"Added {eq_name} to the list!")

# 2. Review List
if st.session_state.all_jobs:
    st.subheader(f"📋 Items Added for {customer_selection}")
    for i, item in enumerate(st.session_state.all_jobs):
        st.write(f"{i+1}. **{item['eq']}** ({item['job']})")
    
    if st.button("🗑️ Clear All"):
        st.session_state.all_jobs = []
        st.rerun()

    if st.button("🔨 Generate FINAL COMBINED PDF"):
        pdf = BG_Summary_Report()
        
        # We loop through each added equipment and create its own detailed page
        for item in st.session_state.all_jobs:
            pdf.add_page()
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Helvetica", "B", 10)
            
            # Header Table for individual Item
            def dr(l1, v1, l2, v2):
                pdf.cell(45, 10, l1, 1, 0, 'L', True)
                pdf.cell(50, 10, str(v1), 1, 0)
                pdf.cell(45, 10, l2, 1, 0, 'L', True)
                pdf.cell(50, 10, str(v2), 1, 1)

            dr("Customer", customer_selection, "Equipment", item['eq'])
            dr("Job Code", item['job'], "ERP Item Code", item['item'])
            dr("PO No.", item['po'], "PO Date", item['po_date'].strftime("%d-%m-%Y"))
            dr("Target Dispatch", item['dispatch'].strftime("%d-%m-%Y"), "Report Date", date.today().strftime("%d-%m-%Y"))

            # Detailed Milestone Table
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(60, 8, "Milestone", 1, 0, 'C', True)
            pdf.cell(40, 8, "Status", 1, 0, 'C', True)
            pdf.cell(90, 8, "Remarks", 1, 1, 'C', True)
            
            pdf.set_font("Helvetica", "", 9)
            for m, data in item['milestones'].items():
                pdf.cell(60, 8, m, 1)
                pdf.cell(40, 8, data['status'], 1)
                pdf.cell(90, 8, data['remark'], 1, 1)

            # Equipment specific photos
            for i, p in enumerate(item['photos']):
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 10, f"Photo: {item['eq']} ({i+1})", align='C', new_x="LMARGIN", new_y="NEXT")
                img_proc = process_photo(p)
                temp_name = f"temp_{item['job']}_{i}.jpg"
                with open(temp_name, "wb") as f: f.write(img_proc.getvalue())
                pdf.image(temp_name, x=20, y=35, w=170)
                os.remove(temp_name)

        pdf_bytes = bytes(pdf.output())
        st.download_button("📥 Download Combined Report", data=pdf_bytes, file_name=f"B&G_Report_{customer_selection}.pdf")
