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

# 2. THE MASTER MAPPING (Add or change fields here, and the whole app updates)
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

# --- PDF ENGINE ---
def generate_pdf(logs):
    pdf = FPDF()
    for log in logs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "C")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"JOB REPORT: {log['job_code']} | ID: {log['id']}", 1, 1, "C", fill=False)
        
        # Header Box
        pdf.set_font("Arial", "B", 8)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1, f2 = HEADER_FIELDS[i], HEADER_FIELDS[i+1]
            pdf.cell(30, 7, f1.replace('_',' ').title(), 1); pdf.cell(65, 7, str(log.get(f1,'')), 1)
            pdf.cell(30, 7, f2.replace('_',' ').title(), 1); pdf.cell(65, 7, str(log.get(f2,'')), 1); pdf.ln()

        # Photo
        try:
            img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((400, 400))
                buf = BytesIO(); img.save(buf, format="JPEG")
                pdf.image(buf, 75, pdf.get_y()+5, 55, 40); pdf.set_y(pdf.get_y()+50)
        except: pdf.ln(5)

        # Milestone Table
        pdf.set_font("Arial", "B", 8)
        pdf.cell(60, 7, "Milestone", 1); pdf.cell(35, 7, "Status", 1); pdf.cell(95, 7, "Remarks", 1, 1)
        pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(s_key,'-')), 1); pdf.cell(95, 6, str(log.get(n_key,'-')), 1, 1)
    return bytes(pdf.output())

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    with st.form("new_entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment")
        
        c4, c5, c6 = st.columns(3)
        f_po_n, f_po_d, f_eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        
        c7, c8 = st.columns(2)
        f_p_del, f_r_del = c7.date_input("PO Delivery Date"), c8.date_input("Revised Dispatch Date")
        
        st.divider()
        cam_photo = st.camera_input("📸 Capture Photo")
        
        m_inputs = {}
        for label, s_key, n_key in MILESTONE_MAP:
            col1, col2 = st.columns([1,2])
            opts = ["Pending", "In-Progress", "Submitted", "Approved", "Completed"]
            m_inputs[s_key] = col1.selectbox(label, opts, key=f"s_{s_key}")
            m_inputs[n_key] = col2.text_input(f"Remarks: {label}", key=f"n_{n_key}")

        if st.form_submit_button("🚀 Save & Sync"):
            if not f_cust or not cam_photo:
                st.error("Select Customer and Take a Photo!")
            else:
                payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                    **m_inputs
                }
                res = conn.table("progress_logs").insert(payload).execute()
                if res.data:
                    new_id = res.data[0]['id']
                    conn.client.storage.from_("progress-photos").upload(f"{new_id}.jpg", cam_photo.getvalue(), {"upsert":"true"})
                    st.success(f"Saved Successfully! ID: {new_id}"); st.rerun()

with tab2:
    data = conn.table("progress_logs").select("*").order("id", desc=True).execute().data
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
                # Clean table view
                for label, s_key, n_key in MILESTONE_MAP:
                    r1, r2, r3 = st.columns([2,1,3])
                    r1.write(f"**{label}**")
                    r2.write(f"🟢 {log[s_key]}" if log[s_key] in ["Completed", "Approved"] else f"🟡 {log[s_key]}")
                    r3.write(f"_{log[n_key]}_")
                
                if st.button("🗑️ Delete", key=f"del_{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    try: conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    except: pass
                    st.rerun()

with tab3:
    st.header("🛠️ Master Data Management")
    st.info("Add or remove Customers and Job Codes here. These will appear in your 'New Entry' dropdowns.")
    
    col_cust, col_job = st.columns(2)
    
    # --- CUSTOMER SECTION ---
    with col_cust:
        st.subheader("👥 Customers")
        with st.container(border=True):
            new_cust = st.text_input("New Customer Name", placeholder="e.g. Reliance Industries")
            if st.button("➕ Add Customer", use_container_width=True):
                if new_cust:
                    conn.table("customer_master").insert({"name": new_cust}).execute()
                    st.success(f"Added {new_cust}")
                    st.rerun()
                else:
                    st.error("Enter a name first")
            
        st.write("**Current Customers:**")
        # Fetch fresh list to display with delete buttons
        c_data = conn.table("customer_master").select("*").execute().data
        for c in sorted(c_data, key=lambda x: x['name']):
            c_row1, c_row2 = st.columns([3, 1])
            c_row1.text(f"• {c['name']}")
            if c_row2.button("🗑️", key=f"del_c_{c['id']}"):
                conn.table("customer_master").delete().eq("id", c['id']).execute()
                st.rerun()

    # --- JOB CODE SECTION ---
    with col_job:
        st.subheader("🔢 Job Codes")
        with st.container(border=True):
            new_job = st.text_input("New Job Code", placeholder="e.g. BG-2024-001")
            if st.button("➕ Add Job Code", use_container_width=True):
                if new_job:
                    conn.table("job_master").insert({"job_code": new_job}).execute()
                    st.success(f"Added {new_job}")
                    st.rerun()
                else:
                    st.error("Enter a code first")
            
        st.write("**Current Job Codes:**")
        # Fetch fresh list to display with delete buttons
        j_data = conn.table("job_master").select("*").execute().data
        for j in sorted(j_data, key=lambda x: x['job_code']):
            j_row1, j_row2 = st.columns([3, 1])
            j_row1.text(f"• {j['job_code']}")
            if j_row2.button("🗑️", key=f"del_j_{j['id']}"):
                conn.table("job_master").delete().eq("id", j['id']).execute()
                st.rerun()
