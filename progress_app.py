import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE
st.set_page_config(page_title="B&G Hub Master", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- A. DEFINE ALL FIELDS (The "Master List" to prevent missing data) ---
# Format: (Display Name, Database Column Name, Note Column Name)
MILESTONES = [
    ("Drawing Submission", "draw_sub", "draw_sub_note"),
    ("Drawing Approval", "draw_app", "draw_app_note"),
    ("RM Status", "rm_status", "rm_note"),
    ("Sub-deliveries", "sub_del", "sub_del_note"),
    ("Fabrication Status", "fab_status", "remarks"),
    ("Buffing Status", "buff_stat", "buff_note"),
    ("Testing Status", "testing", "test_note"),
    ("QC Status", "qc_stat", "qc_note"),
    ("FAT Status", "fat_stat", "fat_note")
]

# --- B. DATA FETCHING ---
customers_data = conn.table("customer_master").select("*").execute().data
jobs_data = conn.table("job_master").select("*").execute().data
customers = sorted([d['name'] for d in customers_data]) if customers_data else []
jobs = sorted([d['job_code'] for d in jobs_data]) if jobs_data else []

# --- C. PDF GENERATOR ---
class ProgressPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES - PROGRESS REPORT", 0, 1, "R")
        self.line(10, 22, 200, 22)
        self.ln(5)

def create_report_pdf(logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" JOB CODE: {log.get('job_code')} | REPORT DATE: {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        
        # Header Fields
        pdf.set_font("helvetica", "B", 8)
        h_info = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Engineer", log.get('engineer')), ("PO No.", log.get('po_no')),
            ("PO Date", log.get('po_date')), ("PO Delivery", log.get('po_delivery_date')),
            ("Revised Disp", log.get('exp_dispatch_date')), ("Entry ID", str(log.get('id')))
        ]
        for i in range(0, len(h_info), 2):
            pdf.cell(30, 7, h_info[i][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_info[i][1]), 1, 0)
            pdf.cell(30, 7, h_info[i+1][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_info[i+1][1]), 1, 1)

        # Photo (Direct ID.jpg fetch)
        e_id = str(log.get('id'))
        try:
            url = conn.client.storage.from_("progress-photos").get_public_url(f"{e_id}.jpg")
            r = requests.get(url)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert('RGB')
                img.thumbnail((350, 350))
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=75)
                pdf.image(buf, 75, pdf.get_y() + 5, 60, 45)
                pdf.set_y(pdf.get_y() + 55)
        except: pdf.ln(5)

        # Milestones
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone Item", 1, 0, 'L', True); pdf.cell(35, 7, " Status", 1, 0, 'L', True); pdf.cell(95, 7, " Remarks", 1, 1, 'L', True)
        pdf.set_font("helvetica", "", 8)
        for label, skey, nkey in MILESTONES:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)
    return bytes(pdf.output())

# --- D. APP UI ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment Name")
        
        c4, c5, c6 = st.columns(3)
        f_po_n = c4.text_input("PO Number")
        f_po_d = c5.date_input("PO Date")
        f_eng = c6.text_input("Responsible Engineer")
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("Contractual Delivery Date")
        f_r_del = c8.date_input("Estimated Dispatch Date")

        st.divider()
        cam_photo = st.camera_input("📸 Capture Progress Photo")
        
        st.write("### Milestone Status")
        m_responses = {}
        for label, skey, nkey in MILESTONES:
            col_s, col_n = st.columns([1,2])
            # Special dropdowns for Drawings
            opts = ["In-Progress", "Submitted"] if "Drawing Submission" in label else ["Pending", "Approved"] if "Drawing Approval" in label else ["Pending", "In-Progress", "Hold", "Completed"]
            m_responses[skey] = col_s.selectbox(label, opts)
            m_responses[nkey] = col_n.text_input(f"Remarks: {label}")

        if st.form_submit_button("🚀 Final Sync"):
            if not f_cust or not f_job or not cam_photo:
                st.error("Missing Customer, Job, or Photo!")
            else:
                # Build Data Payload
                payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del)
                }
                payload.update(m_responses)
                
                res = conn.table("progress_logs").insert(payload).execute()
                if res.data:
                    curr_id = str(res.data[0]['id'])
                    conn.client.storage.from_("progress-photos").upload(path=f"{curr_id}.jpg", file=cam_photo.getvalue(), file_options={"upsert": "true"})
                    st.success(f"Saved! ID: {curr_id}"); st.rerun()

with t2:
    sel_filter = st.selectbox("Filter by Customer", ["All"] + customers)
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_filter != "All": query = query.eq("customer", sel_filter)
    data = query.execute().data
    
    if data:
        st.download_button("📥 Download PDF Report", create_report_pdf(data), "BG_Report.pdf")
        for log in data:
            with st.expander(f"ID: {log['id']} | Job: {log['job_code']} | {log['customer']}"):
                col_i, col_d = st.columns([1,2])
                img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
                col_i.image(img_url, use_container_width=True)
                col_d.write(log)
                if st.button("🗑️ Delete", key=f"del_{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    try: conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    except: pass
                    st.rerun()

with t3:
    st.header("Master Data Management")
    ma, mb = st.columns(2)
    with ma:
        new_c = st.text_input("New Customer")
        if st.button("Add Cust") and new_c:
            conn.table("customer_master").insert({"name": new_c}).execute(); st.rerun()
        st.write(customers)
    with mb:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job") and new_j:
            conn.table("job_master").insert({"job_code": new_j}).execute(); st.rerun()
        st.write(jobs)
