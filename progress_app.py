import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
import os

# 1. INITIALIZE CONNECTION & CONFIG
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

        # Primary Info Table - Capturing ALL header fields [cite: 2, 7, 11-17]
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(35, 8, "Customer", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('customer', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Equipment", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('equipment', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Job Code", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('job_code', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Submitted By", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('engineer', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO No.", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_no', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "PO Date", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_date', 'N/A')}", 1, 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Target Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('po_delivery_date', 'N/A')}", 1)
        pdf.set_font("helvetica", "B", 9); pdf.cell(35, 8, "Revised Dispatch", 1); pdf.set_font("helvetica", "", 9); pdf.cell(60, 8, f" {log.get('exp_dispatch_date', 'N/A')}", 1, 1)
        pdf.ln(5)

        # Milestone Table - Ensuring NO milestones are omitted 
        pdf.set_font("helvetica", "B", 9); pdf.set_fill_color(220, 230, 241)
        pdf.cell(70, 8, " Milestone", 1, 0, "L", fill=True)
        pdf.cell(40, 8, " Status", 1, 0, "L", fill=True)
        pdf.cell(80, 8, " Remarks", 1, 1, "L", fill=True)

        pdf.set_font("helvetica", "", 8)
        ms_items = [
            ("Drawing Submission", log.get('draw_sub'), log.get('draw_sub_note')),
            ("Drawing Approval", log.get('draw_app'), log.get('draw_app_note')),
            ("RM Status", log.get('rm_status'), log.get('rm_note')),
            ("Sub-deliveries Status", log.get('sub_del'), log.get('sub_del_note')),
            ("Fabrication Status", log.get('fab_status'), log.get('remarks')),
            ("Buffing/Finishing Status", log.get('buff_stat'), log.get('buff_note')),
            ("Testing", log.get('testing'), log.get('test_note')),
            ("QC/Dispatch Status", log.get('qc_stat'), log.get('qc_note')),
            ("FAT", log.get('fat_stat'), log.get('fat_note'))
        ]
        for m_name, m_val, m_note in ms_items:
            pdf.cell(70, 7, f" {m_name}", 1)
            pdf.cell(40, 7, f" {m_val if m_val else 'In-Progress'}", 1)
            pdf.cell(80, 7, f" {m_note if m_note else ''}", 1, 1)
    return bytes(pdf.output())

# --- DATA HELPERS ---
@st.cache_data(ttl=10)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return c, j
    except: return [], []

c_list, j_list = get_masters()

# --- APP LAYOUT ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        cust = col1.selectbox("Customer", c_list)
        job = col2.selectbox("Job Code", j_list)
        eq = col3.text_input("Equipment (e.g., 5KL SSR, 250 LTS SSR)")

        col4, col5, col6 = st.columns(3)
        po_n = col4.text_input("PO No.")
        po_d = col5.date_input("PO Date")
        eng = col6.text_input("Engineer In-Charge")

        col7, col8 = st.columns(2)
        po_del = col7.date_input("Target Dispatch")
        rev_del = col8.date_input("Revised Dispatch")

        st.markdown("### 📊 Specific Milestone Updates")
        
        # Unique Dropdowns per Category
        draw_opts = ["In-Progress", "Submitted", "Approved", "N/A"]
        rm_opts = ["In-Progress", "Ordered", "Received", "N/A"]
        
        def m_row(label, key1, key2, opts):
            c1, c2 = st.columns([1, 2])
            val = c1.selectbox(label, opts, key=key1)
            note = c2.text_input(f"Remarks for {label}", key=key2)
            return val, note

        d_s, d_n = m_row("Drawing Submission", "ds1", "dn1", draw_opts)
        da_s, da_n = m_row("Drawing Approval", "da1", "da2", ["In-Progress", "Approved"])
        r_s, r_n = m_row("RM Status", "rs1", "rn1", rm_opts)
        f_s = st.selectbox("Fabrication Status", ["In-Progress", "Completed"], key="fs1")
        f_rem = st.text_area("General Fabrication Remarks")

        if st.form_submit_button("🚀 Sync to Cloud"):
            conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "po_delivery_date": str(po_del), "exp_dispatch_date": str(rev_del),
                "draw_sub": d_s, "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n,
                "rm_status": r_s, "rm_note": r_n, "fab_status": f_s, "remarks": f_rem
            }).execute()
            st.success("Entry Saved Successfully!"); st.rerun()

with t2:
    sel_cust = st.selectbox("View Entries for Customer", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            pdf_bytes = create_bulk_pdf(sel_cust, data)
            st.download_button(f"📥 Download {sel_cust} Report", pdf_bytes, f"BG_{sel_cust}.pdf")
        
        for log in data:
            with st.expander(f"📦 Job: {log.get('job_code')} | Eq: {log.get('equipment')}"):
                st.table([
                    {"Milestone": "Drawing Submission", "Status": log.get('draw_sub'), "Remarks": log.get('draw_sub_note')},
                    {"Milestone": "Drawing Approval", "Status": log.get('draw_app'), "Remarks": log.get('draw_app_note')},
                    {"Milestone": "RM Status", "Status": log.get('rm_status'), "Remarks": log.get('rm_note')},
                    {"Milestone": "Fabrication", "Status": log.get('fab_status'), "Remarks": log.get('remarks')}
                ])
    else:
        st.info("No data entries found.")

with t3:
    if st.text_input("Admin PIN", type="password") == "1234":
        c1, c2 = st.columns(2)
        with c1:
            new_cust = st.text_input("New Customer Name")
            if st.button("Add Customer"): 
                conn.table("customer_master").insert({"name": new_cust}).execute()
                st.rerun()
        with c2:
            new_job = st.text_input("New Job Code (e.g. BG-500, SSR501)")
            if st.button("Add Job Code"): 
                conn.table("job_master").insert({"job_code": new_job}).execute()
                st.rerun()
