import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime, timedelta
from fpdf import FPDF
import requests
from io import BytesIO
import os

# 1. INITIALIZE
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font("helvetica", "B", 15)
        self.set_text_color(0, 51, 102) # Dark Blue
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

        # Primary Info Table - Using .get() to prevent KeyError
        pdf.set_font("helvetica", "B", 9)
        # Row 1
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment', 'N/A')}", 1, 1)
        # Row 2
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Submitted By", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        # Row 3
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date', 'N/A')}", 1, 1)
        # Row 4
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Target Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_delivery_date', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Revised Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('exp_dispatch_date', 'N/A')}", 1, 1)
        
        pdf.ln(5)

        # Milestone Table
        pdf.set_font("helvetica", "B", 9); pdf.set_fill_color(220, 230, 241)
        pdf.cell(70, 8, " Milestone", 1, 0, "L", fill=True)
        pdf.cell(40, 8, " Status", 1, 0, "L", fill=True)
        pdf.cell(80, 8, " Remarks", 1, 1, "L", fill=True)

        pdf.set_font("helvetica", "", 8)
        ms = [
            ("Drawing Submission", log.get('draw_sub')), ("Drawing Approval", log.get('draw_app')),
            ("RM Status", log.get('rm_status')), ("Sub-deliveries Status", log.get('sub_del')),
            ("Fabrication Status", log.get('fab_status')), ("Buffing/Finishing Status", log.get('buff_stat')),
            ("Testing", log.get('testing')), ("QC/Dispatch Status", log.get('qc_stat')), ("FAT", log.get('fat_stat'))
        ]
        for m_name, m_val in ms:
            pdf.cell(70, 7, f" {m_name}", 1)
            pdf.cell(40, 7, f" {m_val if m_val else 'In-Progress'}", 1)
            pdf.cell(80, 7, f" {log.get('remarks', '') if m_name == 'Fabrication Status' else ''}", 1, 1)

        # Photos Section (Error handling added)
        folder = f"reports/{log.get('id')}"
        try:
            files = conn.client.storage.from_("progress-photos").list(folder)
            if files:
                pdf.ln(5); pdf.set_font("helvetica", "B", 9); pdf.cell(0, 6, "SHOP FLOOR MEDIA:", ln=True)
                y_p = pdf.get_y()
                for i, f in enumerate(files[:2]):
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}")
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        img = BytesIO(resp.content)
                        x = 10 if i == 0 else 105
                        pdf.image(img, x=x, y=y_p, w=90, h=60)
        except Exception:
            pass
            
    return bytes(pdf.output())
        # Photos
        folder = f"reports/{log['id']}"
        try:
            files = conn.client.storage.from_("progress-photos").list(folder)
            if files:
                pdf.ln(5); pdf.set_font("helvetica", "B", 9); pdf.cell(0, 6, "SHOP FLOOR MEDIA:", ln=True)
                y_p = pdf.get_y()
                for i, f in enumerate(files[:2]):
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}")
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        img = BytesIO(resp.content)
                        x = 10 if i == 0 else 105
                        pdf.image(img, x=x, y=y_p, w=90, h=60)
        except: pass
    return bytes(pdf.output())

# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return c, j
    except: return [], []

c_list, j_list = get_masters()

# --- APP LAYOUT ---
st.title("🏗️ B&G Professional Dispatcher")
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

        st.markdown("### 📊 Milestone Status Update")
        m1, m2, m3 = st.columns(3)
        d_sub = m1.selectbox("Drawing Submission", ["In-Progress", "Completed"])
        d_app = m2.selectbox("Drawing Approval", ["In-Progress", "Approved"])
        rm_s = m3.selectbox("RM Status", ["In-Progress", "Received"])
        
        m4, m5, m6 = st.columns(3)
        sub_s = m4.selectbox("Sub-deliveries", ["In-Progress", "Received"])
        fab_s = m5.selectbox("Fabrication", ["In-Progress", "Completed"])
        buf_s = m6.selectbox("Buffing/Finishing", ["In-Progress", "Completed"])
        
        m7, m8, m9 = st.columns(3)
        test_s = m7.selectbox("Testing", ["In-Progress", "Completed"])
        qc_s = m8.selectbox("QC Status", ["In-Progress", "Ready"])
        fat_s = m9.selectbox("FAT", ["In-Progress", "Completed"])

        rem = st.text_area("Remarks")
        files = st.file_uploader("Upload Photos", accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync to Cloud"):
            res = conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "po_delivery_date": str(po_del), "exp_dispatch_date": str(rev_del),
                "draw_sub": d_sub, "draw_app": d_app, "rm_status": rm_s, "sub_del": sub_s,
                "fab_status": fab_s, "buff_stat": buf_s, "testing": test_s, "qc_stat": qc_s,
                "fat_stat": fat_s, "remarks": rem
            }).execute()
            if files:
                log_id = res.data[0]['id']
                for i, f in enumerate(files):
                    conn.client.storage.from_("progress-photos").upload(f"reports/{log_id}/img_{i}.jpg", f.getvalue())
            st.success("Cloud Sync Complete!"); st.rerun()

with t2:
    sel_cust = st.selectbox("Select Customer for Weekly Report", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if sel_cust != "All" and data:
        if st.button(f"📥 Download {sel_cust} Official PDF Report"):
            pdf_bytes = create_bulk_pdf(sel_cust, data)
            st.download_button("Click to Download", pdf_bytes, f"BG_{sel_cust}_Report.pdf", "application/pdf")
    
    for log in data:
        with st.expander(f"📦 {log['job_code']} - {log['equipment']}"):
            st.write(log) # Detailed view

with t3: # Admin Master Access
    if st.text_input("PIN", type="password") == "1234":
        c_name = st.text_input("New Customer")
        if st.button("Add"): conn.table("customer_master").insert({"name": c_name}).execute(); st.rerun()
