import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import io, os
from datetime import date
from PIL import Image
from fpdf import FPDF

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

st.title("🏗️ B&G Professional Dispatcher")

# --- HELPER FUNCTIONS ---
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except:
        return [], []

# Fetch live data for dropdowns
customer_list, job_list = get_masters()

# --- TABS CONFIGURATION ---
tab_entry, tab_archive, tab_masters = st.tabs([
    "📝 New Progress Report", "📂 History & PDF", "🛠️ Masters"
])

# --- TAB 1: NEW PROGRESS REPORT ---
with tab_entry:
    with st.form("dispatch_form", clear_on_submit=True):
        st.subheader("📋 Core Details")
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", customer_list if customer_list else ["Enter in Masters First"])
        eng = c2.text_input("Engineer Name")
        eq = c3.text_input("Equipment (e.g., 5KL Vessel)")

        st.divider()
        st.subheader("⚙️ Job & Milestone")
        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", job_list if job_list else ["Enter in Masters First"])
        po = f1.text_input("PO Number")
        status = f2.selectbox("Current Status", ["In-Progress", "Fabrication", "Testing", "Dispatch Ready", "Completed"])
        target = f3.date_input("Target Dispatch Date")
        
        remarks = st.text_area("Work Progress Remarks")

        st.divider()
        st.write("📷 **Upload Shop Floor Photos**")
        pics = st.file_uploader("Select JPG/PNG files", accept_multiple_files=True)
        
        submit = st.form_submit_button("🚀 Sync to Cloud & Save")

        if submit:
            if not cust or not job:
                st.error("Please select a Customer and Job Code from the Masters list.")
            else:
                # 1. Save Text Data to Supabase
                res = conn.table("progress_logs").insert({
                    "customer": cust, "engineer": eng, "equipment": eq,
                    "job_code": job, "po_no": po, "target_date": str(target),
                    "fab_status": status, "remarks": remarks
                }).execute()
                
                log_id = res.data[0]['id']

                # 2. Upload Photos to Storage Bucket
                if pics:
                    for pic in pics:
                        path = f"reports/{log_id}/{pic.name}"
                        conn.storage.from_("progress-photos").upload(path, pic.getvalue())
                
                st.success(f"✅ Report for {eq} successfully archived!")
                st.balloons()
                st.rerun()

# --- TAB 2: HISTORY & ARCHIVE ---
with tab_archive:
    st.subheader("📂 Historical Logs")
    history_res = conn.table("progress_logs").select("*").order("created_at", desc=True).execute().data
    
    if history_res:
        hist_df = pd.DataFrame(history_res)
        st.dataframe(hist_df[['created_at', 'customer', 'equipment', 'job_code', 'fab_status']], use_container_width=True)
        
        st.divider()
        st.info("PDF generation from Cloud Storage will be enabled in the next update. All data is currently safe in the database.")
    else:
        st.info("No reports found yet.")

# --- TAB 3: MASTERS MANAGEMENT ---
with tab_masters:
    st.subheader("⚙️ Master Data Management")
    admin_pin = st.text_input("Enter Admin PIN", type="password")
    
    if admin_pin == "1234":
        st.success("Access Granted")
        m_col1, m_col2 = st.columns(2)
        
        with m_col1:
            st.write("### 🏢 Customers")
            new_cust = st.text_input("Add Customer Name")
            if st.button("Add Customer"):
                conn.table("customer_master").insert({"name": new_cust}).execute()
                st.rerun()
            st.write("Current Customers:", customer_list)
            
        with m_col2:
            st.write("### 🔢 Job Codes")
            new_job = st.text_input("Add Job Code")
            if st.button("Add Job"):
                conn.table("job_master").insert({"job_code": new_job}).execute()
                st.rerun()
            st.write("Current Jobs:", job_list)
            
        st.divider()
        st.warning("🗑️ To delete an entry, please use the Supabase Dashboard for security.")
    else:
        st.info("Enter PIN '1234' to add new customers or job codes.")
