import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

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
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Submitted By", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Disp. Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_delivery_date', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Revised Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('exp_dispatch_date', 'N/A')}", 1, 1)
        pdf.ln(5)
        ms_list = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries Status", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing/Finishing Status", 'buff_stat', 'buff_note'),
            ("Testing", 'testing', 'test_note'), ("QC/Dispatch Status", 'qc_stat', 'qc_note'), ("FAT", 'fat_stat', 'fat_note')
        ]
        pdf.set_font("helvetica", "", 8)
        for label, skey, nkey in ms_list:
            pdf.cell(70, 7, f" {label}", 1); pdf.cell(40, 7, f" {log.get(skey, 'In-Progress')}", 1); pdf.cell(80, 7, f" {log.get(nkey, '')}", 1, 1)
    return bytes(pdf.output())

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
        col1, col2, col3 = st.columns(3)
        cust = col1.selectbox("Customer", c_list)
        job = col2.selectbox("Job Code", j_list)
        eq = col3.text_input("Equipment (e.g., 5KL SSR)")

        col4, col5, col6 = st.columns(3)
        po_n = col4.text_input("PO No.")
        po_d = col5.date_input("PO Date")
        eng = col6.text_input("Engineer In-Charge")

        col7, col8 = st.columns(2)
        po_disp = col7.date_input("PO Disp. Date")
        rev_del = col8.date_input("Revised Dispatch Date")

        st.markdown("### 📊 Unique Milestone Updates")
        def custom_row(label, opts, skey, nkey):
            c1, c2 = st.columns([1, 2])
            s = c1.selectbox(label, opts, key=skey)
            n = c2.text_input(f"Remarks for {label}", key=nkey)
            return s, n

        d_s, d_n = custom_row("Drawing Submission", ["In-Progress", "Under Revision", "Submitted"], "s1", "n1")
        da_s, da_n = custom_row("Drawing Approval", ["Pending", "In-Progress", "Approved"], "s2", "n2")
        rm_s, rm_n = custom_row("RM Status", ["Pending", "Hold", "In-Progress", "Partially received", "Received"], "s3", "n3")
        sd_s, sd_n = custom_row("Sub-deliveries Status", ["Pending", "Hold", "In-Progress", "Partially received", "Received"], "s4", "n4")
        fb_s, fb_n = custom_row("Fabrication Status", ["Pending", "In-Progress", "Hold", "Completed"], "s5", "n5")
        bf_s, bf_n = custom_row("Buffing/Finishing Status", ["Hold", "Pending", "In-Progress", "Completed"], "s6", "n6")
        ts_s, ts_n = custom_row("Testing", ["Pending", "In-Progress", "Completed"], "s7", "n7")
        qc_s, qc_n = custom_row("QC/Dispatch Status", ["Hold", "Pending", "In-Progress", "Completed"], "s8", "n8")
        fat_s, fat_n = custom_row("FAT", ["Pending", "Hold", "Scheduled", "In-Progress", "Completed"], "s9", "n9")

        st.markdown("---")
        st.markdown("### 📸 Take Progress Photo")
        cam_photo = st.camera_input("Capture live image from site")

        if st.form_submit_button("🚀 Sync All Fields to Cloud"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "po_delivery_date": str(po_disp), "exp_dispatch_date": str(rev_del),
                "draw_sub": d_s, "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n,
                "rm_status": rm_s, "rm_note": rm_n, "sub_del": sd_s, "sub_del_note": sd_n,
                "fab_status": fb_s, "remarks": fb_n, "buff_stat": bf_s, "buff_note": bf_n,
                "testing": ts_s, "test_note": ts_n, "qc_stat": qc_s, "qc_note": qc_n, "fat_stat": fat_s, "fat_note": fat_n
            }).execute()
            
            if cam_photo:
                path = f"{job}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                try:
                    conn.client.storage.from_("project-photos").upload(
                        path=path, file=cam_photo.getvalue(),
                        file_options={"content-type": "image/jpeg", "x-upsert": "true"}
                    )
                except: pass

            st.success("All Fields + Photo Synchronized Successfully!")
            st.rerun()

with t2:
    sel_cust = st.selectbox("Filter Archive", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            st.download_button("📥 Download Official PDF", create_bulk_pdf(sel_cust, data), f"BG_{sel_cust}.pdf")
        
        for log in data:
            with st.expander(f"📦 Job: {log.get('job_code')} | Eq: {log.get('equipment')}"):
                try:
                    files = conn.client.storage.from_("project-photos").list()
                    job_files = sorted([f['name'] for f in files if f['name'].startswith(log.get('job_code'))], reverse=True)
                    if job_files:
                        url = conn.client.storage.from_("project-photos").get_public_url(job_files[0])
                        st.image(url, caption="Latest Captured Photo", width=500)
                except: pass
                
                st.table([
                    {"Milestone": "Drawing Submission", "Status": log.get('draw_sub'), "Note": log.get('draw_sub_note')},
                    {"Milestone": "Fabrication", "Status": log.get('fab_status'), "Note": log.get('remarks')},
                    {"Milestone": "Testing", "Status": log.get('testing'), "Note": log.get('test_note')}
                ])

with t3:
    if st.text_input("Admin PIN", type="password") == "1234":
        c1, c2 = st.columns(2)
        with c1:
            nc = st.text_input("Add New Customer")
            if st.button("Save Customer"): conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
        with c2:
            nj = st.text_input("Add New Job Code")
            if st.button("Save Job Code"): conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
