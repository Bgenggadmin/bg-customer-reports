import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import requests
from io import BytesIO
import os

# 1. INITIALIZE CONNECTION & CONFIG
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATION CLASS ---
class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try:
                self.image("logo.png", 10, 8, 30)
            except:
                pass
        self.set_font("helvetica", "B", 15)
        self.cell(80)
        self.cell(30, 10, "PROGRESS REPORT", 0, 0, "C")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Professional Dispatcher", 0, 0, "C")

# --- INDIVIDUAL PDF GENERATOR ---
def create_pdf(log_data, photo_urls):
    pdf = ProgressPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Customer: {log_data['customer']}", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, f"Job Code: {log_data['job_code']} | Equipment: {log_data['equipment']}", ln=True)
    pdf.cell(0, 8, f"Status: {log_data['fab_status']} | Target: {log_data['target_date']}", ln=True)
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Work Progress Remarks:", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, log_data['remarks'] if log_data['remarks'] else "N/A")
    pdf.ln(10)

    if photo_urls:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "Shop Floor Media:", ln=True)
        y_pos = pdf.get_y()
        for i, url in enumerate(photo_urls):
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    img = BytesIO(resp.content)
                    x = 10 if i % 2 == 0 else 110
                    if i > 0 and i % 2 == 0:
                        y_pos += 75
                        if y_pos > 220:
                            pdf.add_page()
                            y_pos = 30
                    pdf.image(img, x=x, y=y_pos, w=90)
            except: continue
    return bytes(pdf.output())

# --- BULK CUSTOMER PDF GENERATOR ---
def create_bulk_pdf(customer_name, logs_list):
    pdf = ProgressPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Weekly Summary: {customer_name}", ln=True, align='C')
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(10)

    for log in logs_list:
        if pdf.get_y() > 200: pdf.add_page()
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, f"Job: {log['job_code']} | Equipment: {log['equipment']}", ln=True, fill=True)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 7, f"Status: {log['fab_status']} | Target: {log['target_date']}", ln=True)
        pdf.multi_cell(0, 6, f"Remarks: {log['remarks']}")
        pdf.ln(5)
    return bytes(pdf.output())

# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except: return [], []

customer_list, job_list = get_masters()

# --- APP LAYOUT ---
st.title("🏗️ B&G Professional Dispatcher")
tab_entry, tab_archive, tab_masters = st.tabs(["📝 New Entry", "📂 Weekly Archive", "🛠️ Admin Masters"])

# --- TAB 1: NEW ENTRY ---
with tab_entry:
    with st.form("dispatch_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", customer_list)
        eng = c2.text_input("Engineer Name")
        eq = c3.text_input("Equipment")
        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", job_list)
        po = f2.text_input("PO Number")
        status = f2.selectbox("Status", ["In-Progress", "Fabrication", "Testing", "Dispatch Ready", "Completed"])
        target = f3.date_input("Target Date")
        remarks = st.text_area("Remarks")
        cam_pic = st.camera_input("Take Live Photo")
        gal_pics = st.file_uploader("Upload Gallery Photos", accept_multiple_files=True)
        
        if st.form_submit_button("🚀 Save & Upload"):
            if not eng or not eq: st.error("Missing Details.")
            else:
                res = conn.table("progress_logs").insert({"customer": cust, "engineer": eng, "equipment": eq, "job_code": job, "po_no": po, "target_date": str(target), "fab_status": status, "remarks": remarks}).execute()
                log_id = res.data[0]['id']
                all_media = ([cam_pic] if cam_pic else []) + (gal_pics if gal_pics else [])
                for i, pic in enumerate(all_media):
                    fname = f"img_{datetime.now().strftime('%H%M%S')}_{i}.jpg"
                    conn.client.storage.from_("progress-photos").upload(path=f"reports/{log_id}/{fname}", file=pic.getvalue())
                st.success("Cloud Sync Complete!"); st.rerun()

# --- TAB 2: ARCHIVE (WITH BULK PDF) ---
with tab_archive:
    st.subheader("📊 Customer Reviews")
    col_f1, col_f2 = st.columns(2)
    sel_cust = col_f1.selectbox("Filter by Customer", ["All"] + customer_list, key="cust_sel")
    show_weekly = col_f2.checkbox("Last 7 days only", value=True, key="week_sel")

    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    if show_weekly: query = query.gte("created_at", (datetime.now() - timedelta(days=7)).isoformat())
    data = query.execute().data

    # --- CUSTOMER-WISE DOWNLOAD ---
    if sel_cust != "All" and data:
        st.info(f"Generating bulk report for {len(data)} jobs for {sel_cust}...")
        try:
            bulk_pdf_data = create_bulk_pdf(sel_cust, data)
            st.download_button(label=f"📥 Download {sel_cust} Weekly Summary PDF", data=bulk_pdf_data, file_name=f"{sel_cust}_Weekly_Report.pdf", mime="application/pdf", key="bulk_pdf")
        except Exception as e: st.error(f"Bulk PDF failed: {e}")
        st.divider()

    if data:
        for log in data:
            with st.expander(f"📦 {log['equipment']} | {log['job_code']} ({log['created_at'][:10]})"):
                t_col, p_col = st.columns([1,1])
                folder = f"reports/{log['id']}"
                files = conn.client.storage.from_("progress-photos").list(folder)
                photo_urls = [conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}") for f in files]
                with t_col:
                    st.write(f"**Status:** {log['fab_status']}")
                    st.write(f"**Remarks:** {log['remarks']}")
                    if photo_urls:
                        pdf_b = create_pdf(log, photo_urls)
                        st.download_button("📥 Job PDF", data=pdf_b, file_name=f"Job_{log['job_code']}.pdf", key=f"btn_{log['id']}")
                with p_col:
                    if photo_urls: st.image(photo_urls, use_container_width=True)
    else: st.info("No logs found.")

# --- TAB 3: ADMIN ---
with tab_masters:
    if st.text_input("Admin PIN", type="password") == "1234":
        m1, m2 = st.columns(2)
        with m1:
            with st.form("add_c", clear_on_submit=True):
                n = st.text_input("New Customer")
                if st.form_submit_button("Add"): conn.table("customer_master").insert({"name": n}).execute(); st.rerun()
        with m2:
            with st.form("add_j", clear_on_submit=True):
                n = st.text_input("New Job Code")
                if st.form_submit_button("Add"): conn.table("job_master").insert({"job_code": n}).execute(); st.rerun()
