import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. SETUP
st.set_page_config(page_title="B&G Hub 2.0", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# 2. THE MASTER MAPPING
HEADER_FIELDS = ["customer", "job_code", "equipment", "po_no", "po_date", "engineer", "po_delivery_date", "exp_dispatch_date"]

MILESTONE_MAP = [
    ("Drawing Submission", "draw_sub", "draw_sub_note"),
    ("Drawing Approval", "draw_app", "draw_app_note"),
    ("RM Status", "rm_status", "rm_note"),
    ("Sub-deliveries", "sub_del", "sub_del_note"),
    ("Fabrication Status", "fab_status", "remarks"),
    ("Buffing Status", "buff_stat", "buff_note"),
    ("Testing Status", "testing", "test_note"),
    ("QC Status", "qc_stat", "qc_note"),
    ("FAT Status", "fat_stat", "fat_note")
]

# --- DATA FETCHING ---
customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])

# --- PDF ENGINE (PHOTO MOVED TO BOTTOM) ---
def generate_pdf(logs):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for log in logs:
        pdf.add_page()
        
        # 1. B&G Header Logo/Bar
        pdf.set_fill_color(0, 51, 102) # Dark Blue
        pdf.rect(0, 0, 210, 35, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 12, "B&G ENGINEERING INDUSTRIES", 0, 1, "C")
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 5, "PROJECT PROGRESS REPORT", 0, 1, "C")
        pdf.ln(15)

        # 2. Job Info Header
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        pdf.ln(3)
        
        # 3. Header Fields Table
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1, f2 = HEADER_FIELDS[i], HEADER_FIELDS[i+1]
            pdf.cell(30, 7, f" {f1.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f1,''))}", 1, 0, 'L')
            pdf.cell(30, 7, f" {f2.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f2,''))}", 1, 1, 'L')

        pdf.ln(5)

        # 4. Milestone Table with Color Coding
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, " Milestone Item", 1, 0, 'L', True)
        pdf.cell(35, 8, " Status", 1, 0, 'C', True)
        pdf.cell(95, 8, " Remarks", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            status = str(log.get(s_key, 'Pending'))
            if status in ["Completed", "Approved", "Submitted"]:
                pdf.set_fill_color(144, 238, 144) # Green
            elif status in ["In-Progress", "Hold"]:
                pdf.set_fill_color(255, 255, 204) # Yellow
            else:
                pdf.set_fill_color(255, 255, 255) # White
            
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {status}", 1, 0, 'C', True)
            pdf.cell(95, 7, f" {str(log.get(n_key,'-'))}", 1, 1)

        # 5. Progress Photo (Moved to Bottom)
        try:
            img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((350, 350))
                buf = BytesIO(); img.save(buf, format="JPEG")
                # Center horizontally and place below table
                pdf.image(buf, x=75, y=pdf.get_y()+10, w=60)
        except: 
            pass

    return bytes(pdf.output())

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    with st.form("main_entry_form", clear_on_submit=True):
        st.subheader("📋 Project Details")
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment Name")
        
        c4, c5, c6 = st.columns(3)
        f_po_n = c4.text_input("PO Number")
        f_po_d = c5.date_input("PO Date")
        f_eng = c6.text_input("Responsible Engineer")
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("Contractual Delivery Date")
        f_r_del = c8.date_input("Revised Dispatch Date")

        st.divider()
        st.subheader("📸 Progress Capture")
        cam_photo = st.camera_input("Take Progress Photo")

        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        for label, skey, nkey in MILESTONE_MAP:
            col_stat, col_note = st.columns([1, 2])
            opts = ["Pending", "In-Progress", "Submitted", "Approved"] if "Drawing" in label else ["Pending", "In-Progress", "Hold", "Completed"]
            m_responses[skey] = col_stat.selectbox(label, opts, key=f"form_{skey}")
            m_responses[nkey] = col_note.text_input(f"Remarks for {label}", key=f"form_{nkey}")

        if st.form_submit_button("🚀 Final Sync to Database", use_container_width=True):
            if not f_cust or not f_job or not cam_photo:
                st.error("Missing required data! Please ensure Customer, Job, and Photo are captured.")
            else:
                entry_payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                    **m_responses
                }
                try:
                    res = conn.table("progress_logs").insert(entry_payload).execute()
                    if res.data:
                        new_id = res.data[0]['id']
                        conn.client.storage.from_("progress-photos").upload(
                            path=f"{new_id}.jpg", file=cam_photo.getvalue(),
                            file_options={"upsert": "true", "content-type": "image/jpeg"}
                        )
                        st.success(f"✅ Success! Data & Photo synced for Entry ID: {new_id}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {str(e)}")

with tab2:
    st.subheader("📂 Report Archive")
    
    cust_list = ["All Customers"] + customers
    selected_cust = st.selectbox("🔍 Filter by Customer", cust_list)
    
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if selected_cust != "All Customers":
        query = query.eq("customer", selected_cust)
    
    data = query.execute().data
    
    if data:
        st.download_button("📥 Download Filtered PDF", generate_pdf(data), f"BG_Report_{selected_cust}.pdf")
        for log in data:
            with st.expander(f"📦 Job: {log['job_code']} | Customer: {log['customer']}"):
                col_img, col_info = st.columns([1,2])
                url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
                col_img.image(url)
                
                with col_info:
                    st.write(f"**Engineer:** {log['engineer']} | **PO:** {log['po_no']}")
                    st.write(f"**Dates:** PO: {log['po_date']} | Delivery: {log['po_delivery_date']}")
                
                st.markdown("---")
                for label, s_key, n_key in MILESTONE_MAP:
                    r1, r2, r3 = st.columns([2,1,3])
                    r1.write(f"**{label}**")
                    r2.write(f"🟢 {log[s_key]}" if log[s_key] in ["Completed", "Approved", "Submitted"] else f"🟡 {log[s_key]}")
                    r3.write(f"_{log[n_key]}_")
                
                if st.button("🗑️ Delete", key=f"del_{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    try: conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    except: pass
                    st.rerun()

with tab3:
    st.header("🛠️ Master Data Management")
    col_cust, col_job = st.columns(2)
    with col_cust:
        st.subheader("👥 Customers")
        with st.container(border=True):
            new_cust = st.text_input("New Customer Name", placeholder="e.g. Reliance Industries")
            if st.button("➕ Add Customer", use_container_width=True):
                if new_cust:
                    conn.table("customer_master").insert({"name": new_cust}).execute()
                    st.rerun()
        c_data = conn.table("customer_master").select("*").execute().data
        for c in sorted(c_data, key=lambda x: x['name']):
            c_row1, c_row2 = st.columns([3, 1])
            c_row1.text(f"• {c['name']}")
            if c_row2.button("🗑️", key=f"del_c_{c['id']}"):
                conn.table("customer_master").delete().eq("id", c['id']).execute()
                st.rerun()

    with col_job:
        st.subheader("🔢 Job Codes")
        with st.container(border=True):
            new_job = st.text_input("New Job Code", placeholder="e.g. BG-2024-001")
            if st.button("➕ Add Job Code", use_container_width=True):
                if new_job:
                    conn.table("job_master").insert({"job_code": new_job}).execute()
                    st.rerun()
        j_data = conn.table("job_master").select("*").execute().data
        for j in sorted(j_data, key=lambda x: x['job_code']):
            j_row1, j_row2 = st.columns([3, 1])
            j_row1.text(f"• {j['job_code']}")
            if j_row2.button("🗑️", key=f"del_j_{j['id']}"):
                conn.table("job_master").delete().eq("id", j['id']).execute()
                st.rerun()
