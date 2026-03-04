import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import os, requests
from io import BytesIO
from PIL import Image

# 1. INITIALIZE
st.set_page_config(page_title="B&G Hub Master", layout="wide", page_icon="🏗️")
conn = st.connection("supabase", type=SupabaseConnection)

# --- PDF GENERATOR (ID-LINKED STORAGE) ---
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
        pdf.cell(0, 8, f" JOB CODE: {log.get('job_code')} | DATE: {log.get('created_at')[:10]}", 1, 1, "C", fill=True)
        
        # --- HEADER FIELDS (8) ---
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

        # --- MILESTONE TABLE (9 ROWS / 18 FIELDS) ---
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
            pdf.cell(60, 6, label, 1); pdf.cell(35, 6, str(log.get(skey)), 1); pdf.cell(95, 6, str(log.get(nkey)), 1, 1)

        # --- FOOLPROOF PHOTO PULL (FROM UNIQUE ID FOLDER) ---
        entry_id = str(log.get('id'))
        try:
            res = conn.client.storage.from_("progress-photos").list(path=entry_id)
            if res:
                pdf.ln(5)
                x_start = 10
                y_pos = pdf.get_y()
                for idx, f_obj in enumerate(res[:4]):
                    url = conn.client.storage.from_("progress-photos").get_public_url(f"{entry_id}/{f_obj['name']}")
                    img_data = requests.get(url).content
                    img = Image.open(BytesIO(img_data)).convert('RGB')
                    img.thumbnail((300, 400))
                    buf = BytesIO()
                    img.save(buf, format='JPEG', quality=50) # Reduced for ~50KB
                    row, col = idx // 4, idx % 4
                    pdf.image(buf, x_start + (col * 48), y_pos, 40, 45) # Smaller passport size
        except: pass
    return bytes(pdf.output())

# --- APP TABS ---
c_list, j_list = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data]), sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])
t1, t2, t3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with t1:
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cust, job, eq = c1.selectbox("Customer", c_list), c2.selectbox("Job Code", j_list), c3.text_input("Equipment")
        c4, c5, c6 = st.columns(3)
        po_n, po_d, eng = c4.text_input("PO No."), c5.date_input("PO Date"), c6.text_input("Engineer")
        c7, c8 = st.columns(2)
        po_del, rev_del = c7.date_input("PO Delivery Date"), c8.date_input("Revised Dispatch Date")
        
        st.markdown("---")
        # SPECIFIC DROPDOWNS
        col_s1, col_n1 = st.columns([1,2])
        ds = col_s1.selectbox("Drawing Submission", ["In-Progress", "Submitted"])
        dn = col_n1.text_input("Remarks: Drawing Sub")
        
        col_s2, col_n2 = st.columns([1,2])
        da = col_s2.selectbox("Drawing Approval", ["Pending", "Approved"])
        dan = col_n2.text_input("Remarks: Drawing App")

        def milestone_row(label):
            ca, cb = st.columns([1,2])
            s = ca.selectbox(label, ["Pending", "In-Progress", "Hold", "Completed"])
            n = cb.text_input(f"Remarks: {label}")
            return s, n

        rm_s, rm_n = milestone_row("RM Status")
        sd_s, sd_n = milestone_row("Sub-deliveries")
        fb_s, fb_n = milestone_row("Fabrication Status")
        bf_s, bf_n = milestone_row("Buffing Status")
        ts_s, ts_n = milestone_row("Testing Status")
        qc_s, qc_n = milestone_row("QC Status")
        fa_s, fa_n = milestone_row("FAT Status")

        st.markdown("---")
        up_files = st.file_uploader("Upload Job Photos", accept_multiple_files=True)

        if st.form_submit_button("🚀 Sync Entry & Photos"):
            # 1. Insert Data to get Unique ID
            res = conn.table("progress_logs").insert({
                "customer": cust, "job_code": job, "equipment": eq, "po_no": po_n, "po_date": str(po_d), "engineer": eng,
                "po_delivery_date": str(po_del), "exp_dispatch_date": str(rev_del),
                "draw_sub": ds, "draw_sub_note": dn, "draw_app": da, "draw_app_note": dan,
                "rm_status": rm_s, "rm_note": rm_n, "sub_del": sd_s, "sub_del_note": sd_n,
                "fab_status": fb_s, "remarks": fb_n, "buff_stat": bf_s, "buff_note": bf_n,
                "testing": ts_s, "test_note": ts_n, "qc_stat": qc_s, "qc_note": qc_n, "fat_stat": fa_s, "fat_note": fa_n
            }).execute()
            
            # 2. Upload to ID Folder
            if up_files and res.data:
                new_id = str(res.data[0]['id'])
                for f in up_files:
                    conn.client.storage.from_("progress-photos").upload(path=f"{new_id}/{f.name}", file=f.getvalue())
            st.success("Entry Synchronized!"); st.rerun()

with t2:
    sel_c = st.selectbox("Select Customer to View/Download", ["All"] + c_list)
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if sel_c != "All": query = query.eq("customer", sel_c)
    data = query.execute().data
    
    if data:
        if sel_c != "All":
            st.download_button(f"📥 Download {sel_c} PDF Report", create_report_pdf(data), f"BG_{sel_c}.pdf")
        
        for log in data:
            c_head, c_btn = st.columns([5,1])
            c_head.write(f"**ID: {log['id']} | Job: {log['job_code']}** - {log['equipment']}")
            if c_btn.button("🗑️", key=f"del_{log['id']}"):
                conn.table("progress_logs").delete().eq("id", log['id']).execute()
                # Also delete folder if needed, but simple entry delete works for now
                st.rerun()
            
            with st.expander("Show Detailed Milestone Table & Photos"):
                # Photos from ID Folder
                res_f = conn.client.storage.from_("progress-photos").list(path=str(log['id']))
                if res_f:
                    pcols = st.columns(5)
                    for i, f in enumerate(res_f):
                        u = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}/{f['name']}")
                        pcols[i % 5].image(u, use_container_width=True)
                
                # Show all 24 fields in a grid
                st.write(log)
