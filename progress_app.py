import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import io
import os
from datetime import date
from PIL import Image

# 1. INITIALIZE SUPABASE
conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="B&G Progress Hub", layout="wide")
st.title("🏗️ B&G Professional Dispatcher")

# --- MASTER DATA FETCH ---
# We fetch customers and jobs from Supabase instead of session_state
try:
    customers = conn.table("customer_master").select("name").execute().data
    customer_list = [c['name'] for c in customers]
    
    jobs = conn.table("job_master").select("job_code").execute().data
    job_list = [j['job_code'] for j in jobs]
except:
    customer_list, job_list = ["Error Loading"], ["Error Loading"]

# --- TABBED INTERFACE ---
tab_entry, tab_archive = st.tabs(["📝 Create Report", "📂 Report Archive"])

with tab_entry:
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        selected_customer = st.selectbox("Select Customer Name", customer_list)
    with c_col2:
        submitted_by = st.text_input("Engineer Name")

    with st.form("main_form", clear_on_submit=True):
        st.subheader("📋 Equipment Details")
        f1, f2, f3 = st.columns(3)
        with f1:
            eq_name = st.text_input("Equipment Name")
            j_code = st.selectbox("Job Code", job_list)
        with f2:
            po_no = st.text_input("PO Number")
            target_date = st.date_input("Target Dispatch")
        with f3:
            fabrication_status = st.selectbox("Fabrication Status", ["In-Progress", "Completed", "Pending"])
            remarks = st.text_area("General Remarks")

        uploaded_pics = st.file_uploader("Upload Progress Photos", accept_multiple_files=True)
        
        if st.form_submit_button("🚀 Submit to Cloud & Storage"):
            # 1. Insert Text Data
            report_entry = conn.table("progress_reports").insert({
                "customer": selected_customer,
                "engineer": submitted_by,
                "equipment": eq_name,
                "job_code": j_code,
                "po_number": po_no,
                "target_date": str(target_date),
                "fab_status": fabrication_status,
                "remarks": remarks
            }).execute()
            
            report_id = report_entry.data[0]['id']

            # 2. Upload Photos to Storage Bucket
            if uploaded_pics:
                for pic in uploaded_pics:
                    file_path = f"reports/{report_id}/{pic.name}"
                    # Upload to 'progress-photos' bucket
                    conn.storage.from_("progress-photos").upload(file_path, pic.getvalue())
                    
                    # Store public URL in report_photos table
                    img_url = conn.storage.from_("progress-photos").get_public_url(file_path)
                    conn.table("report_photos").insert({
                        "report_id": report_id,
                        "photo_url": img_url
                    }).execute()
            
            st.success("Data and Photos archived in Supabase!")

with tab_archive:
    st.subheader("🔍 Historical Progress Logs")
    all_reports = conn.table("progress_reports").select("*").order("created_at", desc=True).execute().data
    if all_reports:
        df = pd.DataFrame(all_reports)
        st.dataframe(df, use_container_width=True)
        
        # Select a report to generate PDF
        report_to_pdf = st.selectbox("Select Report to Print", df['id'])
        if st.button("Generate PDF from Cloud"):
            st.info(f"Generating PDF for Report ID: {report_to_pdf}...")
            # (PDF Generation logic remains similar, fetching from 'report_photos' table)
