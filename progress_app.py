import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE
st.set_page_config(page_title="B&G Hub Final", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- A. REFRESH MASTERS ---
try:
    c_res = conn.table("customer_master").select("*").execute()
    j_res = conn.table("job_master").select("*").execute()
    customers = sorted([d['name'] for d in c_res.data]) if c_res.data else []
    jobs = sorted([d['job_code'] for d in j_res.data]) if j_res.data else []
except:
    customers, jobs = [], []

# --- B. PDF GENERATOR (VERIFIED ALL FIELDS) ---
class ProgressPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES - PROGRESS REPORT", 0, 1, "R")
        self.line(10, 22, 200, 22)
        self.ln(5)

def create_report_pdf(logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" JOB CODE: {log.get('job_code')} | DATE: {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        
        # --- HEADER (8 FIELDS) ---
        pdf.set_font("helvetica", "B", 8)
        h = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Engineer", log.get('engineer')), ("PO No.", log.get('po_no')),
            ("PO Date", log.get('po_date')), ("PO Delivery", log.get('po_delivery_date')),
            ("Revised Disp", log.get('exp_dispatch_date')), ("Entry ID", str(log.get('id')))
        ]
        for i in range(0, len(h), 2):
            pdf.cell(30, 7, h[i][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h[i][1]), 1, 0)
            pdf.cell(30, 7, h[i+1][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h[i+1][1]), 1, 1)

        # --- PHOTO SECTION (FIXED AT TOP) ---
        e_id = str(log.get('id'))
        try:
            u = conn.client.storage.from_("progress-photos").get_public_url(f"{e_id}.jpg")
            r = requests.get(u)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert('RGB')
                img.thumbnail((400, 400))
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=70)
                pdf.image(buf, 75, pdf.get_y() + 5, 60, 45) # Centered Photo
                pdf.set_y(pdf.get_y() + 55)
        except: pdf.ln(10)

        # --- MILESTONE TABLE (18 FIELDS) ---
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone Item", 1, 0, 'L', True); pdf.cell(35, 7, " Status", 1, 0, 'L', True); pdf.cell(95, 7, " Detailed Remarks", 1, 1, 'L', True)
        pdf.set_font("helvetica", "", 8)
        m_map = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), ("QC Status", 'qc_stat', 'qc_note'), ("FAT Status", 'fat_stat', 'fat_note')
        ]
        for label, skey, nkey in m_map:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)
            
    return bytes(pdf.output())

# --- C. APP TABS ---
t1, t2, t3 = st.tabs(["📸 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("master_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment")
        
        c4, c5, c6 = st.columns(3)
        f_po_n, f_po_d, f_eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        c7, c8 = st.columns(2)
        f_p_del, f_r_del = c7.date_input("PO Delivery"), c8.date_input("Revised Dispatch")

        st.markdown("---")
        st.write("### 📷 Step 1: Capture Progress Photo")
        cam_photo = st.camera_input("Take Photo")

        st.markdown("---")
        st.write("### 📊 Step 2: Milestone Status")
        
        # Drawing Logic
        col_a1, col_a2 = st.columns([1,2])
        v1s = col_a1.selectbox("Drawing Submission", ["In-Progress", "Submitted"])
        v1n = col_a2.text_input("Drawing Sub Remarks")
        
        col_b1, col_b2 = st.columns([1,2])
        v2s = col_b1.selectbox("Drawing Approval", ["Pending", "Approved"])
        v2n = col_b2.text_input("Drawing App Remarks")

        def milestone_ui(label, kid):
            ca, cb = st.columns([1,2])
            s = ca.selectbox(label, ["Pending", "In-Progress", "Hold", "Completed"], key=f"s{kid}")
            n = cb.text_input(f"Remarks: {label}", key=f"n{kid}")
            return s, n

        v3s, v3n = milestone_ui("RM Status", "3")
        v4s, v4n = milestone_ui("Sub-deliveries", "4")
        v5s, v5n = milestone_ui("Fabrication Status", "5")
        v6s, v6n = milestone_ui("Buffing Status", "6")
        v7s, v7n = milestone_ui("Testing Status", "7")
        v8s, v8n = milestone_ui("QC Status", "8")
        v9s, v9n = milestone_ui("FAT Status", "9")

        if st.form_submit_button("🚀 Final Sync"):
            if not f_cust or not f_job or not cam_photo:
                st.error("Missing Customer, Job Code, or Photo!")
            else:
                # 1. DB Insert
                res = conn.table("progress_logs").insert({
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq, "po_no": f_po_n, 
                    "po_date": str(f_po_d), "engineer": f_eng, "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                    "draw_sub": v1s, "draw_sub_note": v1n, "draw_app": v2s, "draw_app_note": v2n,
                    "rm_status": v3s, "rm_note": v3n, "sub_del": v4s, "sub_del_note": v4n,
                    "fab_status": v5s, "remarks": v5n, "buff_stat": v6s, "buff_note": v6n,
                    "testing": v7s, "test_note": v7n, "qc_stat": v8s, "qc_note": v8n, "fat_stat": v9s, "fat_note": v9n
                }).execute()
                
                if res.data:
                    curr_id = str(res.data[0]['id'])
                    # 2. Upload Photo as ID.jpg
                    conn.client.storage.from_("progress-photos").upload(
                        path=f"{curr_id}.jpg", file=cam_photo.getvalue(), file_options={"upsert": "true"}
                    )
                    st.success(f"Synced Successfully! ID: {curr_id}"); st.rerun()

with t2:
    f_sel = st.selectbox("Filter by Customer", ["All"] + customers)
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if f_sel != "All": query = query.eq("customer", f_sel)
    data = query.execute().data
    
    if data:
        st.download_button("📥 Download PDF Report", create_report_pdf(data), "BG_Report.pdf")
        for log in data:
            with st.expander(f"Job: {log['job_code']} | ID: {log['id']} ({log['customer']})"):
                c_img, c_txt = st.columns([1,2])
                p_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
                c_img.image(p_url, use_container_width=True)
                c_txt.json(log)
                if st.button("🗑️ Delete Record", key=f"d{log['id']}"):
                    conn.table("progress_logs").delete().eq("id", log['id']).execute()
                    try: conn.client.storage.from_("progress-photos").remove([f"{log['id']}.jpg"])
                    except: pass
                    st.rerun()

with t3:
    st.subheader("🛠️ Master Data Management")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        new_c = st.text_input("New Customer")
        if st.button("Add Customer") and new_c:
            conn.table("customer_master").insert({"name": new_c}).execute(); st.rerun()
        st.write("Current Customers:")
        for c in customers: st.text(f"• {c}")
    with col_m2:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job Code") and new_j:
            conn.table("job_master").insert({"job_code": new_j}).execute(); st.rerun()
        st.write("Current Job Codes:")
        for j in jobs: st.text(f"• {j}")
