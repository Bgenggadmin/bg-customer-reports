import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. SETUP (Line 10) - Fixed: Removed duplicate setup and config dots
st.set_page_config(page_title="B&G Hub 2.0", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# 2. MASTER MAPPINGS (Line 14)
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

# 3. DATA FETCHING (Line 29)
try:
    customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
    jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])
except:
    customers, jobs = [], []

# 4. PDF ENGINE (Line 36) - Fixed: Defined before tabs
def generate_pdf(logs):
    pdf = FPDF()
    for log in logs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "C")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"JOB REPORT: {log['job_code']} | ID: {log['id']}", 1, 1, "C", fill=False)
        
        pdf.set_font("Arial", "B", 8)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1, f2 = HEADER_FIELDS[i], HEADER_FIELDS[i+1]
            pdf.cell(30, 7, f1.replace('_',' ').title(), 1); pdf.cell(65, 7, str(log.get(f1,'')), 1)
            pdf.cell(30, 7, f2.replace('_',' ').title(), 1); pdf.cell(65, 7, str(log.get(f2,'')), 1); pdf.ln()

        try:
            img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((400, 400))
                buf = BytesIO(); img.save(buf, format="JPEG")
                pdf.image(buf, 75, pdf.get_y()+5, 55, 40); pdf.set_y(pdf.get_y()+50)
        except: pdf.ln(5)

        pdf.set_font("Arial", "B", 8)
        pdf.cell(60, 7, "Milestone", 1); pdf.cell(35, 7, "Status", 1); pdf.cell(95, 7, "Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(s_key,'-')), 1); pdf.cell(95, 6, str(log.get(n_key,'-')), 1, 1)
    return bytes(pdf.output())

# 5. APP TABS (Line 66)
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
                st.error("Missing required data!")
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
                        st.success(f"✅ Success! Entry ID: {new_id}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {str(e)}")

with tab2:
    data_res = conn.table("progress_logs").select("*").order("id", desc=True).execute()
    data = data_res.data if data_res.data else []
    if data:
        st.download_button("📥 Download Report PDF", generate_pdf(data), "BG_Report.pdf")
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
        new_cust = st.text_input("New Customer Name")
        if st.button("➕ Add Customer"):
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
        new_job = st.text_input("New Job Code")
        if st.button("➕ Add Job Code"):
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
