import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta

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
    except Exception as e:
        st.error(f"Error fetching Master Data: {e}")
        return [], []

customer_list, job_list = get_masters()

# --- TABS ---
tab_entry, tab_archive, tab_masters = st.tabs([
    "📝 New Progress Report", "📂 History & Weekly Reports", "🛠️ Masters"
])

# --- TAB 1: NEW PROGRESS REPORT ---
with tab_entry:
    safe_cust = customer_list if customer_list else ["Add Customers in Masters Tab"]
    safe_jobs = job_list if job_list else ["Add Jobs in Masters Tab"]

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
        cam_photo = st.camera_input("Take a Live Photo")
        gallery_photos = st.file_uploader("Upload from Gallery", accept_multiple_files=True)
        
        submit = st.form_submit_button("🚀 Sync to Cloud & Save")

        if submit:
            if not customer_list or not job_list:
                st.error("Missing Master Data: Add Customer/Job in Masters tab first.")
            elif not eng or not eq:
                st.error("Required: Please fill in Engineer Name and Equipment.")
            else:
                try:
                    # 1. Save Text Data
                    res = conn.table("progress_logs").insert({
                        "customer": cust, "engineer": eng, "equipment": eq,
                        "job_code": job, "po_no": po, "target_date": str(target),
                        "fab_status": status, "remarks": remarks
                    }).execute()
                    
                    log_id = res.data[0]['id']

                    # 2. Collect & Upload Photos
                    all_pics = []
                    if cam_photo: all_pics.append(cam_photo)
                    if gallery_photos: all_pics.extend(gallery_photos)

                    if all_pics:
                        for i, pic in enumerate(all_pics):
                            ts = datetime.now().strftime("%H%M%S")
                            fname = getattr(pic, 'name', f"cam_{ts}_{i}.jpg")
                            path = f"reports/{log_id}/{fname}"
                            conn.client.storage.from_("progress-photos").upload(
                                path=path, file=pic.getvalue(), file_options={"upsert": "true"}
                            )
                    
                    st.success(f"✅ Report for {eq} saved successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")

# --- TAB 2: HISTORY & WEEKLY REPORTS ---
with tab_archive:
    st.subheader("📊 Customer Weekly Review")
    
    # Filtering UI
    filter_col1, filter_col2 = st.columns(2)
    selected_cust = filter_col1.selectbox("Select Customer for Report", ["All Customers"] + customer_list)
    
    # Weekly Logic (Last 7 Days)
    last_week = datetime.now() - timedelta(days=7)
    show_only_weekly = filter_col2.checkbox("Show only last 7 days", value=True)

    try:
        query = conn.table("progress_logs").select("*").order("created_at", desc=True)
        
        if selected_cust != "All Customers":
            query = query.eq("customer", selected_cust)
        if show_only_weekly:
            query = query.gte("created_at", last_week.isoformat())
            
        history_res = query.execute().data

        if history_res:
            st.write(f"Showing **{len(history_res)}** reports.")
            
            for log in history_res:
                with st.expander(f"📦 {log['equipment']} | {log['job_code']} | Status: {log['fab_status']} ({log['created_at'][:10]})"):
                    c_text, c_img = st.columns([1, 1])
                    with c_text:
                        st.markdown(f"**Customer:** {log['customer']}")
                        st.markdown(f"**Engineer:** {log['engineer']}")
                        st.markdown(f"**PO No:** {log['po_no']}")
                        st.markdown(f"**Remarks:** {log['remarks']}")
                    
                    with c_img:
                        f_path = f"reports/{log['id']}"
                        files = conn.client.storage.from_("progress-photos").list(f_path)
                        if files:
                            # Display photos in a grid
                            cols = st.columns(2)
                            for idx, f in enumerate(files):
                                url = conn.client.storage.from_("progress-photos").get_public_url(f"{f_path}/{f['name']}")
                                cols[idx % 2].image(url, use_container_width=True)
                        else:
                            st.caption("No photos available.")
        else:
            st.info("No reports found for the selected criteria.")
            
    except Exception as e:
        st.error(f"Error loading archive: {e}")

# --- TAB 3: MASTERS MANAGEMENT ---
with tab_masters:
    st.subheader("⚙️ Master Data Management")
    admin_pin = st.text_input("Enter Admin PIN", type="password")
    
    if admin_pin == "1234":
        st.success("Access Granted")
        m1, m2 = st.columns(2)
        with m1:
            st.write("### 🏢 Customers")
            with st.form("add_cust", clear_on_submit=True):
                n_cust = st.text_input("New Customer Name")
                if st.form_submit_button("Add Customer") and n_cust:
                    conn.table("customer_master").insert({"name": n_cust}).execute()
                    st.rerun()
            st.write("List:", customer_list)
        with m2:
            st.write("### 🔢 Job Codes")
            with st.form("add_job", clear_on_submit=True):
                n_job = st.text_input("New Job Code")
                if st.form_submit_button("Add Job") and n_job:
                    conn.table("job_master").insert({"job_code": n_job}).execute()
                    st.rerun()
            st.write("List:", job_list)
    else:
        st.info("Enter PIN '1234' to edit Master Data.")
