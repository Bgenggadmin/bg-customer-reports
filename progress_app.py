import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE
st.set_page_config(page_title="B&G Hub Verified", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# THE MASTER LIST - Every field from your requirement is here.
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

# --- FETCH MASTERS ---
try:
    customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
    jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])
except:
    customers, jobs = [], []

# --- PDF GENERATOR (VERIFIED: INCLUDES ALL 26 FIELDS) ---
def create_report_pdf(logs_list):
    pdf = FPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "C")
        pdf.line(10, 22, 200, 22); pdf.ln(5)
        
        # Header Box (8 Fields)
        pdf.set_font("Arial", "B", 8)
        h = [
            ("Customer", log.get('customer')), ("Job Code", log.get('job_code')),
            ("Equipment", log.get('equipment')), ("Engineer", log.get('engineer')),
            ("PO No.", log.get('po_no')), ("PO Date", log.get('po_date')),
            ("PO Delivery", log.get('po_delivery_date')), ("Rev. Dispatch", log.get('exp_dispatch_date'))
        ]
        for i in range(0, len(h), 2):
            pdf.cell(30, 7, h[i][0], 1, 0, 'L'); pdf.cell(65, 7, str(h[i][1]), 1, 0)
            pdf.cell(30, 7, h[i+1][0], 1, 0, 'L'); pdf.cell(65, 7, str(h[i+1][1]), 1, 1)

        # Photo
        e_id = str(log.get('id'))
        try:
            url = conn.client.storage.from_("progress-photos").get_public_url(f"{e_id}.jpg")
            r = requests.get(url)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert('RGB')
                img.thumbnail((300, 300))
                buf = BytesIO(); img.save(buf, format='JPEG')
                pdf.image(buf, 75, pdf.get_y()+5, 55, 40); pdf.set_y(pdf.get_y()+50)
        except: pdf.ln(5)

        # Milestones (18 Fields)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(60, 7, " Milestone", 1); pdf.cell(35, 7, " Status", 1); pdf.cell(95, 7, " Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, skey, nkey in MILESTONES:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)
    return bytes(pdf.output())

# --- APP TABS ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("complete_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment")
        
        c4, c5, c6 = st.columns(3)
        f_po_n, f_po_d, f_eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Responsible Engineer")
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("PO Delivery Date")
        f_r_del = c8.date_input("Revised Dispatch Date")

        st.divider()
        cam_photo = st.camera_input("📸 Take One Progress Photo")
        
        # Milestone Logic
        m_responses = {}
        for label, skey, nkey in MILESTONES:
            r1, r2 = st.columns([1,2])
            opts = ["Pending", "In-Progress", "Hold", "Completed"]
            if "Drawing" in label: opts = ["Pending", "In-Progress", "Submitted", "Approved"]
            m_responses[skey] = r1.selectbox(label, opts)
            m_responses[nkey] = r2.text_input(f"Remarks: {label}")

        if st.form_submit_button("🚀 Final Sync All Data"):
            if not f_cust or not cam_photo:
                st.error("Missing Customer or Photo!")
            else:
                payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del)
                }
                payload.update(m_responses)
                res = conn.table("progress_logs").insert(payload).execute()
                if res.data:
                    new_id = str(res.data[0]['id'])
                    conn.client.storage.from_("progress-photos").upload(path=f"{new_id}.jpg", file=cam_photo.getvalue(), file_options={"upsert": "true"})
                    st.success("Synchronized Successfully!"); st.rerun()

with t2:
    data = conn.table("progress_logs").select("*").order("id", desc=True).execute().data
    if data:
        st.download_button("📥 Download Report", create_report_pdf(data), "BG_Report.pdf")
        for log in data:
            with st.expander(f"📦 Job: {log['job_code']} | ID: {log['id']}"):
                ca, cb = st.columns([1, 2])
                p_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
                ca.image(p_url)
                
                # Verified: Displays all PO and Delivery info in Archive
                with cb:
                    st.write(f"**Customer:** {log['customer']}")
                    st.write(f"**PO No:** {log['po_no']} | **PO Date:** {log['po_date']}")
                    st.write(f"**Delivery:** {log['po_delivery_date']} | **Revised:** {log['exp_dispatch_date']}")
                
                st.markdown("---")
                # Verified: All 9 Milestones in Archive
                for label, skey, nkey in MILESTONES:
                    r1, r2, r3 = st.columns([2, 1, 3])
                    r1.write(f"**{label}**")
                    r2.write(f"🟢 {log[skey]}" if log[skey] in ["Completed", "Approved", "Submitted"] else f"🟡 {log[skey]}")
                    r3.write(f"_{log[nkey]}_")

                if st.button("🗑️ Delete", key=f"del_{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    try: conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    except: pass
                    st.rerun()

with t3:
    st.subheader("Manage Masters")
    mc1, mc2 = st.columns(2)
    with mc1:
        nc = st.text_input("Add Customer")
        if st.button("Add Cust") and nc:
            conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
        for c in customers:
            st.write(f"• {c}")
    with mc2:
        nj = st.text_input("Add Job Code")
        if st.button("Add Job") and nj:
            conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
        for j in jobs:
            st.write(f"• {j}")
