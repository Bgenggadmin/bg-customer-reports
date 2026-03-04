import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import requests
from io import BytesIO
import os

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Progress Hub", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATION CLASS ---
class ProgressPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font("helvetica", "B", 15)
        self.cell(80)
        self.cell(30, 10, "PROGRESS REPORT", 0, 0, "C")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | B&G Professional Dispatcher", 0, 0, "C")

# --- THE BULK GENERATOR (CRITICAL FIX) ---
def create_bulk_pdf(customer_name, logs_list):
    pdf = ProgressPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Weekly Summary: {customer_name}", ln=True, align='C')
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, f"Report Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(5)

    for log in logs_list:
        if pdf.get_y() > 200: pdf.add_page()

        # Job Header
        pdf.set_fill_color(235, 235, 235)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 9, f"JOB: {log['job_code']} | EQUIPMENT: {log['equipment']}", ln=True, fill=True)
        
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 7, f"Status: {log['fab_status']} | Target: {log['target_date']}", ln=True)
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(0, 6, f"Remarks: {log['remarks'] if log['remarks'] else 'N/A'}")
        pdf.ln(3)

        # PHOTO FETCHING LOGIC
        folder = f"reports/{log['id']}"
        try:
            files = conn.client.storage.from_("progress-photos").list(folder)
            if files:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Site/Shop Photos:", ln=True)
                
                img_w, img_h = 90, 60
                y_before_imgs = pdf.get_y()
                
                for i, f in enumerate(files[:4]): # Max 4 photos per job
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}")
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        img_data = BytesIO(resp.content)
                        
                        # Layout: 2 photos per row
                        col = i % 2
                        x_pos = 10 if col == 0 else 105
                        
                        if i == 2: # Move to second row of photos
                            y_before_imgs += (img_h + 2)
                        
                        # Page break check
                        if y_before_imgs > 230:
                            pdf.add_page()
                            y_before_imgs = 30
                        
                        pdf.image(img_data, x=x_pos, y=y_before_imgs, w=img_w, h=img_h)
                        
                        # Set Y after the last image added
                        pdf.set_y(y_before_imgs + img_h + 2)
        except: pass

        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    return bytes(pdf.output())

# --- DATA HELPERS ---
@st.cache_data(ttl=60)
def get_masters():
    try:
        c = [d['name'] for d in conn.table("customer_master").select("name").execute().data]
        j = [d['job_code'] for d in conn.table("job_master").select("job_code").execute().data]
        return c, j
    except: return [], []

customer_list, job_list = get_masters()

# --- APP UI ---
st.title("🏗️ B&G Professional Dispatcher")
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive & PDF", "🛠️ Masters"])

with tab1:
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", customer_list)
        eng = c2.text_input("Engineer")
        eq = c3.text_input("Equipment")
        
        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", job_list)
        stat = f2.selectbox("Status", ["Fabrication", "Testing", "Ready", "Completed"])
        targ = f3.date_input("Target Date")
        rem = st.text_area("Remarks")
        
        up_files = st.file_uploader("Upload Job Photos", accept_multiple_files=True)
        
        if st.form_submit_button("Submit Entry"):
            res = conn.table("progress_logs").insert({"customer": cust, "engineer": eng, "equipment": eq, "job_code": job, "fab_status": stat, "target_date": str(targ), "remarks": rem}).execute()
            log_id = res.data[0]['id']
            if up_files:
                for i, f in enumerate(up_files):
                    conn.client.storage.from_("progress-photos").upload(f"reports/{log_id}/img_{i}.jpg", f.getvalue())
            st.success("Entry Saved!"); st.rerun()

with tab2:
    st.subheader("📂 Customer-Wise Archive")
    s_col, w_col = st.columns(2)
    sel_c = s_col.selectbox("Select Customer for Report", ["All"] + customer_list)
    show_w = w_col.checkbox("Last 7 Days Only", value=True)

    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    if show_w: query = query.gte("created_at", (datetime.now() - timedelta(days=7)).isoformat())
    data = query.execute().data

    # --- THE BIG CUSTOMER-WISE BUTTON ---
    if sel_c != "All" and data:
        st.markdown(f"### 📋 Generating Report for {sel_c}")
        with st.spinner("Compiling images into Weekly PDF..."):
            bulk_pdf = create_bulk_pdf(sel_c, data)
            st.download_button(
                label=f"📥 DOWNLOAD FULL {sel_c.upper()} WEEKLY REPORT",
                data=bulk_pdf,
                file_name=f"BG_Report_{sel_c}_{datetime.now().strftime('%d_%m')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        st.divider()

    if data:
        for log in data:
            with st.expander(f"📦 {log['job_code']} - {log['equipment']} ({log['customer']})"):
                st.write(f"**Status:** {log['fab_status']} | **Remarks:** {log['remarks']}")
                # Individual view
                folder = f"reports/{log['id']}"
                f_list = conn.client.storage.from_("progress-photos").list(folder)
                if f_list:
                    urls = [conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}") for f in f_list]
                    st.image(urls, width=150)
    else: st.info("No data found for this selection.")

with tab3:
    if st.text_input("Admin PIN", type="password") == "1234":
        c_name = st.text_input("Add New Customer")
        if st.button("Save Customer"): conn.table("customer_master").insert({"name": c_name}).execute(); st.rerun()
