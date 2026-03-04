import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os, requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE CONNECTION
st.set_page_config(page_title="B&G Hub Final", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- A. REFRESH DATA (NO CACHE) ---
try:
    c_res = conn.table("customer_master").select("*").execute()
    j_res = conn.table("job_master").select("*").execute()
    customers = sorted([d['name'] for d in c_res.data]) if c_res.data else []
    jobs = sorted([d['job_code'] for d in j_res.data]) if j_res.data else []
except:
    customers, jobs = [], []

# --- B. PDF GENERATOR ---
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
        pdf.cell(0, 8, f" JOB CODE: {log.get('job_code')} | REPORT DATE: {datetime.now().strftime('%d-%m-%Y')}", 1, 1, "C", fill=True)
        
        # Header (8 Fields)
        pdf.set_font("helvetica", "B", 8)
        h = [
            ("Customer", log.get('customer')), ("Equipment", log.get('equipment')),
            ("Engineer", log.get('engineer')), ("PO No.", log.get('po_no')),
            ("PO Date", log.get('po_date')), ("PO Delivery", log.get('po_delivery_date')),
            ("Revised Disp", log.get('exp_dispatch_date')), ("Entry ID", str(log.get('id')))
        ]
        for i in range(0, len(h), 2):
            pdf.cell(30, 7, h[i][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h[i][1]), 1, 0)
            pdf.cell(30, 7, h[i+1][0], 1, 0, 'L', True); pdf.cell(65, 7, str(h[i+1][1]), 1, 1)

        # Milestone Table (9 Rows / 18 Fields)
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(60, 7, " Milestone", 1, 0, 'L', True); pdf.cell(35, 7, " Status", 1, 0, 'L', True); pdf.cell(95, 7, " Remarks", 1, 1, 'L', True)
        pdf.set_font("helvetica", "", 8)
        mapping = [
            ("Drawing Submission", 'draw_sub', 'draw_sub_note'), ("Drawing Approval", 'draw_app', 'draw_app_note'),
            ("RM Status", 'rm_status', 'rm_note'), ("Sub-deliveries", 'sub_del', 'sub_del_note'),
            ("Fabrication Status", 'fab_status', 'remarks'), ("Buffing Status", 'buff_stat', 'buff_note'),
            ("Testing Status", 'testing', 'test_note'), ("QC Status", 'qc_stat', 'qc_note'), ("FAT Status", 'fat_stat', 'fat_note')
        ]
        for label, skey, nkey in mapping:
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey, '-')), 1); pdf.cell(95, 6, str(log.get(nkey, '-')), 1, 1)

        # Photos (ID Folder Logic)
        e_id = str(log.get('id'))
        try:
            res_p = conn.client.storage.from_("progress-photos").list(path=e_id)
            if res_p:
                pdf.ln(5); y_p = pdf.get_y()
                for idx, f_o in enumerate(res_p[:4]):
                    u = conn.client.storage.from_("progress-photos").get_public_url(f"{e_id}/{f_o['name']}")
                    img_d = requests.get(u).content
                    img = Image.open(BytesIO(img_d)).convert('RGB')
                    img.thumbnail((300, 400))
                    buf = BytesIO()
                    img.save(buf, format='JPEG', quality=60)
                    pdf.image(buf, 10 + ((idx % 4) * 48), y_p, 40, 45)
        except: pass
    return bytes(pdf.output())

