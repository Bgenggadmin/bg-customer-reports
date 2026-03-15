import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from fpdf import FPDF
import tempfile

# 1. SETUP
st.set_page_config(page_title="B&G Hub 2.0", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection, ttl=60)

# 2. MASTER MAPPING
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
def generate_filtered_pdf(data_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for log in data_list:
        pdf.add_page()
        # Header
        pdf.set_fill_color(0, 51, 102); pdf.rect(0, 0, 210, 20, 'F')
        pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 14)
        pdf.set_xy(10, 5); pdf.cell(0, 10, f"PROGRESS REPORT: {log.get('job_code')}", 0, 1, "L")
        
        # Project Info
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 10); pdf.ln(10)
        pdf.cell(0, 8, f"Customer: {log.get('customer')} | Date: {log.get('created_at','')[:10]}", "B", 1)
        pdf.cell(0, 8, f"Overall Progress: {log.get('overall_progress')}%", 0, 1)
        
        # Table
        pdf.ln(5); pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 8, " Milestone", 1); pdf.cell(30, 8, " Status", 1); pdf.cell(20, 8, " %", 1); pdf.cell(80, 8, " Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, skey, nkey in MILESTONE_MAP:
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(30, 7, f" {log.get(skey, '-')}", 1)
            pdf.cell(20, 7, f" {log.get(skey+'_prog', 0)}%", 1)
            pdf.cell(80, 7, f" {log.get(nkey, '-')}", 1, 1)
            
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def get_master_data():
    try:
        c_res = conn.table("customer_master").select("name").execute()
        j_res = conn.table("job_master").select("job_code").execute()
        return sorted([d['name'] for d in c_res.data]), sorted([d['job_code'] for d in j_res.data])
    except: return [], []

customers, jobs = get_master_data()

tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# (Tab 1 & Tab 3 remain as previously provided...)

with tab2:
    st.subheader("📂 Report Archive & Filters")
    
    # --- FILTER SECTION ---
    with st.expander("🔍 Filter Reports", expanded=True):
        f_col1, f_col2, f_col3 = st.columns(3)
        sel_cust = f_col1.multiselect("Filter by Customer", customers)
        start_dt = f_col2.date_input("Start Date", value=date(2024, 1, 1))
        end_dt = f_col3.date_input("End Date", value=date.today())

    # Fetch Data
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    
    # Apply Filters in Python for flexibility
    res = query.execute()
    filtered_data = res.data if res and res.data else []
    
    if sel_cust:
        filtered_data = [d for d in filtered_data if d['customer'] in sel_cust]
    
    filtered_data = [d for d in filtered_data if str(start_dt) <= d.get('created_at', '')[:10] <= str(end_dt)]

    # --- ACTIONS ---
    if filtered_data:
        pdf_data = generate_filtered_pdf(filtered_data)
        st.download_button(
            label="📥 Download Filtered PDF Report",
            data=pdf_data,
            file_name=f"B&G_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
        
        st.write(f"Showing **{len(filtered_data)}** records")
        
        for log in filtered_data:
            with st.expander(f"📦 Job: {log.get('job_code')} | {log.get('customer')} ({log.get('created_at','')[:10]})"):
                # Overall Bar
                ov_p = int(log.get('overall_progress', 0))
                st.progress(min(max(ov_p / 100.0, 0.0), 1.0))
                st.caption(f"Overall Progress: {ov_p}%")
                
                # Detailed Grid
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_s, c_p, c_r = st.columns([1.5, 1, 1.5])
                    val = float(log.get(pk, 0) or 0)
                    
                    c_s.write(f"**{label}**")
                    c_s.caption(f"Status: {log.get(skey)}")
                    with c_p:
                        st.progress(min(max(val / 100.0, 0.0), 1.0))
                        st.caption(f"{int(val)}%")
                    c_r.write(f"_{log.get(nkey, '-')}_")
    else:
        st.info("No reports match your filters.")

# (Include Tab 3 logic here...)
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
