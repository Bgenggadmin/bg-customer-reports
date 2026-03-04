import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
import os

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font("helvetica", "B", 15)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "B&G ENGINEERING", 0, 1, "R")
        self.set_font("helvetica", "B", 8)
        self.cell(0, 5, "EVAPORATION | MIXING | DRYING", 0, 1, "R")
        self.ln(10)
        self.set_draw_color(0, 51, 102)
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Engineering Industries", 0, 0, "C")

def create_bulk_pdf(customer_name, logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" PROJECT PROGRESS REPORT - {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        pdf.ln(4)

        # Primary Info Table
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Submitted By", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Target Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_delivery_date', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Revised Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('exp_dispatch_date', 'N/A')}", 1, 1)
        
        pdf.ln(5)

        # Milestone Table with Individual Remarks
        pdf.set_font("helvetica", "B", 9); pdf.set_fill_color(220, 230, 241)
        pdf.cell(70, 8, " Milestone", 1, 0, "L", fill=True)
        pdf.cell(40, 8, " Status", 1, 0, "L", fill=True)
        pdf.cell(80, 8, " Remarks", 1, 1, "L", fill=True)

        pdf.set_font("helvetica", "", 8)
        ms = [
            ("Drawing Submission", log.get('draw_sub'), log.get('draw_sub_note')),
            ("Drawing Approval", log.get('draw_app'), log.get('draw_app_note')),
            ("RM Status", log.get('rm_status'), log.get('rm_note')),
            ("Sub-deliveries Status", log.get('sub_del'), log.get('sub_del_note')),
            ("Fabrication Status", log.get('fab_status'), log.get('remarks')),
            ("Buffing/Finishing Status", log.get('buff_stat'), log.get('buff_note')),
            ("Testing", log.get('testing'), log.get('test_note')),
            ("QC/Dispatch Status", log.get('qc_stat'), log.get('qc_note')),
            ("FAT", log.get('fat_stat'), log.get('fat_note'))
        ]
        for m_name, m_val, m_note in ms:
            pdf.cell(70, 7, f" {m_name}", 1)
            pdf.cell(40, 7, f" {m_val if m_val else 'In-Progress'}", 1)
            pdf.cell(80, 7, f" {m_note if m_note else ''}", 1, 1)

        # Photos logic
        folder_path = f"reports/{log.get('id')}"
        try:
            files = conn.client.storage.from_("progress-photos").list(folder_path)
            if files:
                pdf.ln(5); pdf.set_font("helvetica", "B", 9); pdf.cell(0, 6, "SHOP FLOOR MEDIA:", ln=True)
                y_start = pdf.get_y()
                for i, f in enumerate(files[:2]):
                    img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{folder_path}/{f['name']}")
                    resp = requests.get(img_url, timeout=5)
                    if resp.status_code == 200:
                        img_bytes = BytesIO(resp.content)
                        pdf.image(img_bytes, x=10 if i == 0 else 105, y=y_start, w=90, h=60)
        except: pass
    return bytes(pdf.output())

# --- DATA HELPERS ---
@st.cache_data(ttl=60)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return c, j
    except: return [], []

c_list, j_list = get_masters()

# --- APP LAYOUT ---
st.title("🏗️ B&G Progress Hub")
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        cust = col1.selectbox("Customer", c_list)
        job = col2.selectbox("Job Code", j_list)
        eq = col3.text_input("Equipment")
        
        col4, col5, col6 = st.columns(3)
        po_n = col4.text_input("PO No.")
        po_d = col5.date_input("PO Date")
        eng = col6.text_input("Engineer In-Charge")

        col7, col8 = st.columns(2)
        po_del = col7.date_input("Target Dispatch Date")
        rev_del = col8.date_input("Revised Dispatch Date")

        st.markdown("### 📊 Specific Milestone Updates")
        
        # DIFFERENT DROPDOWNS FOR DIFFERENT MILESTONES
        draw_opts = ["In-Progress", "Submitted", "Revised", "Approved", "N/A"]
        rm_opts = ["In-Progress", "Ordered", "Partially Received", "Received", "N/A"]
        fab_opts = ["In-Progress", "Shell Welding", "Jacket Welding", "Structure", "Completed"]
        test_opts = ["In-Progress", "Hydro-Test", "Pneumatic-Test", "Completed"]
        
        m1, n1 = st.columns([1, 2])
        d_sub = m1.selectbox("Drawing Submission", draw_opts)
        d_sub_n = n1.text_input("Drawing Sub Note")

        m2, n2 = st.columns([1, 2])
        d_app = m2.selectbox("Drawing Approval", ["In-Progress", "Approved", "Conditionally Approved"])
        d_app_n = n2.text_input("Drawing App Note")

        m3, n3 = st.columns([1, 2])
        rm_s = m3.selectbox("RM Status", rm_opts)
        rm_n = n3.text_input("RM Status Note")

        m4, n4 = st.columns([1, 2])
        fab_s = m4.selectbox("Fabrication Status", fab_opts)
        rem = n4.text_input("Fabrication Remarks (Main)")

        files = st.file_uploader("Upload Photos", accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync to Cloud"):
            res = conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "po_delivery_date": str(po_del), "exp_dispatch_date": str(rev_del),
                "draw_sub": d_sub, "draw_sub_note": d_sub_n,
                "draw_app": d_app, "draw_app_note": d_app_n,
                "rm_status": rm_s, "rm_note": rm_n,
                "fab_status": fab_s, "remarks": rem
            }).execute()
            if files and res.data:
                log_id = res.data[0]['id']
                for i, f in enumerate(files):
                    conn.client.storage.from_("progress-photos").upload(f"reports/{log_id}/img_{i}.jpg", f.getvalue())
            st.success("Cloud Sync Complete!"); st.rerun()

with t2:
    sel_cust = st.selectbox("Select Customer", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if sel_cust != "All" and data:
        pdf_bytes = create_bulk_pdf(sel_cust, data)
        st.download_button(f"📥 Download {sel_cust} Official PDF", pdf_bytes, f"BG_{sel_cust}.pdf", "application/pdf")
    
    if not data:
        st.info("No logs found for the selected customer.")
    else:
        for log in data:
            with st.expander(f"📦 {log.get('job_code')} - {log.get('equipment')}"):
                st.table({
                    "Milestone": ["Drawing Sub", "Drawing App", "RM Status", "Fabrication"],
                    "Status": [log.get('draw_sub'), log.get('draw_app'), log.get('rm_status'), log.get('fab_status')],
                    "Remarks": [log.get('draw_sub_note'), log.get('draw_app_note'), log.get('rm_note'), log.get('remarks')]
                })

with t3:
    if st.text_input("PIN", type="password") == "1234":
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader("Add Customer")
            c_name = st.text_input("Customer Name")
            if st.button("Add Customer"): 
                conn.table("customer_master").insert({"name": c_name}).execute()
                st.rerun()
        with col_m2:
            st.subheader("Add Job Code")
            j_code = st.text_input("Job Code (e.g. BG-500)")
            if st.button("Add Job Code"): 
                conn.table("job_master").insert({"job_code": j_code}).execute()
                st.rerun()
