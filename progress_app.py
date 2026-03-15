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

# 2. MASTER MAPPING
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
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 30)
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

        pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, " Milestone Item", 1, 0, 'L', True)
        pdf.cell(35, 8, " Status", 1, 0, 'C', True)
        pdf.cell(95, 8, " Remarks", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {str(log.get(s_key, 'Pending'))}", 1, 0, 'C')
            pdf.cell(95, 7, f" {str(log.get(n_key,'-'))}", 1, 1)

    if logo_path: os.unlink(logo_path)
    return bytes(pdf.output())

# --- DATA FETCH ---
@st.cache_data(ttl=600)
def get_master_data():
    try:
        c_res = conn.table("customer_master").select("name").execute()
        j_res = conn.table("job_master").select("job_code").execute()
        return [d['name'] for d in c_res.data], [d['job_code'] for d in j_res.data]
    except: return [], []

customers, jobs = get_master_data()

tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# --- TAB 1: NEW ENTRY ---
with tab1:
    st.subheader("📋 Project Update")
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        if res and res.data: last_data = res.data[0]

    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cust = c1.selectbox("Customer", [""] + customers, index=customers.index(last_data['customer'])+1 if last_data.get('customer') in customers else 0)
        f_eq = c2.text_input("Equipment", value=last_data.get('equipment', ""))
        
        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        for label, skey, nkey in MILESTONE_MAP:
            pk = f"{skey}_prog"
            col1, col2, col3 = st.columns([1.5, 1, 2])
            
            opts = ["Pending", "In-Progress", "Completed", "NA", "Hold", "Approved"]
            prev_status = last_data.get(skey, "Pending")
            m_responses[skey] = col1.selectbox(label, opts, index=opts.index(prev_status) if prev_status in opts else 0, key=f"s_{skey}")
            
            # Use Slider for Progress % (Old Logic restored)
            m_responses[pk] = col2.slider("Prog %", 0, 100, value=int(last_data.get(pk, 0)), key=f"p_{skey}")
            m_responses[nkey] = col3.text_input("Remarks", value=last_data.get(nkey, ""), key=f"n_{skey}")

        if st.form_submit_button("🚀 SUBMIT UPDATE", use_container_width=True):
            avg_p = sum([m_responses[f"{m[1]}_prog"] for m in MILESTONE_MAP]) // len(MILESTONE_MAP)
            payload = {"customer": f_cust, "job_code": f_job, "equipment": f_eq, "overall_progress": avg_p, **m_responses}
            conn.table("progress_logs").insert(payload).execute()
            st.success(f"✅ Saved! Total Progress: {avg_p}%")
            st.cache_data.clear(); st.rerun()

# --- TAB 2: ARCHIVE (FIXED STATUS BARS) ---
with tab2:
    st.subheader("📂 Report Archive")
    f1, f2 = st.columns(2)
    sel_c = f1.selectbox("Filter by Customer", ["All"] + customers)
    
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    res = query.execute()
    data = res.data if res else []
    
    if data:
        st.download_button("📥 Download PDF", data=generate_pdf(data), file_name="BG_Archive.pdf", mime="application/pdf")
        
        for log in data:
            with st.expander(f"📦 {log.get('job_code')} - {log.get('customer')}"):
                # Total Project Bar
                ov_p = int(log.get('overall_progress', 0))
                st.write(f"**Total Completion: {ov_p}%**")
                st.progress(min(max(ov_p / 100.0, 0.0), 1.0))
                st.divider()

                # RESTORED OLD LOGIC: Individual milestone bars
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_status, c_bar, c_note = st.columns([1.5, 1, 1.5])
                    
                    # Data fetching
                    m_status = log.get(skey, "Pending")
                    m_prog = int(log.get(pk, 0))
                    m_note = log.get(nkey, "-")
                    
                    c_status.write(f"**{label}**")
                    c_status.caption(f"Status: {m_status}")
                    
                    with c_bar:
                        st.progress(m_prog / 100.0)
                        st.caption(f"Progress: {m_prog}%")
                        
                    c_note.write(f"_{m_note}_")
                    st.write("") # Spacer

# --- TAB 3: MASTERS ---
with tab3:
    st.subheader("🛠️ Master Management")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_cust"):
            new_c = st.text_input("Customer Name")
            if st.form_submit_button("Add Customer"):
                conn.table("customer_master").insert({"name": new_c}).execute()
                st.cache_data.clear(); st.rerun()
    with col2:
        with st.form("add_job"):
            new_j = st.text_input("Job Code")
            if st.form_submit_button("Add Job"):
                conn.table("job_master").insert({"job_code": new_j}).execute()
                st.cache_data.clear(); st.rerun()
