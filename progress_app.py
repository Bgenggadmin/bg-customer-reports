import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os, requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE CONNECTION & CONFIG
st.set_page_config(page_title="B&G Hub Master", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATOR (VERIFIED 24+ FIELDS) ---
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
        
        # --- HEADER FIELDS (8 FIELDS) ---
        pdf.set_font("helvetica", "B", 8)
        h_data = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Engineer", log.get('engineer')), ("PO No.", log.get('po_no')),
            ("PO Date", log.get('po_date')), ("PO Delivery", log.get('po_delivery_date')),
            ("Revised Disp", log.get('exp_dispatch_date')), ("Entry ID", str(log.get('id')))
        ]
        for i in range(0, len(h_data), 2):
            pdf.cell(30, 7, h_data[i][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_data[i][1]), 1, 0)
            pdf.cell(30, 7, h_data[i+1][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_data[i+1][1]), 1, 1)

        # --- MILESTONE TABLE (9 ROWS / 18 FIELDS) ---
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone Item", 1, 0, 'L', True); pdf.cell(35, 7, " Status", 1, 0, 'L', True); pdf.cell(95, 7, " Detailed Remarks", 1, 1, 'L', True)
        
        pdf.set_font("helvetica", "", 8)
        ms_mapping = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), ("QC Status", 'qc_stat', 'qc_note'), ("FAT Status", 'fat_stat', 'fat_note')
        ]
        for label, skey, nkey in ms_mapping:
            pdf.cell(60, 6, label, 1)
            pdf.cell(35, 6, str(log.get(skey, '-')), 1)
            pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)

        # --- PHOTO INTEGRATION (UNIQUE FOLDER LOGIC) ---
        entry_id = str(log.get('id'))
        try:
            res = conn.client.storage.from_("progress-photos").list(path=entry_id)
            if res:
                pdf.ln(5)
                y_pos = pdf.get_y()
                for idx, f_obj in enumerate(res[:4]): # Show top 4
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{entry_id}/{f_obj['name']}")
                    img_data = requests.get(url).content
                    img = Image.open(BytesIO(img_data)).convert('RGB')
                    img.thumbnail((300, 400))
                    buf = BytesIO()
                    img.save(buf, format='JPEG', quality=60)
                    col = idx % 4
                    pdf.image(buf, 10 + (col * 48), y_pos, 40, 45)
        except: pass
    return bytes(pdf.output())

# --- DATA LOAD ---
customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])

