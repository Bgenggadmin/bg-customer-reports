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

# --- BULK CUSTOMER PDF GENERATOR (UPDATED WITH IMAGES) ---
def create_bulk_pdf(customer_name, logs_list):
    pdf = ProgressPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Weekly Summary: {customer_name}", ln=True, align='C')
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(5)

    for log in logs_list:
        # Start a new page if we are near the bottom
        if pdf.get_y() > 220:
            pdf.add_page()

        # Job Header Box
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, f"Job: {log['job_code']} | Equipment: {log['equipment']}", ln=True, fill=True)
        
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 7, f"Status: {log['fab_status']} | Target: {log['target_date']}", ln=True)
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(0, 6, f"Remarks: {log['remarks'] if log['remarks'] else 'No remarks recorded.'}")
        pdf.ln(2)

        # FETCH & ADD PHOTOS FOR THIS JOB
        folder = f"reports/{log['id']}"
        try:
            files = conn.client.storage.from_("progress-photos").list(folder)
            if files:
                pdf.set_font("helvetica", "B", 9)
                pdf.cell(0, 6, "Progress Photos:", ln=True)
                
                # Grid coordinates
                x_start = 10
                img_width = 85
                img_height = 60 # Standardized height
                
                for i, f in enumerate(files):
                    # Limit to 4 photos per job to keep report size manageable
                    if i >= 4: break 
                    
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}")
                    try:
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            img = BytesIO(resp.content)
                            
                            # Determine X and Y
                            # Row 1: i=0,1 | Row 2: i=2,3
                            col = i % 2
                            x = x_start if col == 0 else 105
                            
                            # If we just finished a row (i=2), move Y down
                            if i > 0 and col == 0:
                                pdf.ln(img_height + 2)
                            
                            curr_y = pdf.get_y()
                            
                            # Page break check for images
                            if curr_y > 230:
                                pdf.add_page()
                                curr_y = 30
                                pdf.set_y(curr_y)
                            
                            pdf.image(img, x=x, y=curr_y, w=img_width, h=img_height)
                            
                            # If it's the last image or last in row, adjust Y for next text block
                            if i == len(files)-1 or i == 3:
                                pdf.set_y(curr_y + img_height + 5)
                    except:
                        continue
        except:
            pass # Skip if storage error

        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Separator line
        pdf.ln(5)

    return bytes(pdf.output())

# --- REST OF THE CODE (INDIVIDUAL PDF, TABS, MASTER) ---
def create_pdf(log_data, photo_urls):
    pdf = ProgressPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Customer: {log_data['customer']}", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, f"Job Code: {log_data['job_code']} | Equipment: {log_data['equipment']}", ln=True)
    pdf.cell(0, 8, f"Status: {log_data['fab_status']} | Target: {log_data['target_date']}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Remarks: {log_data['remarks']}")
    pdf.ln(5)
    if photo_urls:
        y_pos = pdf.get_y()
        for i, url in enumerate(photo_urls):
            try:
                resp = requests.get(url, timeout=5)
                img = BytesIO(resp.content)
                x = 10 if i % 2 == 0 else 110
                if i > 0 and i % 2 == 0: y_pos += 75
                pdf.image(img, x=x, y=y_pos, w=90)
            except: continue
    return bytes(pdf.output())

@st.cache_data(ttl=60)
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except: return [], []

customer_list, job_list = get_masters()
st.title("🏗️ B&G Professional Dispatcher")
tab_entry, tab_archive, tab_masters = st.tabs(["📝 New Entry", "📂 Weekly Archive", "🛠️ Admin Masters"])

# --- TAB 1: NEW ENTRY (Same as before) ---
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
        gal_pics = st.file_uploader("Upload Photos", accept_multiple_files=True)
        if st.form_submit_button("🚀 Save & Upload"):
            res = conn.table("progress_logs").insert({"customer": cust, "engineer": eng, "equipment": eq, "job_code": job, "po_no": po, "target_date": str(target), "fab_status": status, "remarks": remarks}).execute()
            log_id = res.data[0]['id']
            all_m = ([cam_pic] if cam_pic else []) + (gal_pics if gal_pics else [])
            for i, p in enumerate(all_m):
                conn.client.storage.from_("progress-photos").upload(path=f"reports/{log_id}/img_{i}.jpg", file=p.getvalue())
            st.success("Synced!"); st.rerun()

# --- TAB 2: ARCHIVE ---
with tab_archive:
    col_f1, col_f2 = st.columns(2)
    sel_cust = col_f1.selectbox("Customer", ["All"] + customer_list)
    show_weekly = col_f2.checkbox("Last 7 days", value=True)
    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    if show_weekly: query = query.gte("created_at", (datetime.now() - timedelta(days=7)).isoformat())
    data = query.execute().data

    if sel_cust != "All" and data:
        st.write(f"### 📋 {sel_cust} Weekly Report")
        with st.spinner("Building Report with Images..."):
            bulk_pdf_data = create_bulk_pdf(sel_cust, data)
            st.download_button(f"📥 Download Full {sel_cust} Report", data=bulk_pdf_data, file_name=f"{sel_cust}_Report.pdf", mime="application/pdf")
        st.divider()

    if data:
        for log in data:
            with st.expander(f"📦 {log['equipment']} | {log['job_code']}"):
                t, p = st.columns([1,1])
                folder = f"reports/{log['id']}"
                files = conn.client.storage.from_("progress-photos").list(folder)
                photo_urls = [conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}") for f in files]
                with t:
                    st.write(f"**Status:** {log['fab_status']}")
                    if photo_urls:
                        st.download_button("📥 Job PDF", create_pdf(log, photo_urls), f"{log['job_code']}.pdf", key=f"j_{log['id']}")
                with p:
                    if photo_urls: st.image(photo_urls, width=150)

# --- TAB 3: ADMIN (Same as before) ---
with tab_masters:
    if st.text_input("PIN", type="password") == "1234":
        n_c = st.text_input("New Customer")
        if st.button("Add Customer"): conn.table("customer_master").insert({"name": n_c}).execute(); st.rerun()
