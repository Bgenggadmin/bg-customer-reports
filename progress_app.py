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

# --- PDF GENERATOR (8 Header Fields + 9 Milestones + Photos) ---
class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font("helvetica", "B", 15)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "B&G ENGINEERING", 0, 1, "R")
        self.ln(10)
        self.set_draw_color(0, 51, 102)
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Engineering Industries", 0, 0, "C")

def create_bulk_pdf(logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" PROJECT PROGRESS REPORT - {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        pdf.ln(4)
        
        # ALL 8 HEADER FIELDS
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Engineer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Disp. Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_delivery_date')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Revised Disp.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('exp_dispatch_date')}", 1, 1)
        pdf.ln(5)

        # ALL 9 MILESTONES (Status + Remarks)
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

        # PHOTO INTEGRATION (Passport Size + Compression)
        current_job = log.get('job_code')
        try:
            res = conn.client.storage.from_("progress-photos").list()
            job_files = [f['name'] for f in res if f['name'].startswith(f"{current_job}_")]
            if job_files:
                pdf.ln(5)
                x_start, y_start = 10, pdf.get_y() + 2
                for idx, f_name in enumerate(job_files[:4]):
                    url = conn.client.storage.from_("progress-photos").get_public_url(f_name)
                    img_data = requests.get(url).content
                    img = Image.open(BytesIO(img_data))
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.thumbnail((350, 450)) # Passport size optimization
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG', quality=70) # Target 50KB
                    row, col = idx // 2, idx % 2
                    pdf.image(img_bytes, x_start + (col * 40), y_start + (row * 50), 35, 45)
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
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive & Delete", "🛠️ Masters"])

# --- TAB 1: FULL ENTRY FORM ---
with t1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust, job, eq = c1.selectbox("Customer", c_list), c2.selectbox("Job Code", j_list), c3.text_input("Equipment")
        c4, c5, c6 = st.columns(3)
        po_n, po_d, eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        c7, c8 = st.columns(2)
        po_disp, rev_disp = c7.date_input("PO Dispatch Date"), c8.date_input("Revised Dispatch Date")

        st.markdown("---")
        def custom_row(label, opts, skey, nkey):
            co1, co2 = st.columns([1, 2])
            s = co1.selectbox(label, opts, key=skey)
            n = co2.text_input(f"Remarks for {label}", key=nkey)
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

        if st.form_submit_button("🚀 Sync All 24 Fields"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d), "engineer": eng,
                "po_delivery_date": str(po_disp), "exp_dispatch_date": str(rev_disp),
                "draw_sub": d_s, "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n,
                "rm_status": rm_s, "rm_note": rm_n, "sub_del": sd_s, "sub_del_note": sd_n,
                "fab_status": fb_s, "remarks": fb_n, "buff_stat": bf_s, "buff_note": bf_n,
                "testing": ts_s, "test_note": ts_n, "qc_stat": qc_s, "qc_note": qc_n, "fat_stat": fat_s, "fat_note": fat_n
            }).execute()
            if job_photos:
                for photo in job_photos:
                    path = f"{job}_{photo.name.replace(' ', '_')}"
                    conn.client.storage.from_("progress-photos").upload(path=path, file=photo.getvalue(), file_options={"upsert": "true"})
            st.success("Synchronized!"); st.rerun()

# --- TAB 2: SUMMARY TABLE & DELETE ---
with t2:
    data = conn.table("progress_logs").select("*").order("created_at", desc=True).execute().data
    if data:
        st.markdown("### 📊 Project Summary List")
        for log in data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"**{log.get('customer')}** | {log.get('job_code')} | {log.get('equipment')}")
            c2.write(f"Status: {log.get('fab_status')}")
            
            # Delete Logic
            if c4.button("🗑️ Delete", key=f"del_{log.get('id')}"):
                conn.table("progress_logs").delete().eq("id", log.get('id')).execute()
                st.rerun()
            
            with st.expander("View Details & Photos"):
                cur_job = log.get('job_code')
                # Photos matching strictly to job reference
                try:
                    res = conn.client.storage.from_("progress-photos").list()
                    job_files = [f['name'] for f in res if f['name'].startswith(f"{cur_job}_")]
                    if job_files:
                        cols = st.columns(4)
                        for i, f in enumerate(job_files):
                            url = conn.client.storage.from_("progress-photos").get_public_url(f)
                            cols[i % 4].image(url, use_container_width=True)
                except: pass
                st.json(log) # Shows all 24 fields for verification

        st.divider()
        if st.button("📥 Download All as PDF"):
            st.download_button("Click to Save PDF", create_bulk_pdf(data), "BG_Report.pdf")
