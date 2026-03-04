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

# --- PDF GENERATOR ---
class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font("helvetica", "B", 15)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "B&G ENGINEERING", 0, 1, "R")
        self.set_font("helvetica", "B", 8)
        self.cell(0, 5, "EVAPORATION | MIXING | DRYING", 0, 1, "R")
        self.ln(10)
        self.set_draw_color(0, 51, 102)
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Engineering Industries", 0, 0, "C")

def create_bulk_pdf(customer_name, logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" PROJECT PROGRESS REPORT - {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        pdf.ln(4)
        
        # Header Info Table
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Engineer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        pdf.ln(5)

        # Milestone Table
        ms_list = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), ("QC Status", 'qc_stat', 'qc_note'), ("FAT Status", 'fat_stat', 'fat_note')
        ]
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(70, 8, " Milestone", 1, 0, "L", fill=True)
        pdf.cell(40, 8, " Status", 1, 0, "L", fill=True)
        pdf.cell(80, 8, " Remarks", 1, 1, "L", fill=True)
        
        pdf.set_font("helvetica", "", 8)
        for label, skey, nkey in ms_list:
            pdf.cell(70, 7, f" {label}", 1)
            pdf.cell(40, 7, f" {log.get(skey, 'N/A')}", 1)
            pdf.cell(80, 7, f" {log.get(nkey, '')}", 1, 1)

        # --- FIXED PDF PHOTO LOGIC (STRICT JOB MATCHING) ---
        current_job = log.get('job_code')
        try:
            res = conn.client.storage.from_("progress-photos").list()
            # Added "_" check to ensure strict matching (e.g., Job 101 vs 1011)
            job_files = [f['name'] for f in res if f['name'].startswith(f"{current_job}_")]
            
            if job_files:
                pdf.ln(8)
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 7, f"SITE PHOTOS - JOB: {current_job}", 0, 1, "L")
                
                x_start, y_start = 10, pdf.get_y() + 2
                img_w_mm, img_h_mm = 35, 45 # passport size
                gap_mm = 5 
                
                for idx, f_name in enumerate(job_files[:4]): 
                    url = conn.client.storage.from_("progress-photos").get_public_url(f_name)
                    img_data = requests.get(url).content
                    img = Image.open(BytesIO(img_data))
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.thumbnail((400, 500))
                    
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG', quality=85)
                    img_bytes.seek(0)

                    row, col = idx // 2, idx % 2
                    pdf.image(img_bytes, x_start + (col * (img_w_mm + gap_mm)), y_start + (row * (img_h_mm + gap_mm)), img_w_mm, img_h_mm)
        except: pass

    return bytes(pdf.output())

# --- MASTER DATA ---
@st.cache_data(ttl=5)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return sorted(c), sorted(j)
    except: return [], []

c_list, j_list = get_masters()
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust, job, eq = c1.selectbox("Customer", c_list), c2.selectbox("Job Code", j_list), c3.text_input("Equipment")
        c4, c5, c6 = st.columns(3)
        po_n, po_d, eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")

        st.markdown("---")
        def custom_row(label, opts, skey, nkey):
            co1, co2 = st.columns([1, 2])
            s = co1.selectbox(label, opts, key=skey)
            n = co2.text_input(f"Remarks for {label}", key=nkey)
            return s, n

        opts = ["Pending", "In-Progress", "Hold", "Completed"]
        d_s, d_n = custom_row("Drawing Submission", ["In-Progress", "Submitted"], "s1", "n1")
        da_s, da_n = custom_row("Drawing Approval", ["Pending", "Approved"], "s2", "n2")
        fb_s, fb_n = custom_row("Fabrication Status", opts, "s5", "n5")

        st.markdown("---")
        job_photos = st.file_uploader("Upload Photos", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync All Fields"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, 
                "po_date": str(po_d), "engineer": eng, "draw_sub": d_s, 
                "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n, 
                "fab_status": fb_s, "remarks": fb_n
            }).execute()
            
            if job_photos:
                for photo in job_photos:
                    # STRICT NAMING: JobCode_Filename
                    path = f"{job}_{photo.name.replace(' ', '_')}"
                    conn.client.storage.from_("progress-photos").upload(path=path, file=photo.getvalue(), file_options={"upsert": "true"})
            st.success("Done!"); st.rerun()

with t2:
    sel_cust = st.selectbox("Filter Archive", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            pdf_bytes = create_bulk_pdf(sel_cust, data)
            st.download_button("📥 Download PDF with Photos", pdf_bytes, f"BG_{sel_cust}.pdf", "application/pdf")
        
        for log in data:
            current_job = log.get('job_code')
            with st.expander(f"📦 Job: {current_job} | Eq: {log.get('equipment')}"):
                
                # --- FIXED ARCHIVE PHOTO LOGIC (STRICT JOB MATCHING) ---
                try:
                    res = conn.client.storage.from_("progress-photos").list()
                    # Added "_" check to match Tab 1 naming convention
                    job_files = [f['name'] for f in res if f['name'].startswith(f"{current_job}_")]
                    if job_files:
                        st.markdown("### 📷 Site Photos")
                        p_cols = st.columns(4)
                        for idx, f_name in enumerate(job_files):
                            url = conn.client.storage.from_("progress-photos").get_public_url(f_name)
                            p_cols[idx % 4].image(url, use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading photos: {e}")
                
                st.write(f"**Fabrication Status:** {log.get('fab_status')}")
                st.write(f"**Remarks:** {log.get('remarks')}")
