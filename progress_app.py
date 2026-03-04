import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE & MASTERS MAPPING
st.set_page_config(page_title="B&G Hub Master", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# The "Source of Truth" for all fields
FIELDS = [
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

# --- FETCH DATA ---
try:
    customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
    jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])
except:
    customers, jobs = [], []

# --- PDF GENERATOR ---
def create_report_pdf(logs_list):
    pdf = FPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "B&G ENGINEERING INDUSTRIES - PROGRESS REPORT", 0, 1, "C")
        pdf.line(10, 25, 200, 25)
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f" JOB: {log.get('job_code')} | CUSTOMER: {log.get('customer')}", 1, 1, "L", fill=False)
        
        # Pull Photo
        e_id = str(log.get('id'))
        try:
            url = conn.client.storage.from_("progress-photos").get_public_url(f"{e_id}.jpg")
            img_res = requests.get(url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((300, 300))
                buf = BytesIO()
                img.save(buf, format='JPEG')
                pdf.image(buf, 10, pdf.get_y() + 5, 50, 40)
                pdf.set_y(pdf.get_y() + 50)
        except: pdf.ln(5)

        # Milestone Table
        pdf.set_font("Arial", "B", 8)
        pdf.cell(60, 7, " Milestone", 1); pdf.cell(35, 7, " Status", 1); pdf.cell(95, 7, " Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, skey, nkey in FIELDS:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)
    return bytes(pdf.output())

# --- APP TABS ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("master_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment Name")
        
        c4, c5, c6 = st.columns(3)
        f_po_n, f_po_d, f_eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        
        st.divider()
        cam_photo = st.camera_input("📸 Capture Progress Photo")
        
        m_data = {}
        for label, skey, nkey in FIELDS:
            col_s, col_n = st.columns([1,2])
            opts = ["Pending", "In-Progress", "Hold", "Completed"]
            if "Drawing" in label: opts = ["Pending", "In-Progress", "Submitted", "Approved"]
            m_data[skey] = col_s.selectbox(label, opts)
            m_data[nkey] = col_n.text_input(f"Remarks: {label}")

        if st.form_submit_button("🚀 Synchronize Data"):
            if not f_cust or not cam_photo:
                st.error("Select Customer and Take Photo!")
            else:
                payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(datetime.now().date()), # Fallback
                    "exp_dispatch_date": str(datetime.now().date())
                }
                payload.update(m_data)
                res = conn.table("progress_logs").insert(payload).execute()
                if res.data:
                    new_id = str(res.data[0]['id'])
                    conn.client.storage.from_("progress-photos").upload(path=f"{new_id}.jpg", file=cam_photo.getvalue(), file_options={"upsert": "true"})
                    st.success("Entry Saved!"); st.rerun()

with t2:
    data = conn.table("progress_logs").select("*").order("id", desc=True).execute().data
    if data:
        st.download_button("📥 Download All Reports PDF", create_report_pdf(data), "BG_Full_Report.pdf")
        for log in data:
            with st.expander(f"📦 Job: {log['job_code']} | ID: {log['id']} ({log['customer']})"):
                # Header Section
                col_img, col_info = st.columns([1, 2])
                p_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
                col_img.image(p_url, caption=f"ID: {log['id']}")
                
                with col_info:
                    st.subheader("Job Details")
                    ca, cb = st.columns(2)
                    ca.write(f"**PO No:** {log['po_no']}")
                    cb.write(f"**Engineer:** {log['engineer']}")
                    ca.write(f"**Equipment:** {log['equipment']}")
                    cb.write(f"**Date:** {log['po_date']}")

                # Milestone Table Representation (Clean UI)
                st.markdown("---")
                st.write("### 📊 Status Tracking")
                for label, skey, nkey in FIELDS:
                    r1, r2, r3 = st.columns([2, 1, 3])
                    r1.write(f"**{label}**")
                    status_color = "🟢" if log[skey] in ["Completed", "Approved", "Submitted"] else "🟡"
                    r2.write(f"{status_color} {log[skey]}")
                    r3.write(f"_{log[nkey] if log[nkey] else 'No remarks'}_")
                
                if st.button("🗑️ Delete Entry", key=f"del_{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    st.rerun()

with t3:
    st.info("Manage Customer and Job lists here.")
    # (Keep previous Master logic here)
