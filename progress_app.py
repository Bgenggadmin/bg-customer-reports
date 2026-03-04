import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import io, os
from datetime import date
from PIL import Image

# 1. INITIALIZE CONNECTION & CONFIG
st.set_page_config(page_title="B&G Progress Hub", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

st.title("🏗️ B&G Professional Dispatcher")

# --- DATA FETCHING ---
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except:
        return [], []

customer_list, job_list = get_masters()

# --- TABS ---
tab_entry, tab_archive, tab_masters = st.tabs([
    "📝 New Progress Report", "📂 History & Archive", "🛠️ Masters"
])

# --- TAB 1: NEW PROGRESS REPORT ---
with tab_entry:
    # Ensure lists are not empty to avoid selectbox errors
    safe_cust = customer_list if customer_list else ["Enter Customers in Masters"]
    safe_jobs = job_list if job_list else ["Enter Jobs in Masters"]

    with st.form("dispatch_form", clear_on_submit=True):
        st.subheader("📋 Core Details")
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", safe_cust)
        eng = c2.text_input("Engineer Name")
        eq = c3.text_input("Equipment (e.g., 5KL Vessel)")

        st.divider()
        st.subheader("⚙️ Job & Milestone")
        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", safe_jobs)
        po = f1.text_input("PO Number")
        status = f2.selectbox("Current Status", ["In-Progress", "Fabrication", "Testing", "Dispatch Ready", "Completed"])
        target = f3.date_input("Target Dispatch Date")
        
        remarks = st.text_area("Work Progress Remarks")

        st.divider()
        st.subheader("📸 Shop Floor Media")
        
        # Camera Input for live snapshots
        cam_photo = st.camera_input("Take a Live Photo")
        
        # File Uploader for gallery photos
        gallery_photos = st.file_uploader("Upload from Gallery", accept_multiple_files=True)
        
        submit = st.form_submit_button("🚀 Sync to Cloud & Save")

        if submit:
            if not customer_list or not job_list:
                st.error("Please add a Customer and Job Code in the Masters tab first.")
            elif not eng or not eq:
                st.error("Please fill in Engineer Name and Equipment.")
            else:
                # 1. Save Text Data to Supabase
                res = conn.table("progress_logs").insert({
                    "customer": cust, 
                    "engineer": eng, 
                    "equipment": eq,
                    "job_code": job, 
                    "po_no": po, 
                    "target_date": str(target),
                    "fab_status": status, 
                    "remarks": remarks
                }).execute()
                
                log_id = res.data[0]['id']

                # 2. Collect all photos
                all_pics = []
                if cam_photo:
                    all_pics.append(cam_photo)
                if gallery_photos:
                    all_pics.extend(gallery_photos)

                # 3. Upload to Storage
                if all_pics:
                    for i, pic in enumerate(all_pics):
                        # Use actual name or generate one for camera shots
                        fname = getattr(pic, 'name', f"camera_shot_{i}.jpg")
                        path = f"reports/{log_id}/{fname}"
                        # Added file_options with upsert=True
conn.client.storage.from_("progress-photos").upload(
    path=path, 
    file=pic.getvalue(), 
    file_options={"upsert": "true"}
)
#      ^--- Added .client here
                
                st.success(f"✅ Report for {eq} successfully archived with {len(all_pics)} photos!")
                st.balloons()
                st.rerun()

# --- TAB 2: HISTORY & ARCHIVE ---
with tab_archive:
    st.subheader("📂 Historical Logs")
    history_res = conn.table("progress_logs").select("*").order("created_at", desc=True).execute().data
    
    if history_res:
        hist_df = pd.DataFrame(history_res)
        # Display key columns
        st.dataframe(hist_df[['created_at', 'customer', 'equipment', 'job_code', 'fab_status', 'remarks']], 
                     use_container_width=True, hide_index=True)
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
            with st.form("add_customer", clear_on_submit=True):
                new_cust = st.text_input("New Customer Name")
                if st.form_submit_button("Add Customer"):
                    if new_cust:
                        conn.table("customer_master").insert({"name": new_cust}).execute()
                        st.rerun()
            st.write("Current:", customer_list)
            
        with m_col2:
            st.write("### 🔢 Job Codes")
            with st.form("add_job", clear_on_submit=True):
                new_job = st.text_input("New Job Code")
                if st.form_submit_button("Add Job"):
                    if new_job:
                        conn.table("job_master").insert({"job_code": new_job}).execute()
                        st.rerun()
            st.write("Current:", job_list)
    else:
        st.info("Enter PIN '1234' to unlock Master Management.")
