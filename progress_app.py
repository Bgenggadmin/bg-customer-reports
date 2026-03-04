import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os
import requests
from tempfile import NamedTemporaryFile

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATOR WITH PHOTO SUPPORT ---
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
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Submitted By", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date', 'N/A')}", 1, 1)
        pdf.ln(5)

        # Milestone Logic (All 9 Milestone Rows)
        ms_list = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries Status", 'sub_del', 'sub_del_note'),
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

        # --- PHOTO INTEGRATION INTO PDF ---
        current_job = log.get('job_code')
        try:
            res = conn.client.storage.from_("progress-photos").list()
            # Find photos belonging to this job
            job_files = [f['name'] for f in res if f['name'].startswith(current_job)]
            
            if job_files:
                pdf.add_page()
                pdf.set_font("helvetica", "B", 11)
                pdf.cell(0, 10, f"SITE PROGRESS PHOTOS - JOB: {current_job}", 0, 1, "L")
                
                x_start, y_start = 10, 35
                img_w, img_h = 90, 65
                
                for idx, f_name in enumerate(job_files[:4]): # Max 4 photos per job in PDF
                    url = conn.client.storage.from_("progress-photos").get_public_url(f_name)
                    img_data = requests.get(url).content
                    
                    with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(img_data)
                        tmp_path = tmp.name
                    
                    row, col = idx // 2, idx % 2
                    pdf.image(tmp_path, x_start + (col * 100), y_start + (row * 75), img_w, img_h)
                    os.unlink(tmp_path)
        except Exception as e:
            print(f"PDF Image Error: {e}")

    return bytes(pdf.output())

# --- MASTER DATA & TABS ---
@st.cache_data(ttl=5)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return sorted(c), sorted(j)
    except: return [], []

c_list, j_list = get_masters()
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# --- TAB 1: ENTRY FORM ---
with t1:
    with st.form("main_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        cust, job, eq = col1.selectbox("Customer", c_list), col2.selectbox("Job Code", j_list), col3.text_input("Equipment")
        
        col4, col5, col6 = st.columns(3)
        po_n, po_d, eng = col4.text_input("PO No."), col5.date_input("PO Date"), col6.text_input("Engineer")

        st.markdown("---")
        def custom_row(label, opts, skey, nkey):
            c1, c2 = st.columns([1, 2])
            s = c1.selectbox(label, opts, key=skey)
            n = c2.text_input(f"Remarks for {label}", key=nkey)
            return s, n

        opts = ["Pending", "In-Progress", "Hold", "Completed"]
        d_s, d_n = custom_row("Drawing Submission", ["In-Progress", "Submitted"], "s1", "n1")
        da_s, da_n = custom_row("Drawing Approval", ["Pending", "Approved"], "s2", "n2")
        rm_s, rm_n = custom_row("RM Status", opts, "s3", "n3")
        sd_s, sd_n = custom_row("Sub-deliveries", opts, "s4", "n4")
        fb_s, fb_n = custom_row("Fabrication Status", opts, "s5", "n5")
        bf_s, bf_n = custom_row("Buffing Status", opts, "s6", "n6")
        ts_s, ts_n = custom_row("Testing Status", opts, "s7", "n7")
        qc_s, qc_n = custom_row("QC Status", opts, "s8", "n8")
        fat_s, fat_n = custom_row("FAT Status", opts, "s9", "n9")

        st.markdown("---")
        job_photos = st.file_uploader("Upload Photos", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync All Fields to Cloud"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "draw_sub": d_s, "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n,
                "rm_status": rm_s, "rm_note": rm_n, "sub_del": sd_s, "sub_del_note": sd_n,
                "fab_status": fb_s, "remarks": fb_n, "buff_stat": bf_s, "buff_note": bf_n,
                "testing": ts_s, "test_note": ts_n, "qc_stat": qc_s, "qc_note": qc_n, "fat_stat": fat_s, "fat_note": fat_n
            }).execute()
            
            if job_photos:
                for photo in job_photos:
                    path = f"{job}_{photo.name.replace(' ', '_')}"
                    conn.client.storage.from_("progress-photos").upload(path=path, file=photo.getvalue(), file_options={"upsert": "true"})
            st.success("Synchronized!"); st.rerun()

# --- TAB 2: ARCHIVE ---
with t2:
    sel_cust = st.selectbox("Filter Archive", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            st.download_button("📥 Download PDF with Photos", create_bulk_pdf(sel_cust, data), f"BG_{sel_cust}.pdf", "application/pdf")
        
        for log in data:
            current_job = log.get('job_code')
            with st.expander(f"📦 Job: {current_job} | Eq: {log.get('equipment')}"):
                # Web Photo Display
                try:
                    res = conn.client.storage.from_("progress-photos").list()
                    job_files = [f['name'] for f in res if f['name'].startswith(current_job)]
                    if job_files:
                        cols = st.columns(len(job_files))
                        for i, f in enumerate(job_files): cols[i].image(conn.client.storage.from_("progress-photos").get_public_url(f))
                except: pass
                st.table([{"Milestone": "Fabrication", "Status": log.get('fab_status'), "Note": log.get('remarks')}])

# --- TAB 3: MASTERS ---
with t3:
    if st.text_input("Admin PIN", type="password") == "1234":
        c1, c2 = st.columns(2)
        with c1:
            nc = st.text_input("Add Customer")
            if st.button("Save C"): conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
        with c2:
            nj = st.text_input("Add Job")
            if st.button("Save J"): conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
