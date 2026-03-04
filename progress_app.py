import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import io, os
from datetime import date
from PIL import Image
from fpdf import FPDF

# 1. INITIALIZE
st.set_page_config(page_title="B&G Progress Hub", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

st.title("🏗️ B&G Professional Dispatcher")

# --- FETCH MASTER LISTS FROM CLOUD ---
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except:
        return ["Add in Masters"], ["Add in Masters"]

customer_list, job_list = get_masters()

# --- TABS ---
tab_entry, tab_archive = st.tabs(["📝 New Progress Report", "📂 History & PDF"])

with tab_entry:
    with st.form("dispatch_form", clear_on_submit=True):
        st.subheader("📋 Core Details")
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", customer_list)
        eng = c2.text_input("Engineer Name")
        eq = c3.text_input("Equipment (e.g., 5KL Vessel)")

        st.divider()
        st.subheader("⚙️ Job & Milestone")
        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", job_list)
        po = f2.text_input("PO Number")
        status = f3.selectbox("Status", ["In-Progress", "Fabrication", "Testing", "Dispatch Ready", "Completed"])
        
        target = st.date_input("Target Dispatch Date")
        remarks = st.text_area("Work Progress Remarks")

        st.divider()
        pics = st.file_uploader("Upload Shop Floor Photos", accept_multiple_files=True)
        
        submit = st.form_submit_button("🚀 Sync to Cloud & Save")

        if submit:
            # 1. Save Text Data
            res = conn.table("progress_logs").insert({
                "customer": cust, "engineer": eng, "equipment": eq,
                "job_code": job, "po_no": po, "target_date": str(target),
                "fab_status": status, "remarks": remarks
            }).execute()
            
            log_id = res.data[0]['id']

            # 2. Upload Photos to Storage
            if pics:
                for pic in pics:
                    path = f"reports/{log_id}/{pic.name}"
                    conn.storage.from_("progress-photos").upload(path, pic.getvalue())
            
            st.success(f"Report for {eq} saved to Cloud!")
            st.rerun()

with tab_archive:
    st.subheader("📂 Historical Logs")
    history = conn.table("progress_logs").select("*").order("created_at", desc=True).execute().data
    
    if history:
        df = pd.DataFrame(history)
        st.dataframe(df[['created_at', 'customer', 'equipment', 'job_code', 'fab_status']], use_container_width=True)
        
        st.divider()
        st.info("To generate a PDF, select a report ID from the database history.")
