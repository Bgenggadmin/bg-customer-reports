import streamlit as st
import os
import io
from datetime import date
from PIL import Image

# 1. PAGE SETUP
st.set_page_config(page_title="B&G Progress Hub", layout="wide")

try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing 'fpdf2' in requirements.txt")
    st.stop()

# --- DYNAMIC LIST MANAGEMENT ---
if 'customer_list' not in st.session_state:
    st.session_state.customer_list = ["Divis Laboratories", "Dr. Reddy's", "Aurobindo Pharma"]
if 'job_list' not in st.session_state:
    st.session_state.job_list = ["BG-234", "BG-235", "BG-500"]
if 'all_jobs' not in st.session_state:
    st.session_state.all_jobs = []

# Sidebar for Dynamic Entry
st.sidebar.header("⚙️ Data Management")
new_cust = st.sidebar.text_input("➕ Add New Customer")
if st.sidebar.button("Add Customer"):
    if new_cust and new_cust not in st.session_state.customer_list:
        st.session_state.customer_list.append(new_cust)

new_job = st.sidebar.text_input("➕ Add New Job Code")
if st.sidebar.button("Add Job Code"):
    if new_job and new_job not in st.session_state.job_list:
        st.session_state.job_list.append(new_job)

# --- PDF CLASS ---
class BG_Report(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES", align='R', new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 5, f"PROJECT PROGRESS REPORT - {date.today().strftime('%d-%m-%Y')}", align='R', new_x="LMARGIN", new_y="NEXT")
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

# Global Report Details
c_col1, c_col2 = st.columns(2)
with c_col1:
    selected_customer = st.selectbox("Select Customer Name", st.session_state.customer_list)
with c_col2:
    submitted_by = st.text_input("Report Submitted By (Engineer Name)")

st.divider()

# Equipment Entry Form
with st.expander("➕ Add Equipment Details to Report", expanded=True):
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📋 Equipment & PO Details")
        f1, f2, f3 = st.columns(3)
        with f1:
            equipment_name = st.text_input("Equipment Name (e.g. 5KL Reactor)")
            job_code = st.selectbox("B&G Job Code", st.session_state.job_list)
        with f2:
            item_code = st.text_input("Customer Item Code / ERP No.")
            po_no = st.text_input("PO Number")
        with f3:
            po_date = st.date_input("PO Date", format="DD/MM/YYYY")
            target_dispatch = st.date_input("Target Dispatch Date", format="DD/MM/YYYY")
            revised_dispatch = st.date_input("Revised Dispatch Date", format="DD/MM/YYYY")

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
        pics = st.file_uploader("Upload Progress Photos", accept_multiple_files=True)
        cam = st.camera_input("Take Shop Floor Photo")
        
        add_item = st.form_submit_button("✅ Add This Item")

        if add_item:
            all_pics = []
            if cam: all_pics.append(cam)
            if pics: all_pics.extend(pics)
            
            st.session_state.all_jobs.append({
                "eq": equipment_name, "job": job_code, "item": item_code,
                "po": po_no, "po_date": po_date, "target": target_dispatch, "revised": revised_dispatch,
                "milestones": ms_results, "photos": all_pics, "sub_by": submitted_by
            })
            st.success(f"Added {equipment_name} to the list!")

# --- FULL LOG SUMMARY AT BOTTOM ---
if st.session_state.all_jobs:
    st.divider()
    st.subheader(f"📋 Full Log Summary: {selected_customer}")
    
    # Building a complete data list for the summary table
    summary_data = []
    for item in st.session_state.all_jobs:
        # Flattening milestone statuses for the table view
        row = {
            "Equipment": item['eq'],
            "Job Code": item['job'],
            "ERP Code": item['item'],
            "PO No": item['po'],
            "PO Date": item['po_date'].strftime("%d-%m-%Y"),
            "Target Date": item['target'].strftime("%d-%m-%Y"),
            "Revised Date": item['revised'].strftime("%d-%m-%Y"),
            "Fab. Status": item['milestones']['Fabrication Status']['status'],
            "Testing": item['milestones']['Testing']['status'],
            "Photos": len(item['photos'])
        }
        summary_data.append(row)
    
    # Display full table
    st.dataframe(summary_data, use_container_width=True)

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🗑️ Clear All Items"):
            st.session_state.all_jobs = []
            st.rerun()
    with c2:
        if st.button("🔨 Generate Final PDF"):
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
                    draw_row("Job Code", item['job'], "Submitted By", item['sub_by'])
                    draw_row("PO No.", item['po'], "PO Date", item['po_date'].strftime("%d-%m-%Y"))
                    draw_row("Target Dispatch", item['target'].strftime("%d-%m-%Y"), "Revised Dispatch", item['revised'].strftime("%d-%m-%Y"))

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
                        t_name = f"t_{item['job']}_{i}.jpg"
                        with open(t_name, "wb") as f: f.write(img_proc.getvalue())
                        pdf.image(t_name, x=20, y=35, w=170)
                        os.remove(t_name)

                pdf_bytes = bytes(pdf.output())
                st.download_button("📥 Download PDF", data=pdf_bytes, file_name=f"BG_Report_{selected_customer}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")
