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
        try:
            if os.path.exists("logo.png"):
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

def create_pdf(log_data, photo_urls):
    pdf = ProgressPDF()
    pdf.add_page()
    
    # Header Info
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Customer: {log_data['customer']}", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, f"Job Code: {log_data['job_code']} | Equipment: {log_data['equipment']}", ln=True)
    pdf.cell(0, 8, f"Status: {log_data['fab_status']} | Target: {log_data['target_date']}", ln=True)
    pdf.ln(5)
    
    # Remarks
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, "Work Progress Remarks:", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, log_data['remarks'] if log_data['remarks'] else "No remarks.")
    pdf.ln(10)

    # Photos Logic
    if photo_urls:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "Shop Floor Media:", ln=True)
        
        y_start = pdf.get_y()
        for i, url in enumerate(photo_urls):
            try:
                # Fast timeout to prevent app hanging
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    img = BytesIO(resp.content)
                    
                    # 2-column layout
                    x = 10 if i % 2 == 0 else 110
                    if i > 0 and i % 2 == 0:
                        y_start += 75
                        if y_start > 230:
                            pdf.add_page()
                            y_start = 30
                    
                    pdf.image(img, x=x, y=y_start, w=90)
            except:
                continue
    
    # Return as clean bytes
    return bytes(pdf.output())

# --- DATA FETCHING ---
@st.cache_data(ttl=30) # Reduced TTL for faster refresh
def get_masters():
    try:
        c_data = conn.table("customer_master").select("name").execute().data
        j_data = conn.table("job_master").select("job_code").execute().data
        return [c['name'] for c in c_data], [j['job_code'] for j in j_data]
    except:
        return [], []

customer_list, job_list = get_masters()

st.title("🏗️ B&G Professional Dispatcher")

tab_entry, tab_archive, tab_masters = st.tabs(["📝 New Entry", "📂 Weekly Archive", "🛠️ Admin Masters"])

# --- TAB 1: NEW ENTRY ---
with tab_entry:
    with st.form("dispatch_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust = c1.selectbox("Customer", customer_list if customer_list else ["Add in Masters"])
        eng = c2.text_input("Engineer Name")
        eq = c3.text_input("Equipment")

        f1, f2, f3 = st.columns(3)
        job = f1.selectbox("Job Code", job_list if job_list else ["Add in Masters"])
        po = f2.text_input("PO Number")
        status = f2.selectbox("Status", ["In-Progress", "Fabrication", "Testing", "Dispatch Ready", "Completed"])
        target = f3.date_input("Target Date")
        remarks = st.text_area("Remarks")

        cam_pic = st.camera_input("Take Live Photo")
        gal_pics = st.file_uploader("Upload Gallery Photos", accept_multiple_files=True)
        
        if st.form_submit_button("🚀 Save & Upload"):
            if not eng or not eq:
                st.error("Please fill Engineer and Equipment.")
            else:
                try:
                    res = conn.table("progress_logs").insert({
                        "customer": cust, "engineer": eng, "equipment": eq,
                        "job_code": job, "po_no": po, "target_date": str(target),
                        "fab_status": status, "remarks": remarks
                    }).execute()
                    log_id = res.data[0]['id']

                    all_media = ([cam_pic] if cam_pic else []) + (gal_pics if gal_pics else [])
                    for i, pic in enumerate(all_media):
                        ts = datetime.now().strftime("%H%M%S")
                        fname = getattr(pic, 'name', f"cam_{ts}_{i}.jpg")
                        path = f"reports/{log_id}/{fname}"
                        conn.client.storage.from_("progress-photos").upload(
                            path=path, file=pic.getvalue(), file_options={"upsert": "true"}
                        )
                    st.success("Cloud Sync Complete!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- TAB 2: ARCHIVE ---
with tab_archive:
    st.subheader("📊 Customer Reviews")
    col_f1, col_f2 = st.columns(2)
    sel_cust = col_f1.selectbox("Customer", ["All"] + customer_list, key="cust_sel")
    show_weekly = col_f2.checkbox("Last 7 days only", value=True, key="week_sel")

    query = conn.table("progress_logs").select("*").order("created_at", desc=True)
    if sel_cust != "All": query = query.eq("customer", sel_cust)
    if show_weekly: query = query.gte("created_at", (datetime.now() - timedelta(days=7)).isoformat())
    
    data = query.execute().data
    
    if data:
        for log in data:
            with st.expander(f"📦 {log['equipment']} | {log['customer']} ({log['created_at'][:10]})"):
                t_col, p_col = st.columns([1,1])
                
                # Fetch Photos
                folder = f"reports/{log['id']}"
                files = conn.client.storage.from_("progress-photos").list(folder)
                photo_urls = [conn.client.storage.from_("progress-photos").get_public_url(f"{folder}/{f['name']}") for f in files]

                with t_col:
                    st.write(f"**Status:** :blue[{log['fab_status']}]")
                    st.info(f"**Remarks:** {log['remarks']}")
                    
                    # PDF GENERATION
                    if not photo_urls:
                        st.warning("⚠️ No photos - PDF disabled.")
                    else:
                        try:
                            # Pre-calculating bytes to ensure button has data
                            report_bytes = create_pdf(log, photo_urls)
                            st.download_button(
                                label="📥 Download PDF Report",
                                data=report_bytes,
                                file_name=f"Report_{log['job_code']}.pdf",
                                mime="application/pdf",
                                key=f"dl_btn_{log['id']}" # Unique key is vital
                            )
                        except Exception as e:
                            st.error(f"PDF Error: {e}")

                with p_col:
                    if photo_urls:
                        st.image(photo_urls, use_container_width=True)

# --- TAB 3: ADMIN ---
with tab_masters:
    if st.text_input("Admin PIN", type="password") == "1234":
        m1, m2 = st.columns(2)
        with m1:
            with st.form("add_c", clear_on_submit=True):
                n = st.text_input("New Customer")
                if st.form_submit_button("Add"):
                    conn.table("customer_master").insert({"name": n}).execute()
                    st.rerun()
        with m2:
            with st.form("add_j", clear_on_submit=True):
                n = st.text_input("New Job Code")
                if st.form_submit_button("Add"):
                    conn.table("job_master").insert({"job_code": n}).execute()
                    st.rerun()
