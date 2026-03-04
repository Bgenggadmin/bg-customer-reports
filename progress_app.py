import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATOR (FULL DATA TABLE + SMALL PHOTOS) ---
class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 30)
            except: pass
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "R")
        self.ln(5)
        self.line(10, 25, 200, 25)

def create_filtered_pdf(logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(235, 235, 235)
        pdf.cell(0, 8, f" JOB REPORT: {log.get('job_code')}", 1, 1, "C", fill=True)
        pdf.ln(3)
        
        # --- ALL 8 HEADER FIELDS ---
        pdf.set_font("helvetica", "B", 8)
        header_data = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Job Code", log.get('job_code')), ("Engineer", log.get('engineer')),
            ("PO No.", log.get('po_no')), ("PO Date", log.get('po_date')),
            ("PO Delivery", log.get('po_delivery_date')), ("Rev. Dispatch", log.get('exp_dispatch_date'))
        ]
        for i in range(0, len(header_data), 2):
            pdf.cell(30, 7, f" {header_data[i][0]}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {header_data[i][1]}", 1, 0)
            pdf.cell(30, 7, f" {header_data[i+1][0]}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {header_data[i+1][1]}", 1, 1)
        
        pdf.ln(2)

        # --- ALL 9 MILESTONES (18 FIELDS TOTAL) ---
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone Item", 1, 0, 'C', True)
        pdf.cell(35, 7, " Status", 1, 0, 'C', True)
        pdf.cell(95, 7, " Detailed Remarks", 1, 1, 'C', True)
        
        pdf.set_font("helvetica", "", 8)
        milestones = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), 
            ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), 
            ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), 
            ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), 
            ("QC Status", 'qc_stat', 'qc_note'), 
            ("FAT Status", 'fat_stat', 'fat_note')
        ]
        for label, skey, nkey in milestones:
            pdf.cell(60, 6, f" {label}", 1)
            pdf.cell(35, 6, f" {log.get(skey, '-')}", 1, 0, 'C')
            pdf.cell(95, 6, f" {log.get(nkey, '-')}", 1, 1)

        # --- ALL PHOTOS (SMALL PASSPORT SIZE BELOW TABLE) ---
        current_job = log.get('job_code')
        try:
            res = conn.client.storage.from_("progress-photos").list()
            job_files = [f['name'] for f in res if f['name'].startswith(f"{current_job}_")]
            if job_files:
                pdf.ln(4)
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 7, "SITE PHOTOS", 0, 1, "L")
                x, y = 10, pdf.get_y()
                for idx, f_name in enumerate(job_files[:8]): # Show up to 8 photos
                    url = conn.client.storage.from_("progress-photos").get_public_url(f_name)
                    img_data = requests.get(url).content
                    img = Image.open(BytesIO(img_data)).convert('RGB')
                    img.thumbnail((300, 400))
                    buf = BytesIO()
                    img.save(buf, format='JPEG', quality=50) # Further reduced for 50KB target
                    
                    row, col = idx // 4, idx % 4
                    pdf.image(buf, x + (col * 45), y + (row * 45), 35, 40)
        except: pass
    return bytes(pdf.output())

# --- FETCH MASTERS ---
c_list, j_list = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data]), sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])

t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive & Delete", "🛠️ Masters"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust, job, eq = c1.selectbox("Customer", c_list), c2.selectbox("Job Code", j_list), c3.text_input("Equipment")
        c4, c5, c6 = st.columns(3)
        po_n, po_d, eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        c7, c8 = st.columns(2)
        po_disp, rev_disp = c7.date_input("PO Dispatch Date"), c8.date_input("Revised Dispatch Date")

        st.markdown("---")
        # DROPDOWNS AS SPECIFIED
        opts_std = ["Pending", "In-Progress", "Hold", "Completed"]
        
        s1, n1 = st.columns([1,2])[0].selectbox("Drawing Submission", ["In-Progress", "Submitted"]), st.columns([1,2])[1].text_input("Remarks: Drawing Sub", key="n1")
        s2, n2 = st.columns([1,2])[0].selectbox("Drawing Approval", ["Pending", "Approved"]), st.columns([1,2])[1].text_input("Remarks: Drawing App", key="n2")
        
        def row_ui(label, key_s, key_n):
            col_a, col_b = st.columns([1, 2])
            s = col_a.selectbox(label, opts_std, key=key_s)
            n = col_b.text_input(f"Remarks: {label}", key=key_n)
            return s, n

        s3, n3 = row_ui("RM Status", "s3", "n3")
        s4, n4 = row_ui("Sub-deliveries", "s4", "n4")
        s5, n5 = row_ui("Fabrication Status", "s5", "n5")
        s6, n6 = row_ui("Buffing Status", "s6", "n6")
        s7, n7 = row_ui("Testing Status", "s7", "n7")
        s8, n8 = row_ui("QC Status", "s8", "n8")
        s9, n9 = row_ui("FAT Status", "s9", "n9")

        st.markdown("---")
        photos = st.file_uploader("Upload Photos (Multiple Allowed)", accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync All 24+ Fields"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d), "engineer": eng,
                "po_delivery_date": str(po_disp), "exp_dispatch_date": str(rev_disp),
                "draw_sub": s1, "draw_sub_note": n1, "draw_app": s2, "draw_app_note": n2,
                "rm_status": s3, "rm_note": n3, "sub_del": s4, "sub_del_note": n4,
                "fab_status": s5, "remarks": n5, "buff_stat": s6, "buff_note": n6,
                "testing": s7, "test_note": n7, "qc_stat": s8, "qc_note": n8, "fat_stat": s9, "fat_note": n9
            }).execute()
            
            if photos:
                for p in photos:
                    # Unique timestamping to prevent "latest photo only" issue
                    filename = f"{job}_{datetime.now().strftime('%H%M%S')}_{p.name}"
                    conn.client.storage.from_("progress-photos").upload(path=filename, file=p.getvalue())
            st.success("Synchronized Successfully!"); st.rerun()

with t2:
    sel_cust = st.selectbox("Filter by Customer", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            st.download_button(f"📥 Download PDF for {sel_cust}", create_filtered_pdf(data), f"{sel_cust}_Report.pdf")
        
        for log in data:
            c_info, c_del = st.columns([5, 1])
            c_info.write(f"**Job: {log.get('job_code')}** | {log.get('customer')} | {log.get('equipment')}")
            if c_del.button("🗑️ Delete", key=f"del_{log.get('id')}"):
                conn.table("progress_logs").delete().eq("id", log.get('id')).execute()
                st.rerun()
            
            with st.expander("View Full Fields & Photos"):
                # Photo Display
                cur_job = log.get('job_code')
                res = conn.client.storage.from_("progress-photos").list()
                job_files = [f['name'] for f in res if f['name'].startswith(f"{cur_job}_")]
                if job_files:
                    cols = st.columns(6)
                    for i, f in enumerate(job_files):
                        url = conn.client.storage.from_("progress-photos").get_public_url(f)
                        cols[i % 6].image(url, use_container_width=True)
                
                # Full Field Table (Verification)
                st.table({k: [v] for k, v in log.items() if v})
