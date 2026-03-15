import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image
import tempfile
import os

# 1. SETUP
st.set_page_config(page_title="B&G Hub 2.0", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection, ttl=60)

# 2. THE MASTER MAPPING
HEADER_FIELDS = ["customer", "job_code", "equipment", "po_no", "po_date", "engineer", "po_delivery_date", "exp_dispatch_date"]

MILESTONE_MAP = [
    ("Drawing Submission", "draw_sub", "draw_sub_note"),
    ("Drawing Approval", "draw_app", "draw_app_note"),
    ("RM Status", "rm_status", "rm_note"),
    ("Sub-deliveries", "sub_del", "sub_del_note"),
    ("Fabrication Status", "fab_status", "remarks"),
    ("Buffing Status", "buff_stat", "buff_note"),
    ("Testing Status", "testing", "test_note"),
    ("Dispatch Status", "qc_stat", "qc_note"),
    ("FAT Status", "fat_stat", "fat_note")
]

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def get_master_data():
    try:
        c_res = conn.table("customer_master").select("name").execute()
        cust_list = sorted([d['name'] for d in c_res.data]) if c_res and c_res.data else []
        j_res = conn.table("job_master").select("job_code").execute()
        job_list = sorted([d['job_code'] for d in j_res.data]) if j_res and j_res.data else []
        return cust_list, job_list
    except Exception:
        return [], []

customers, jobs = get_master_data()

