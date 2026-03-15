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

# --- PDF ENGINE (FIXED ATTRIBUTE ERROR) ---
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
        # 1. Header
        pdf.set_fill_color(0, 51, 102); pdf.rect(0, 0, 210, 25, 'F')
        if logo_path: pdf.image(logo_path, x=12, y=5, h=15)
        pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 16)
        pdf.set_xy(70, 5); pdf.cell(130, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "L")
        pdf.set_font("Arial", "I", 10); pdf.set_xy(70, 14); pdf.cell(130, 5, "PROJECT PROGRESS REPORT", 0, 1, "L")
        
        # 2. Field Grid
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 30)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        pdf.ln(2); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
        
        for i in range(0, len(HEADER_FIELDS), 2):
            f1 = HEADER_FIELDS[i]
            f2 = HEADER_FIELDS[i+1] if i+1 < len(HEADER_FIELDS) else None
            pdf.cell(30, 7, f" {f1.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f1,''))}", 1, 0, 'L')
            if f2:
                pdf.cell(30, 7, f" {f2.replace('_',' ').title()}", 1, 0, 'L', True)
                pdf.cell(65, 7, f" {str(log.get(f2,''))}", 1, 1, 'L')
            else: pdf.ln(7)

        # 3. Table
        pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, " Milestone Item", 1, 0, 'L', True)
        pdf.cell(35, 8, " Status", 1, 0, 'C', True)
        pdf.cell(95, 8, " Remarks", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            status = str(log.get(s_key, 'Pending'))
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {status}", 1, 0, 'C')
            pdf.cell(95, 7, f" {str(log.get(n_key,'-'))}", 1, 1)

    # FIX: Clean output handling for FPDF2
    if logo_path: os.unlink(logo_path)
    return bytes(pdf.output()) # Simplified for compatibility

# --- MASTER DATA FETCH ---
@st.cache_data(ttl=600)
def get_master_data():
    try:
        c_res = conn.table("customer_master").select("name").execute()
        j_res = conn.table("job_master").select("job_code").execute()
        return [d['name'] for d in c_res.data], [d['job_code'] for d in j_res.data]
    except: return [], []

customers, jobs = get_master_data()

tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        if res and res.data: last_data = res.data[0]

    with st.form("main_form"):
        # ... [Keep your existing Tab 1 Form Fields here] ...
        st.subheader("📋 Project Details")
        c1, c2 = st.columns(2)
        f_cust = c1.selectbox("Customer", [""] + customers, index=customers.index(last_data['customer'])+1 if last_data.get('customer') in customers else 0)
        f_eq = c2.text_input("Equipment", value=last_data.get('equipment', ""))
        
        # New Progress Bar Input for Tab 1
        st.divider()
        m_responses = {}
        for label, skey, nkey in MILESTONE_MAP:
            pk = f"{skey}_prog"
            col1, col2, col3 = st.columns([2, 1, 2])
            m_responses[skey] = col1.selectbox(label, ["Pending", "In-Progress", "Completed", "NA"], key=f"s_{skey}")
            m_responses[pk] = col2.number_input("%", 0, 100, value=int(last_data.get(pk, 0)), key=f"p_{skey}")
            m_responses[nkey] = col3.text_input("Note", value=last_data.get(nkey, ""), key=f"n_{skey}")

        if st.form_submit_button("🚀 SUBMIT"):
            payload = {"customer": f_cust, "job_code": f_job, "equipment": f_eq, **m_responses}
            conn.table("progress_logs").insert(payload).execute()
            st.cache_data.clear(); st.rerun()

with tab2:
    st.subheader("📂 Filtered Archive")
    f1, f2, f3 = st.columns(3)
    sel_c = f1.selectbox("Customer", ["All"] + customers)
    dur = f2.selectbox("Duration", ["All Time", "Current Month", "Custom Range"])
    
    # Query logic
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    
    res = query.execute()
    filtered_data = res.data if res else []
    
    if filtered_data:
        # Action Buttons
        pdf_bytes = generate_pdf(filtered_data)
        st.download_button("📥 Download PDF Report", data=pdf_bytes, file_name="BG_Archive.pdf", mime="application/pdf")
        
        for log in filtered_data:
            with st.expander(f"📦 {log.get('job_code')} - {log.get('customer')}"):
                # Progress Bar rendering
                ov_p = sum([int(log.get(f"{m[1]}_prog", 0)) for m in MILESTONE_MAP]) // len(MILESTONE_MAP)
                st.write(f"**Overall: {ov_p}%**")
                st.progress(ov_p / 100)
                
                # Detailed Grid
                for label, skey, nkey in MILESTONE_MAP:
                    col_a, col_b = st.columns([1, 2])
                    col_a.write(f"**{label}**: {log.get(skey)}")
                    col_b.write(f"_{log.get(nkey, '-')}_")

with tab3:
    # ... [Keep your existing Tab 3 Master Data Management here] ...
    st.write("Manage Customers and Jobs here.")
# --- TAB 3: MASTERS (The Missing Tab) ---
with tab3:
    st.subheader("🛠️ Master Management")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏢 Add New Customer")
        with st.form("add_customer", clear_on_submit=True):
            new_cust = st.text_input("Customer Name")
            if st.form_submit_button("Add Customer"):
                if new_cust:
                    conn.table("customer_master").insert({"name": new_cust}).execute()
                    st.success(f"Added {new_cust}"); st.cache_data.clear(); st.rerun()
                else: st.error("Name cannot be empty")

    with col2:
        st.markdown("### 🔢 Add New Job Code")
        with st.form("add_job", clear_on_submit=True):
            new_job = st.text_input("Job Code")
            if st.form_submit_button("Add Job"):
                if new_job:
                    conn.table("job_master").insert({"job_code": new_job}).execute()
                    st.success(f"Added {new_job}"); st.cache_data.clear(); st.rerun()
                else: st.error("Job Code cannot be empty")