# --- C. APP TABS ---
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("final_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cust = c1.selectbox("Customer", [""] + customers)
        f_job = c2.selectbox("Job Code", [""] + jobs)
        f_eq = c3.text_input("Equipment")
        
        c4, c5, c6 = st.columns(3)
        f_po_n, f_po_d, f_eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        c7, c8 = st.columns(2)
        f_p_del, f_r_del = c7.date_input("PO Delivery"), c8.date_input("Revised Dispatch")

        st.markdown("---")
        # 18 Milestone Fields
        r1a, r1b = st.columns([1,2])
        v1s = r1a.selectbox("Drawing Submission", ["In-Progress", "Submitted"])
        v1n = r1b.text_input("Remarks: Drawing Sub")
        
        r2a, r2b = st.columns([1,2])
        v2s = r2a.selectbox("Drawing Approval", ["Pending", "Approved"])
        v2n = r2b.text_input("Remarks: Drawing App")

        def m_row(label, kid):
            ca, cb = st.columns([1,2])
            s = ca.selectbox(label, ["Pending", "In-Progress", "Hold", "Completed"], key=f"s{kid}")
            n = cb.text_input(f"Remarks: {label}", key=f"n{kid}")
            return s, n

        v3s, v3n = m_row("RM Status", "3")
        v4s, v4n = m_row("Sub-deliveries", "4")
        v5s, v5n = m_row("Fabrication Status", "5")
        v6s, v6n = m_row("Buffing Status", "6")
        v7s, v7n = m_row("Testing Status", "7")
        v8s, v8n = m_row("QC Status", "8")
        v9s, v9n = m_row("FAT Status", "9")

        f_imgs = st.file_uploader("Upload Photos", accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync Entry"):
            if not f_cust or not f_job:
                st.error("Select Customer & Job Code")
            else:
                ins = conn.table("progress_logs").insert({
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq, "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                    "draw_sub": v1s, "draw_sub_note": v1n, "draw_app": v2s, "draw_app_note": v2n,
                    "rm_status": v3s, "rm_note": v3n, "sub_del": v4s, "sub_del_note": v4n,
                    "fab_status": v5s, "remarks": v5n, "buff_stat": v6s, "buff_note": v6n,
                    "testing": v7s, "test_note": v7n, "qc_stat": v8s, "qc_note": v8n, "fat_stat": v9s, "fat_note": v9n
                }).execute()
                
                if ins.data:
                    curr_id = str(ins.data[0]['id'])
                    if f_imgs:
                        for p in f_imgs:
                            conn.client.storage.from_("progress-photos").upload(
                                path=f"{curr_id}/{p.name}", file=p.getvalue(), file_options={"upsert": "true"}
                            )
                    st.success(f"Saved ID: {curr_id}"); st.rerun()

with t2:
    sel_c = st.selectbox("Filter Customer", ["All"] + customers)
    q = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": q = q.eq("customer", sel_c)
    data = q.execute().data
    
    if data:
        if sel_c != "All":
            st.download_button(f"📥 Download {sel_c} PDF", create_report_pdf(data), f"{sel_c}_Report.pdf")
        
        for entry in data:
            col1, col2 = st.columns([6,1])
            col1.write(f"**ID: {entry['id']} | {entry['job_code']}** - {entry['customer']}")
            if col2.button("🗑️", key=f"d{entry['id']}"):
                try:
                    fs = conn.client.storage.from_("progress-photos").list(path=str(entry['id']))
                    if fs: conn.client.storage.from_("progress-photos").remove([f"{entry['id']}/{f['name']}" for f in fs])
                except: pass
                conn.table("progress_logs").delete().eq("id", entry['id']).execute(); st.rerun()
            
            with st.expander("Details & Photos"):
                ps = conn.client.storage.from_("progress-photos").list(path=str(entry['id']))
                if ps:
                    pcols = st.columns(6)
                    for i, p in enumerate(ps):
                        url = conn.client.storage.from_("progress-photos").get_public_url(f"{entry['id']}/{p['name']}")
                        pcols[i % 6].image(url)
                st.table({k: [v] for k, v in entry.items()})

with t3:
    st.subheader("Manage Masters")
    mc1, mc2 = st.columns(2)
    with mc1:
        nc = st.text_input("New Customer")
        if st.button("Add Cust") and nc:
            conn.table("customer_master").insert({"name": nc}).execute(); st.rerun()
        for c in c_res.data:
            r = st.columns([3,1])
            r[0].write(c['name'])
            if r[1].button("❌", key=f"cc{c['id']}"):
                conn.table("customer_master").delete().eq("id", c['id']).execute(); st.rerun()
    with mc2:
        nj = st.text_input("New Job Code")
        if st.button("Add Job") and nj:
            conn.table("job_master").insert({"job_code": nj}).execute(); st.rerun()
        for j in j_res.data:
            r = st.columns([3,1])
            r[0].write(j['job_code'])
            if r[1].button("❌", key=f"jj{j['id']}"):
                conn.table("job_master").delete().eq("id", j['id']).execute(); st.rerun()
