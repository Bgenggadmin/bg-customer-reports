import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime, timedelta, timezone
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE & IST TIME LOGIC
st.set_page_config(page_title="B&G Hub Master", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# Define IST (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST).strftime("%d-%m-%Y %H:%M")

# --- PDF GENERATOR (IST & PHOTO SYNC) ---
class ProgressPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "B&G ENGINEERING INDUSTRIES - PROGRESS REPORT", 0, 1, "R")
        self.line(10, 22, 200, 22)
        self.ln(5)

def create_report_pdf(logs_list):
    pdf = ProgressPDF()
    for log in logs_list:
        pdf.add_page()
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        # Using IST Date in Header
        pdf.cell(0, 8, f" JOB CODE: {log.get('job_code')} | REPORT GEN: {now_ist}", 1, 1, "C", fill=True)
        
        # --- HEADER (8 FIELDS - FORMATTED DATES) ---
        pdf.set_font("helvetica", "B", 8)
        h_data = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Engineer", log.get('engineer')), ("PO No.", log.get('po_no')),
            ("PO Date", log.get('po_date')), ("PO Delivery", log.get('po_delivery_date')),
            ("Revised Disp", log.get('exp_dispatch_date')), ("Entry ID", str(log.get('id')))
        ]
        for i in range(0, len(h_data), 2):
            pdf.cell(30, 7, h_data[i][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_data[i][1]), 1, 0)
            pdf.cell(30, 7, h_data[i+1][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h_data[i+1][1]), 1, 1)

        # --- MILESTONES (18 FIELDS) ---
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone", 1, 0, 'L', True); pdf.cell(35, 7, " Status", 1, 0, 'L', True); pdf.cell(95, 7, " Remarks", 1, 1, 'L', True)
        pdf.set_font("helvetica", "", 8)
        ms = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), ("QC Status", 'qc_stat', 'qc_note'), ("FAT Status", 'fat_stat', 'fat_note')
        ]
        for label, skey, nkey in ms:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)

        # --- PHOTO SYNC IN PDF ---
        eid = str(log.get('id'))
        try:
            res = conn.client.storage.from_("progress-photos").list(path=eid)
            if res:
                pdf.ln(5); y_p = pdf.get_y()
                for idx, f in enumerate(res[:4]):
                    u = conn.client.storage.from_("progress-photos").get_public_url(f"{eid}/{f['name']}")
                    img_data = requests.get(u).content
                    img = Image.open(BytesIO(img_data)).convert('RGB')
                    img.thumbnail((300, 400)); buf = BytesIO(); img.save(buf, format='JPEG', quality=50)
                    pdf.image(buf, 10 + ((idx % 4) * 48), y_p, 40, 45)
        except: pass
    return bytes(pdf.output())

# --- DATA FETCH ---
customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])

t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

# --- TAB 1: NEW ENTRY (IST DATES & UPSERT FIX) ---
with t1:
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust, job, eq = c1.selectbox("Customer", customers), c2.selectbox("Job", jobs), c3.text_input("Equipment")
        
        c4, c5, c6 = st.columns(3)
        po_n = c4.text_input("PO No.")
        po_d = c5.date_input("PO Date", value=datetime.now(IST)) # Default IST
        eng = c6.text_input("Engineer")
        
        c7, c8 = st.columns(2)
        p_del = c7.date_input("PO Delivery Date")
        r_del = c8.date_input("Revised Dispatch Date")
        
        # 18 Milestone Fields
        def m_row(label, sid, nid, opts=["Pending", "In-Progress", "Hold", "Completed"]):
            ca, cb = st.columns([1,2]); return ca.selectbox(label, opts, key=sid), cb.text_input(f"Remarks: {label}", key=nid)

        s1, n1 = m_row("Drawing Submission", "s1", "n1", ["In-Progress", "Submitted"])
        s2, n2 = m_row("Drawing Approval", "s2", "n2", ["Pending", "Approved"])
        s3, n3 = m_row("RM Status", "s3", "n3")
        s4, n4 = m_row("Sub-deliveries", "s4", "n4")
        s5, n5 = m_row("Fabrication Status", "s5", "n5")
        s6, n6 = m_row("Buffing Status", "s6", "n6")
        s7, n7 = m_row("Testing Status", "s7", "n7")
        s8, n8 = m_row("QC Status", "s8", "n8")
        s9, n9 = m_row("FAT Status", "s9", "n9")

        f_photos = st.file_uploader("Upload Photos (Multi-Select)", accept_multiple_files=True)

        if st.form_submit_button("🚀 Final Sync"):
            # INSERT with IST-formatted strings
            res = conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, 
                "po_date": po_d.strftime("%d-%m-%Y"), "engineer": eng,
                "po_delivery_date": p_del.strftime("%d-%m-%Y"), "exp_dispatch_date": r_del.strftime("%d-%m-%Y"),
                "draw_sub": s1, "draw_sub_note": n1, "draw_app": s2, "draw_app_note": n2,
                "rm_status": s3, "rm_note": n3, "sub_del": s4, "sub_del_note": n4,
                "fab_status": s5, "remarks": n5, "buff_stat": s6, "buff_note": n6,
                "testing": s7, "test_note": n7, "qc_stat": s8, "qc_note": n8, "fat_stat": s9, "fat_note": n9
            }).execute()
            
            if f_photos and res.data:
                new_id = str(res.data[0]['id'])
                for p in f_photos:
                    conn.client.storage.from_("progress-photos").upload(
                        path=f"{new_id}/{p.name}", file=p.getvalue(), file_options={"upsert": "true"}
                    )
            st.success(f"Successfully Synced at {now_ist}!"); st.rerun()

# --- TAB 2: ARCHIVE (PHOTO SYNC & PDF DOWNLOAD) ---
with t2:
    sel_c = st.selectbox("Select Customer", ["All"] + customers)
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    data = query.execute().data
    
    if data:
        if sel_c != "All":
            st.download_button(f"📥 Download {sel_c} PDF Report", create_report_pdf(data), f"{sel_c}_Report.pdf")
        
        for log in data:
            c_h, c_d = st.columns([6,1])
            c_h.write(f"**ID: {log['id']} | Job: {log['job_code']}** - {log['customer']}")
            if c_d.button("🗑️", key=f"del_{log['id']}"):
                try:
                    flist = conn.client.storage.from_("progress-photos").list(path=str(log['id']))
                    if flist: conn.client.storage.from_("progress-photos").remove([f"{log['id']}/{f['name']}" for f in flist])
                except: pass
                conn.table("progress_logs").delete().eq("id", log['id']).execute(); st.rerun()
            
            with st.expander("Show Details & Photos"):
                # PHOTO FETCH LOGIC
                eid = str(log['id'])
                plist = conn.client.storage.from_("progress-photos").list(path=eid)
                if plist:
                    pcols = st.columns(5)
                    for i, p in enumerate(plist):
                        u = conn.client.storage.from_("progress-photos").get_public_url(f"{eid}/{p['name']}")
                        pcols[i % 5].image(u, use_container_width=True)
                else:
                    st.info("No photos found for this entry.")
                st.table({k: [v] for k, v in log.items() if v})

# --- TAB 3: MASTERS ---
with t3:
    st.subheader("🛠️ Master Lists")
    ma, mb = st.columns(2)
    with ma:
        nc = st.text_input("New Customer")
        if st.button("Add Customer"): conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
    with mb:
        nj = st.text_input("New Job Code")
        if st.button("Add Job Code"): conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
