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
    except Exception: return [], []

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
                tmp_logo.write(logo_data); logo_path = tmp_logo.name
    except: pass

    for log in logs:
        pdf.add_page()
        pdf.set_fill_color(0, 51, 102); pdf.rect(0, 0, 210, 25, 'F')
        if logo_path: pdf.image(logo_path, x=12, y=5, h=15)
        pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 16)
        pdf.set_xy(70, 5); pdf.cell(130, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "L")
        pdf.set_font("Arial", "I", 10); pdf.set_xy(70, 14); pdf.cell(130, 5, "PROJECT PROGRESS REPORT", 0, 1, "L")
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 30)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        
        # Milestone Table in PDF
        pdf.ln(10); pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 8, " Milestone Item", 1); pdf.cell(35, 8, " Status", 1); pdf.cell(95, 8, " Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {log.get(s_key, 'Pending')} ({log.get(s_key+'_prog', 0)}%)", 1)
            pdf.cell(95, 7, f" {log.get(n_key, '-')}", 1, 1)

    output = pdf.output(dest='S')
    return bytes(output) if not isinstance(output, str) else output.encode('latin-1', 'replace')

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    st.subheader("📋 Select Project")
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        if res and res.data: last_data = res.data[0]

    with st.form("main_entry_form", clear_on_submit=True):
        st.subheader("📋 Project Details")
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers, index=customers.index(last_data['customer']) + 1 if last_data.get('customer') in customers else 0)
        c2.text_input("Selected Job", value=f_job, disabled=True)
        f_eq = c3.text_input("Equipment Name", value=last_data.get('equipment', ""))
        
        def safe_date(field):
            val = last_data.get(field)
            try: return datetime.strptime(val, "%Y-%m-%d") if val else datetime.now()
            except: return datetime.now()

        f_po_d = st.date_input("PO Date", value=safe_date('po_date'))
        
        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        
        # FIX: Ensure everything inside this loop is indented correctly
        for label, skey, nkey in MILESTONE_MAP:
            prog_key = f"{skey}_prog"
            col_stat, col_prog, col_note = st.columns([1.5, 1, 2])
            
            opts = ["Pending", "NA", "In-Progress", "Submitted", "Approved", "Ordered", "Received", "Hold", "Completed"]
            prev_status = last_data.get(skey, "Pending")
            m_responses[skey] = col_stat.selectbox(label, opts, index=opts.index(prev_status) if prev_status in opts else 0, key=f"s_{f_job}_{skey}")
            
            prev_prog = int(last_data.get(prog_key, 0))
            m_responses[prog_key] = col_prog.slider("Prog %", 0, 100, value=prev_prog, key=f"p_{f_job}_{skey}")
            
            m_responses[nkey] = col_note.text_input("Remarks", value=last_data.get(nkey, ""), key=f"n_{f_job}_{skey}")

        cam_photo = st.camera_input("Take Progress Photo")

        if st.form_submit_button("🚀 SUBMIT UPDATE"):
            if not f_cust or not f_job:
                st.error("Select Job/Customer!")
            else:
                try:
                    # Calculate overall average automatically
                    all_vals = [m_responses[f"{m[1]}_prog"] for m in MILESTONE_MAP]
                    overall_avg = sum(all_vals) // len(all_vals)
                    
                    entry_payload = {
                        "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                        "po_date": str(f_po_d), "overall_progress": overall_avg,
                        **m_responses
                    }
                    res = conn.table("progress_logs").insert(entry_payload).execute()
                    st.success(f"✅ Saved! Project is {overall_avg}% Complete.")
                    st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    st.subheader("📂 Report Archive")
    res = conn.table("progress_logs").select("*").order("id", desc=True).execute()
    if res and res.data:
        for log in res.data:
            with st.expander(f"📦 Job: {log.get('job_code')} | {log.get('customer')}"):
                # Top Overall Progress
                ov_p = int(log.get('overall_progress', 0))
                st.write(f"**Total Completion: {ov_p}%**")
                st.progress(ov_p / 100)
                
                st.markdown("---")
                # Individual Milestone Bars
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_s, c_p, c_r = st.columns([1.5, 1, 1.5])
                    
                    val = int(log.get(pk, 0))
                    c_s.write(f"**{label}:** {log.get(skey)}")
                    c_p.progress(val / 100)
                    c_p.caption(f"{val}%")
                    c_r.write(f"_{log.get(nkey, '-')}_")
    else: st.warning("No records found.")
