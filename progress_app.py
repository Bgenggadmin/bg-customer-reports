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
            try: return datetime.strptime(str(val)[:10], "%Y-%m-%d") if val else datetime.now()
            except: return datetime.now()
        f_po_d = st.date_input("PO Date", value=safe_date('po_date'))
        
        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        
        for label, skey, nkey in MILESTONE_MAP:
            prog_key = f"{skey}_prog"
            col_stat, col_prog, col_note = st.columns([1.5, 1, 2])
            
            opts = ["Pending", "NA", "In-Progress", "Submitted", "Approved", "Ordered", "Received", "Hold", "Completed"]
            prev_status = last_data.get(skey, "Pending")
            m_responses[skey] = col_stat.selectbox(label, opts, index=opts.index(prev_status) if prev_status in opts else 0, key=f"s_{f_job}_{skey}")
            
            # SAFE DATA FETCH: Ensure it's an integer
            try: prev_p = int(last_data.get(prog_key, 0))
            except: prev_p = 0
            
            m_responses[prog_key] = col_prog.slider("Prog %", 0, 100, value=prev_p, key=f"p_{f_job}_{skey}")
            m_responses[nkey] = col_note.text_input("Remarks", value=last_data.get(nkey, ""), key=f"n_{f_job}_{skey}")

        if st.form_submit_button("🚀 SUBMIT UPDATE"):
            try:
                # Logic: Average of all manual sliders
                all_vals = [m_responses[f"{m[1]}_prog"] for m in MILESTONE_MAP]
                overall_avg = sum(all_vals) // len(all_vals)
                
                entry_payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_date": str(f_po_d), "overall_progress": overall_avg,
                    **m_responses
                }
                conn.table("progress_logs").insert(entry_payload).execute()
                st.success(f"✅ Saved! Overall: {overall_avg}%")
                st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

with tab2:
    st.subheader("📂 Report Archive")
    res = conn.table("progress_logs").select("*").order("id", desc=True).execute()
    if res and res.data:
        for log in res.data:
            with st.expander(f"📦 Job: {log.get('job_code')} | {log.get('customer')}"):
                # 1. Overall Progress Bar
                try: ov_p = int(log.get('overall_progress', 0))
                except: ov_p = 0
                st.write(f"**Total Completion: {ov_p}%**")
                st.progress(min(max(ov_p / 100, 0.0), 1.0)) # Ensure value is between 0 and 1
                
                st.markdown("---")
                # 2. Individual Milestone Bars
                for label, skey, nkey in MILESTONE_MAP:
                    pk = f"{skey}_prog"
                    c_s, c_p, c_r = st.columns([1.5, 1, 1.5])
                    
                    # Logic Fix: Convert to float safely
                    try: val = float(log.get(pk, 0))
                    except: val = 0.0
                    
                    c_s.write(f"**{label}:** {log.get(skey, 'Pending')}")
                    # Render progress bar
                    c_p.progress(min(max(val / 100.0, 0.0), 1.0))
                    c_p.caption(f"{int(val)}%")
                    c_r.write(f"_{log.get(nkey, '-')}_")
