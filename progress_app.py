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
        return sorted([d['name'] for d in c_res.data]), sorted([d['job_code'] for d in j_res.data])
    except: return [], []

customers, jobs = get_master_data()

tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# --- TAB 1: NEW ENTRY (WITH FULL AUTOFILL) ---
with tab1:
    st.subheader("📋 Project Update")
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        if res and res.data: 
            last_data = res.data[0]
            st.toast(f"🔄 Autofilled latest data for {f_job}")

    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cust = c1.selectbox("Customer", [""] + customers, index=customers.index(last_data['customer'])+1 if last_data.get('customer') in customers else 0)
        f_eq = c2.text_input("Equipment", value=last_data.get('equipment', ""))
        
        # Additional Project Details Autofill
        c3, c4, c5 = st.columns(3)
        f_po_n = c3.text_input("PO Number", value=last_data.get('po_no', ""))
        
        def safe_date(field):
            val = last_data.get(field)
            try: return datetime.strptime(val, "%Y-%m-%d") if val else datetime.now()
            except: return datetime.now()

        f_po_d = c4.date_input("PO Date", value=safe_date('po_date'))
        f_eng = c5.text_input("Responsible Engineer", value=last_data.get('engineer', ""))

        # ... (Previous code for Customer, Equipment, etc.)

        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        opts = ["Pending", "NA", "In-Progress", "Submitted", "Approved", "Ordered", "Received", "Hold", "Completed", "Planning", "Scheduled"]
        
        for label, skey, nkey in MILESTONE_MAP:
            pk = f"{skey}_prog"
            col1, col2, col3 = st.columns([1.5, 1, 2])
            
            # 1. Get previous values from last_data
            prev_status = last_data.get(skey, "Pending")
            prev_prog = int(last_data.get(pk, 0))
            prev_remarks = last_data.get(nkey, "")

            # 2. Calculate default index for status
            def_idx = opts.index(prev_status) if prev_status in opts else 0
            
            # 3. FIX: Add f_job to the key to force refresh on job change
            widget_suffix = f"{f_job}" if f_job else "default"
            
            m_responses[skey] = col1.selectbox(
                label, 
                opts, 
                index=def_idx, 
                key=f"s_{skey}_{widget_suffix}" 
            )
            
            m_responses[pk] = col2.slider(
                "Prog %", 
                0, 100, 
                value=prev_prog, 
                key=f"p_{skey}_{widget_suffix}"
            )
            
            m_responses[nkey] = col3.text_input(
                "Remarks", 
                value=prev_remarks, 
                key=f"n_{skey}_{widget_suffix}"
            )

        st.divider()
        # Apply the same key logic to the Overall Completion slider
        f_progress = st.slider(
            "📈 Overall Completion %", 
            0, 100, 
            value=int(last_data.get('overall_progress') or 0),
            key=f"overall_slider_{f_job if f_job else 'none'}"
        )
       st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        opts = ["Pending", "NA", "In-Progress", "Submitted", "Approved", "Ordered", "Received", "Hold", "Completed", "Planning", "Scheduled"]
        
        # Unique suffix forces Streamlit to re-render widgets with new 'value' when Job Code changes
        job_suffix = str(f_job) if f_job else "initial"

        # ... inside the with st.form("main_form", clear_on_submit=True): block ...

        for label, skey, nkey in MILESTONE_MAP:
            pk = f"{skey}_prog"
            col1, col2, col3 = st.columns([1.5, 1, 2])
            
            # (Autofill logic here...)
            
            m_responses[skey] = col1.selectbox(label, opts, index=def_idx, key=f"s_{skey}_{job_suffix}")
            m_responses[pk] = col2.slider("Prog %", 0, 100, value=prev_prog, key=f"p_{skey}_{job_suffix}")
            m_responses[nkey] = col3.text_input("Remarks", value=prev_note, key=f"n_{skey}_{job_suffix}")

        # --- FIX: Ensure this divider and f_progress are indented to match the 'for' loop above ---
        st.divider()
        
        raw_overall = last_data.get('overall_progress', 0)
        prev_overall = int(raw_overall) if raw_overall is not None else 0
        
        f_progress = st.slider(
            "📈 Overall Completion %", 
            0, 100, 
            value=prev_overall,
            key=f"overall_slider_{job_suffix}"
        )
        
        cam_photo = st.camera_input("📸 Take Progress Photo")

        if st.form_submit_button("🚀 SUBMIT UPDATE", use_container_width=True):
            # ... (Submit logic here) ...
            st.success("✅ Saved!")
            st.cache_data.clear()
            st.rerun()

# --- TAB 2 starts here (Back to 0 indentation) ---
with tab2:
    st.subheader("📂 Report Archive")
# --- TAB 2: ARCHIVE (WITH FILTERS & BARS) ---
with tab2:
    st.subheader("📂 Report Archive")
    f1, f2, f3 = st.columns(3)
    sel_c = f1.selectbox("Filter Customer", ["All"] + customers)
    report_type = f2.selectbox("📅 Report Duration", ["All Time", "Current Week", "Current Month", "Custom Range"])
    
    start_date, end_date = None, None
    if report_type == "Custom Range":
        c_date = f3.date_input("Select Range", [datetime.now().date(), datetime.now().date()])
        if isinstance(c_date, list) and len(c_date) == 2: start_date, end_date = c_date

    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    res = query.execute()
    data = res.data if res else []
    
    today = datetime.now().date()
    filtered_data = []
    for log in data:
        try:
            # Filtering logic by duration
            raw_date = log.get('created_at') or log.get('po_date')
            log_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
            if report_type == "Current Week" and log_date.isocalendar()[1] != today.isocalendar()[1]: continue
            if report_type == "Current Month" and log_date.month != today.month: continue
            if report_type == "Custom Range" and not (start_date <= log_date <= end_date): continue
            filtered_data.append(log)
        except: continue

    if filtered_data:
        st.download_button("📥 Download PDF Report", data=generate_pdf(filtered_data), file_name="BG_Archive.pdf", mime="application/pdf", use_container_width=True)
        
        for log in filtered_data:
            with st.expander(f"📦 {log.get('job_code')} - {log.get('customer')}"):
                ov_p = int(log.get('overall_progress', 0))
                st.write(f"**Overall Progress: {ov_p}%**")
                st.progress(ov_p / 100)
                
                # Individual milestone bars
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_status, c_bar, c_note = st.columns([1.5, 1, 1.5])
                    m_prog = int(log.get(pk, 0))
                    c_status.write(f"**{label}**")
                    c_status.caption(f"Status: {log.get(skey, 'Pending')}")
                    with c_bar:
                        st.progress(m_prog / 100.0)
                        st.caption(f"{m_prog}%")
                    c_note.write(f"_{log.get(nkey, '-')}_")
                
                # Display Photo
                try:
                    photo_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log.get('id')}.jpg")
                    st.image(photo_url, width=250, caption=f"Capture for Job {log.get('job_code')}")
                except: pass

# --- TAB 3: MASTERS ---
with tab3:
    st.subheader("🛠️ Master Management")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_cust"):
            nc = st.text_input("New Customer")
            if st.form_submit_button("Add Customer"):
                conn.table("customer_master").insert({"name": nc}).execute()
                st.cache_data.clear(); st.rerun()
    with col2:
        with st.form("add_job"):
            nj = st.text_input("New Job Code")
            if st.form_submit_button("Add Job"):
                conn.table("job_master").insert({"job_code": nj}).execute()
                st.cache_data.clear(); st.rerun()