t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# --- TAB 1: FORM (ALL 24+ FIELDS) ---
with t1:
    with st.form("main_sync_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", customers)
        f_job = c2.selectbox("Job Code", jobs)
        f_eq = c3.text_input("Equipment Name")
        
        c4, c5, c6 = st.columns(3)
        f_po_n = c4.text_input("PO Number")
        f_po_d = c5.date_input("PO Date")
        f_eng = c6.text_input("Responsible Engineer")
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("Contractual Delivery Date")
        f_r_del = c8.date_input("Estimated Dispatch Date")

        st.markdown("---")
        # 1. Drawing Sub (Unique Dropdown)
        r1a, r1b = st.columns([1,2])
        v1s = r1a.selectbox("Drawing Submission", ["In-Progress", "Submitted"])
        v1n = r1b.text_input("Remarks: Drawing Submission")
        
        # 2. Drawing App (Unique Dropdown)
        r2a, r2b = st.columns([1,2])
        v2s = r2a.selectbox("Drawing Approval", ["Pending", "Approved"])
        v2n = r2b.text_input("Remarks: Drawing Approval")

        def milestone_ui(label, key_id):
            ca, cb = st.columns([1,2])
            s = ca.selectbox(label, ["Pending", "In-Progress", "Hold", "Completed"], key=f"s_{key_id}")
            n = cb.text_input(f"Remarks: {label}", key=f"n_{key_id}")
            return s, n

        v3s, v3n = milestone_ui("RM Status", "rm")
        v4s, v4n = milestone_ui("Sub-deliveries", "sd")
        v5s, v5n = milestone_ui("Fabrication Status", "fb")
        v6s, v6n = milestone_ui("Buffing Status", "bf")
        v7s, v7n = milestone_ui("Testing Status", "ts")
        v8s, v8n = milestone_ui("QC Status", "qc")
        v9s, v9n = milestone_ui("FAT Status", "fa")

        st.markdown("---")
        f_photos = st.file_uploader("Upload Progress Photos", accept_multiple_files=True)

        if st.form_submit_button("🚀 Synchronize Data & Photos"):
            # DB INSERT
            res = conn.table("progress_logs").insert({
                "customer": f_cust, "job_code": f_job, "equipment": f_eq, "po_no": f_po_n, 
                "po_date": str(f_po_d), "engineer": f_eng, "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                "draw_sub": v1s, "draw_sub_note": v1n, "draw_app": v2s, "draw_app_note": v2n,
                "rm_status": v3s, "rm_note": v3n, "sub_del": v4s, "sub_del_note": v4n,
                "fab_status": v5s, "remarks": v5n, "buff_stat": v6s, "buff_note": v6n,
                "testing": v7s, "test_note": v7n, "qc_stat": v8s, "qc_note": v8n, "fat_stat": v9s, "fat_note": v9n
            }).execute()
            
            # UNIQUE ID FOLDER STORAGE
            if f_photos and res.data:
                new_id = str(res.data[0]['id'])
                for p in f_photos:
                    conn.client.storage.from_("progress-photos").upload(path=f"{new_id}/{p.name}", file=p.getvalue())
            st.success("Entry Locked and Synced!"); st.rerun()

# --- TAB 2: ARCHIVE & DELETE ---
with t2:
    sel_customer = st.selectbox("View by Customer", ["All"] + customers)
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_customer != "All": query = query.eq("customer", sel_customer)
    archive_data = query.execute().data
    
    if archive_data:
        if sel_customer != "All":
            st.download_button(f"📥 Download {sel_customer} Report", create_report_pdf(archive_data), f"{sel_customer}_Status.pdf")
        
        for entry in archive_data:
            col_info, col_del = st.columns([6, 1])
            col_info.write(f"**ID: {entry['id']}** | Job: {entry['job_code']} | {entry['customer']}")
            
            if col_del.button("🗑️", key=f"del_{entry['id']}"):
                # 1. Clean Storage Folder First
                try:
                    folder_files = conn.client.storage.from_("progress-photos").list(path=str(entry['id']))
                    if folder_files:
                        conn.client.storage.from_("progress-photos").remove([f"{entry['id']}/{f['name']}" for f in folder_files])
                except: pass
                # 2. Delete DB Entry
                conn.table("progress_logs").delete().eq("id", entry['id']).execute()
                st.warning(f"Deleted Entry {entry['id']}"); st.rerun()
            
            with st.expander("Full Data & Photo Preview"):
                # Gallery
                entry_photos = conn.client.storage.from_("progress-photos").list(path=str(entry['id']))
                if entry_photos:
                    gal = st.columns(6)
                    for i, photo in enumerate(entry_photos):
                        url = conn.client.storage.from_("progress-photos").get_public_url(f"{entry['id']}/{photo['name']}")
                        gal[i % 6].image(url)
                st.table({k: [v] for k, v in entry.items()})

# --- TAB 3: MASTERS ---
with t3:
    st.info("Add/Remove Masters below to update dropdowns in 'New Entry'.")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.subheader("Manage Customers")
        nc = st.text_input("Add Customer Name")
        if st.button("Save Customer") and nc:
            conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
    with m_col2:
        st.subheader("Manage Job Codes")
        nj = st.text_input("Add Job Code")
        if st.button("Save Job Code") and nj:
            conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