# --- PDF ENGINE ---
def generate_pdf(logs):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    logo_path = None
    try:
        logo_data = conn.client.storage.from_("progress-photos").download("logo.png")
        if logo_data:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
                tmp_logo.write(logo_data)
                logo_path = tmp_logo.name
    except: pass

    for log in logs:
        pdf.add_page()
        pdf.set_fill_color(0, 51, 102); pdf.rect(0, 0, 210, 25, 'F')
        if logo_path: pdf.image(logo_path, x=12, y=5, h=15)
        
        pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 16)
        pdf.set_xy(70, 5); pdf.cell(130, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "L")
        pdf.set_font("Arial", "I", 10); pdf.set_xy(70, 14); pdf.cell(130, 5, "PROJECT PROGRESS REPORT", 0, 1, "L")
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 30)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        
        pdf.ln(2); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1 = HEADER_FIELDS[i]; f2 = HEADER_FIELDS[i+1] if i+1 < len(HEADER_FIELDS) else None
            pdf.cell(30, 7, f" {f1.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f1,''))}", 1, 0, 'L')
            if f2:
                pdf.cell(30, 7, f" {f2.replace('_',' ').title()}", 1, 0, 'L', True)
                pdf.cell(65, 7, f" {str(log.get(f2,''))}", 1, 1, 'L')
            else: pdf.ln(7)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 9); pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, " Milestone Item", 1, 0, 'L', True); 
        pdf.cell(45, 8, " Status & Progress", 1, 0, 'C', True); 
        pdf.cell(85, 8, " Remarks", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
        for label, skey, nkey in MILESTONE_MAP:
            status = str(log.get(skey, 'Pending'))
            prog = log.get(f"{skey}_prog", 0)
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(45, 7, f" {status} ({prog}%)", 1, 0, 'C')
            pdf.cell(85, 7, f" {str(log.get(nkey,'-'))}", 1, 1)

    output = pdf.output(dest='S')
    if logo_path: os.unlink(logo_path)
    return bytes(output) if not isinstance(output, str) else output.encode('latin-1', 'replace')

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    st.subheader("📋 Select Project")
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        if res and res.data:
            last_data = res.data[0]
            st.toast(f"Loaded details for {f_job}", icon="🔄")

    with st.form("main_entry_form", clear_on_submit=True):
        st.subheader("📋 Project Details")
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers, index=customers.index(last_data['customer']) + 1 if last_data.get('customer') in customers else 0)
        c2.text_input("Selected Job", value=f_job, disabled=True)
        f_eq = c3.text_input("Equipment Name", value=last_data.get('equipment', ""))
        
        c4, c5, c6 = st.columns(3)
        f_po_n = c4.text_input("PO Number", value=last_data.get('po_no', ""))
        def safe_date(field):
            val = last_data.get(field)
            try: return datetime.strptime(val, "%Y-%m-%d").date() if val else datetime.now().date()
            except: return datetime.now().date()
        
        f_po_d = c5.date_input("PO Date", value=safe_date('po_date'))
        f_eng = c6.text_input("Responsible Engineer", value=last_data.get('engineer', ""))
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("PO Delivery Date", value=safe_date('po_delivery_date'))
        f_r_del = c8.date_input("Revised Dispatch Date", value=safe_date('exp_dispatch_date'))

        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        for label, skey, nkey in MILESTONE_MAP:
            prog_key = f"{skey}_prog"
            col_stat, col_prog, col_note = st.columns([1.5, 1, 2])
            opts = ["Pending", "NA", "In-Progress", "Submitted", "Approved", "Ordered", "Received", "Hold", "Completed"]
            prev_status = last_data.get(skey, "Pending")
            m_responses[skey] = col_stat.selectbox(label, opts, index=opts.index(prev_status) if prev_status in opts else 0, key=f"s_{f_job}_{skey}")
            m_responses[prog_key] = col_prog.slider(f"{label} %", 0, 100, value=int(last_data.get(prog_key, 0)), key=f"p_{f_job}_{skey}")
            m_responses[nkey] = col_note.text_input(f"Remarks for {label}", value=last_data.get(nkey, ""), key=f"n_{f_job}_{skey}")

        st.divider()
        st.subheader("📸 Progress Capture")
        cam_photo = st.camera_input("Take Progress Photo")

        if st.form_submit_button("🚀 SUBMIT UPDATE", use_container_width=True):
            if not f_cust or not f_job:
                st.error("Select a Job Code and Customer first!")
            else:
                try:
                    # Calculate overall average automatically
                    all_progs = [m_responses[f"{m[1]}_prog"] for m in MILESTONE_MAP]
                    avg_progress = sum(all_progs) // len(all_progs)
                    
                    entry_payload = {
                        "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                        "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                        "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                        "overall_progress": avg_progress,
                        **m_responses
                    }
                    res = conn.table("progress_logs").insert(entry_payload).execute()
                    if cam_photo and res and res.data:
                        file_path = f"{res.data[0]['id']}.jpg"
                        conn.client.storage.from_("progress-photos").upload(file_path, cam_photo.getvalue())
                    st.success(f"✅ Saved! Overall Project is {avg_progress}% Complete.")
                    st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    st.subheader("📂 Report Archive")
    filter_c1, filter_c2 = st.columns(2)
    selected_cust = filter_c1.selectbox("🔍 Filter by Customer", ["All Customers"] + customers)
    report_type = filter_c2.selectbox("📅 Duration", ["All Time", "Current Week", "Current Month"])

    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if selected_cust != "All Customers": query = query.eq("customer", selected_cust)
    res = query.execute()
    filtered_data = res.data if res else []

    if filtered_data:
        pdf_bytes = generate_pdf(filtered_data)
        st.download_button("📥 Download PDF Report", pdf_bytes, "BG_Report.pdf", "application/pdf", use_container_width=True)
        
        for log in filtered_data:
            with st.expander(f"📦 Job: {log.get('job_code')} | {log.get('customer')}"):
                ov_p = log.get('overall_progress', 0)
                st.write(f"**Overall Project Completion: {ov_p}%**")
                st.progress(int(ov_p)/100)
                
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_s, c_p, c_r = st.columns([1.5, 1, 1.5])
                    c_s.write(f"**{label}:** {log.get(skey)}")
                    c_p.progress(int(log.get(pk, 0))/100)
                    c_p.caption(f"{log.get(pk, 0)}%")
                    c_r.write(f"_{log.get(nkey, '-')}_")
                
                # Image Display
                img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log.get('id')}.jpg")
                st.image(img_url, width=250, caption=f"Latest Photo for {log.get('job_code')}")

with tab3:
    st.header("🛠️ Master Data")
    c_m, j_m = st.columns(2)
    new_c = c_m.text_input("New Customer Name")
    if c_m.button("Add Customer") and new_c:
        conn.table("customer_master").insert({"name": new_c}).execute()
        st.cache_data.clear(); st.rerun()
    new_j = j_m.text_input("New Job Code")
    if j_m.button("Add Job") and new_j:
        conn.table("job_master").insert({"job_code": new_j}).execute()
        st.cache_data.clear(); st.rerun()
