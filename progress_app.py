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

        # Primary Info Table (All 8 Fields from your PDF)
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

        # Milestone Table (All 9 Items from PDF)
        pdf.set_font("helvetica", "B", 9); pdf.set_fill_color(220, 230, 241)
        pdf.cell(70, 8, " Milestone", 1, 0, "L", fill=True)
        pdf.cell(40, 8, " Status", 1, 0, "L", fill=True)
        pdf.cell(80, 8, " Remarks", 1, 1, "L", fill=True)

        pdf.set_font("helvetica", "", 8)
        ms_map = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'),
            ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'),
            ("Sub-deliveries Status", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'),
            ("Buffing/Finishing Status", 'buff_stat', 'buff_note'),
            ("Testing", 'testing', 'test_note'),
            ("QC/Dispatch Status", 'qc_stat', 'qc_note'),
            ("FAT", 'fat_stat', 'fat_note')
        ]
        for label, s_key, r_key in ms_map:
            pdf.cell(70, 7, f" {label}", 1)
            pdf.cell(40, 7, f" {log.get(s_key, 'In-Progress')}", 1)
            pdf.cell(80, 7, f" {log.get(r_key, '')}", 1, 1)
    return bytes(pdf.output())

# --- DATA HELPERS ---
@st.cache_data(ttl=5)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return sorted(c), sorted(j)
    except: return [], []

c_list, j_list = get_masters()

# --- APP LAYOUT ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        cust = col1.selectbox("Customer", c_list)
        job = col2.selectbox("Job Code", j_list)
        eq = col3.text_input("Equipment")

        col4, col5, col6 = st.columns(3)
        po_n = col4.text_input("PO No.")
        po_d = col5.date_input("PO Date")
        eng = col6.text_input("Engineer In-Charge")

        col7, col8 = st.columns(2)
        po_del = col7.date_input("Target Dispatch")
        rev_del = col8.date_input("Revised Dispatch")

        st.markdown("### 📊 Complete Milestone Status")
        
        # Defining specific status options for different milestones
        opts_std = ["In-Progress", "Submitted", "Approved", "Received", "Completed", "Ready", "N/A"]
        
        def entry_row(label, s_key, r_key):
            c1, c2 = st.columns([1, 2])
            s = c1.selectbox(label, opts_std, key=s_key)
            r = c2.text_input(f"Remarks for {label}", key=r_key)
            return s, r

        d_s, d_n = entry_row("Drawing Submission", "s1", "n1")
        da_s, da_n = entry_row("Drawing Approval", "s2", "n2")
        rm_s, rm_n = entry_row("RM Status", "s3", "n3")
        sd_s, sd_n = entry_row("Sub-deliveries", "s4", "n4")
        fb_s, fb_n = entry_row("Fabrication", "s5", "n5")
        bf_s, bf_n = entry_row("Buffing/Finishing", "s6", "n6")
        ts_s, ts_n = entry_row("Testing", "s7", "n7")
        qc_s, qc_n = entry_row("QC Status", "s8", "n8")
        fat_s, fat_n = entry_row("FAT Status", "s9", "n9")

        if st.form_submit_button("🚀 Sync All Fields to Cloud"):
            data_payload = {
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d),
                "engineer": eng, "po_delivery_date": str(po_del), "exp_dispatch_date": str(rev_del),
                "draw_sub": d_s, "draw_sub_note": d_n, "draw_app": da_s, "draw_app_note": da_n,
                "rm_status": rm_s, "rm_note": rm_n, "sub_del": sd_s, "sub_del_note": sd_n,
                "fab_status": fb_s, "remarks": fb_n, "buff_stat": bf_s, "buff_note": bf_n,
                "testing": ts_s, "test_note": ts_n, "qc_stat": qc_s, "qc_note": qc_n,
                "fat_stat": fat_s, "fat_note": fat_n
            }
            conn.table("progress_logs").insert(data_payload).execute()
            st.success("All 24 fields synchronized!"); st.rerun()

with t2:
    sel_cust = st.selectbox("Customer Filter", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    data = query.execute().data
    
    if data:
        if sel_cust != "All":
            pdf_bytes = create_bulk_pdf(sel_cust, data)
            st.download_button(f"📥 Download Official PDF", pdf_bytes, f"BG_{sel_cust}.pdf")
        
        for log in data:
            with st.expander(f"📦 {log.get('job_code')} - {log.get('equipment')}"):
                # FULL ARCHIVE VIEW
                st.table([
                    {"Milestone": "Drawing Submission", "Status": log.get('draw_sub'), "Note": log.get('draw_sub_note')},
                    {"Milestone": "Drawing Approval", "Status": log.get('draw_app'), "Note": log.get('draw_app_note')},
                    {"Milestone": "RM Status", "Status": log.get('rm_status'), "Note": log.get('rm_note')},
                    {"Milestone": "Sub-deliveries", "Status": log.get('sub_del'), "Note": log.get('sub_del_note')},
                    {"Milestone": "Fabrication", "Status": log.get('fab_status'), "Note": log.get('remarks')},
                    {"Milestone": "Buffing/Finishing", "Status": log.get('buff_stat'), "Note": log.get('buff_note')},
                    {"Milestone": "Testing", "Status": log.get('testing'), "Note": log.get('test_note')},
                    {"Milestone": "QC Status", "Status": log.get('qc_stat'), "Note": log.get('qc_note')},
                    {"Milestone": "FAT Status", "Status": log.get('fat_stat'), "Note": log.get('fat_note')}
                ])

with t3:
    if st.text_input("Admin PIN", type="password") == "1234":
        c1, c2 = st.columns(2)
        with c1:
            nc = st.text_input("New Customer")
            if st.button("Add Customer"): conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
        with c2:
            nj = st.text_input("New Job Code")
            if st.button("Add Job Code"): conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
