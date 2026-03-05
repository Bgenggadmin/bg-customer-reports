import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. SETUP
st.set_page_config(page_title="B&G Hub 2.0", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# 2. THE MASTER MAPPING
HEADER_FIELDS = ["customer", "job_code", "equipment", "po_no", "po_date", "engineer", "po_delivery_date", "exp_dispatch_date"]

MILESTONE_MAP = [
    ("Drawing Submission", "draw_sub", "draw_sub_note"),
    ("Drawing Approval", "draw_app", "draw_app_note"),
    ("RM Status", "rm_status", "rm_note"),
    ("Sub-deliveries", "sub_del", "sub_del_note"),
    ("Fabrication Status", "fab_status", "remarks"),
    ("Buffing Status", "buff_stat", "buff_note"),
    ("Testing Status", "testing", "test_note"),
    ("Dispatch Status", "qc_stat", "qc_note"),
    ("FAT Status", "fat_stat", "fat_note")
]

# --- DATA FETCHING ---
customers = sorted([d['name'] for d in conn.table("customer_master").select("name").execute().data])
jobs = sorted([d['job_code'] for d in conn.table("job_master").select("job_code").execute().data])

# --- PDF ENGINE ---
def generate_pdf(logs):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for log in logs:
        pdf.add_page()
        
        # 1. DRAW BLUE STRIP FIRST (Background layer)
        pdf.set_fill_color(0, 51, 102) # Dark Blue
        pdf.rect(0, 0, 210, 35, 'F')
        
        # 2. DRAW LOGO SECOND (Foreground layer)
        # We put this AFTER the rect so it stays on top
        try:
            logo_data = conn.client.storage.from_("progress-photos").download("logo.png")
            if logo_data:
                # x=10, y=5. Increasing height to 25 to make it visible
                pdf.image(BytesIO(logo_data), x=10, y=5, h=25)
        except Exception as e:
            # If it fails, we keep going
            pass

        # 3. HEADER TEXT
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 18)
        # Shift X to 50 so it doesn't overlap the logo on the left
        pdf.set_xy(50, 10) 
        pdf.cell(150, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "L")
        
        pdf.set_font("Arial", "I", 10)
        pdf.set_x(50)
        pdf.cell(150, 5, "PROJECT PROGRESS REPORT", 0, 1, "L")
        
        # Reset colors for the body text
        pdf.set_text_color(0, 0, 0)
        pdf.ln(20) # Space after the blue header

        # --- Sub-Header (Job Code) ---
        pdf.set_font("Arial", "B", 10)
        pdf.set_xy(10, 38)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        pdf.ln(3)

        # --- Header Grid Fields ---
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1, f2 = HEADER_FIELDS[i], HEADER_FIELDS[i+1]
            pdf.cell(30, 7, f" {f1.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f1,''))}", 1, 0, 'L')
            pdf.cell(30, 7, f" {f2.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f2,''))}", 1, 1, 'L')

        pdf.ln(5)

        # --- Milestone Table ---
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 8, " Milestone Item", 1, 0, 'L', True)
        pdf.cell(35, 8, " Status", 1, 0, 'C', True)
        pdf.cell(95, 8, " Remarks", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
        for label, s_key, n_key in MILESTONE_MAP:
            status = str(log.get(s_key, 'Pending'))
            if status in ["Completed", "Approved", "Submitted"]:
                pdf.set_fill_color(144, 238, 144)
            elif status in ["In-Progress", "Hold", "Ordered", "Received", "Planning", "Scheduled"]:
                pdf.set_fill_color(255, 255, 204)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {status}", 1, 0, 'C', True)
            pdf.cell(95, 7, f" {str(log.get(n_key,'-'))}", 1, 1)

        # --- Progress Photo ---
        try:
            img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((350, 350))
                buf = BytesIO(); img.save(buf, format="JPEG")
                pdf.image(buf, x=75, y=pdf.get_y()+10, w=60)
        except: 
            pass

    return bytes(pdf.output())
        # --- PHOTO LOGIC ---
        try:
            img_url = conn.client.storage.from_("progress-photos").get_public_url(f"{log['id']}.jpg")
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(BytesIO(img_res.content)).convert('RGB')
                img.thumbnail((350, 350))
                buf = BytesIO(); img.save(buf, format="JPEG")
                # Position photo below the table
                pdf.image(buf, x=75, y=pdf.get_y()+10, w=60)
        except: 
            pass

    return bytes(pdf.output())

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 New Entry", "📂 Archive", "🛠️ Masters"])

with tab1:
    st.subheader("📋 Select Project")
    
    # 1. Job selection MUST be outside the form to trigger the database lookup
    f_job = st.selectbox("Job Code", [""] + jobs, key="job_lookup")

    # 2. Fetch the LATEST data for this specific Job Code
    last_data = {}
    if f_job:
        res = conn.table("progress_logs").select("*").eq("job_code", f_job).order("id", desc=True).limit(1).execute()
        last_data = res.data[0] if res.data else {}

    # 3. Form starts here
    with st.form("main_entry_form", clear_on_submit=True):
        st.subheader("📋 Project Details")
        
        c1, c2, c3 = st.columns(3)
        # Pre-fill Customer and Equipment based on last_data
        f_cust = c1.selectbox("Customer", [""] + customers, 
                             index=customers.index(last_data['customer']) + 1 if last_data.get('customer') in customers else 0)
        
        # Display selected job as info
        c2.text_input("Selected Job", value=f_job, disabled=True)
        f_eq = c3.text_input("Equipment Name", value=last_data.get('equipment', ""))
        
        c4, c5, c6 = st.columns(3)
        f_po_n = c4.text_input("PO Number", value=last_data.get('po_no', ""))
        
        # Date Logic: Fallback to today if no previous record
        prev_po_date = datetime.now()
        if last_data.get('po_date'):
            prev_po_date = datetime.strptime(last_data['po_date'], "%Y-%m-%d")
            
        f_po_d = c5.date_input("PO Date", value=prev_po_date)
        f_eng = c6.text_input("Responsible Engineer", value=last_data.get('engineer', ""))
        
        c7, c8 = st.columns(2)
        f_p_del = c7.date_input("PO Delivery Date", value=datetime.strptime(last_data['po_delivery_date'], "%Y-%m-%d") if last_data.get('po_delivery_date') else datetime.now())
        f_r_del = c8.date_input("Revised Dispatch Date", value=datetime.strptime(last_data['exp_dispatch_date'], "%Y-%m-%d") if last_data.get('exp_dispatch_date') else datetime.now())

        st.divider()
        st.subheader("📊 Milestone Tracking")
        m_responses = {}
        
        for label, skey, nkey in MILESTONE_MAP:
            col_stat, col_note = st.columns([1, 2])
            
            # --- DEFINE OPTIONS PER LABEL ---
            if label == "Drawing Submission": opts = ["Pending", "In-Progress", "Submitted"]
            elif label == "Drawing Approval": opts = ["Pending", "In-Progress", "Approved"]
            elif label == "RM Status": opts = ["Pending", "Ordered", "Received", "Hold"]
            elif label == "Sub-deliveries": opts = ["Pending", "In-Progress", "Completed"]
            elif label == "Fabrication Status": opts = ["Planning", "In-Progress", "Hold", "Completed"]
            elif label == "Buffing Status": opts = ["Planning", "In-Progress", "Completed"]
            elif label == "Testing Status": opts = ["Scheduled", "In-Progress", "Completed"]
            elif label == "Dispatch Status": opts = ["Pending", "Scheduled", "In-Progress", "Completed"]
            elif label == "FAT Status": opts = ["Scheduled", "In-Progress", "Completed"]
            else: opts = ["Pending", "Scheduled", "Hold","In-Progress", "Completed"]

            # --- FORWARD-ONLY GUARD LOGIC ---
            prev_status = last_data.get(skey, "Pending")
            
            # If the status was already "Submitted" or "Approved", don't allow going back to "In-Progress"
            if prev_status in ["Submitted", "Approved", "Completed", "Received"]:
                # Filter out the "lower" statuses
                opts = [opt for opt in opts if opt not in ["Pending", "In-Progress", "Planning", "Ordered"]]
                # Ensure the previous status remains in the list as the default
                if prev_status not in opts: opts.insert(0, prev_status)

            # Find index of previous status to set as default
            default_idx = opts.index(prev_status) if prev_status in opts else 0
            
            m_responses[skey] = col_stat.selectbox(label, opts, index=default_idx, key=f"form_{skey}")
            # Pre-fill previous remarks so the team doesn't have to re-type
            m_responses[nkey] = col_note.text_input(f"Remarks for {label}", value=last_data.get(nkey, ""), key=f"form_{nkey}")

        st.divider()
        st.subheader("📸 Progress Capture")
        cam_photo = st.camera_input("Take Progress Photo")

        if st.form_submit_button("🚀 SUBMIT UPDATE", use_container_width=True):
            if not f_cust or not f_job:
                st.error("Select a Job Code and Customer first!")
            else:
                # Payload remains the same as your existing logic
                entry_payload = {
                    "customer": f_cust, "job_code": f_job, "equipment": f_eq,
                    "po_no": f_po_n, "po_date": str(f_po_d), "engineer": f_eng,
                    "po_delivery_date": str(f_p_del), "exp_dispatch_date": str(f_r_del),
                    **m_responses
                }
                # ... [Keep your existing try/except insert logic here] ...
with tab2:
    st.subheader("📂 Report Archive")
    
    # 1. Row for Filters
    filter_c1, filter_c2, filter_c3 = st.columns(3)
    
    cust_list = ["All Customers"] + customers
    selected_cust = filter_c1.selectbox("🔍 Filter by Customer", cust_list)
    
    report_type = filter_c2.selectbox("📅 Report Duration", 
                                    ["All Time", "Current Week", "Current Month", "Custom Range"])

    # 2. Date Input for Custom Range
    start_date, end_date = None, None
    if report_type == "Custom Range":
        c_date = filter_c3.date_input("Select Range", [datetime.now().date(), datetime.now().date()])
        if len(c_date) == 2:
            start_date, end_date = c_date

    # 3. Base Query Fetching
    query = conn.table("progress_logs").select("*").order("id", desc=True)
    if selected_cust != "All Customers":
        query = query.eq("customer", selected_cust)
    
    res = query.execute()
    data = res.data if res else []

    # 4. Apply Time Filtering Logic (Python side)
    filtered_data = []
    today = datetime.now().date()
    
    if data:
        for log in data:
            try:
                # Identify date (created_at is timestamp, po_date is date string)
                raw_date = log.get('created_at') or log.get('po_date')
                if not raw_date: continue
                log_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()

                if report_type == "Current Week":
                    if log_date.isocalendar()[1] == today.isocalendar()[1] and log_date.year == today.year:
                        filtered_data.append(log)
                elif report_type == "Current Month":
                    if log_date.month == today.month and log_date.year == today.year:
                        filtered_data.append(log)
                elif report_type == "Custom Range" and start_date and end_date:
                    if start_date <= log_date <= end_date:
                        filtered_data.append(log)
                elif report_type == "All Time":
                    filtered_data.append(log)
            except:
                continue
        
        data = filtered_data

    # 5. Display Logic
    if data:
        # --- EXECUTIVE SUMMARY ---
        total_count = len(data)
        dispatched = sum(1 for log in data if log.get('qc_stat') == "Completed")
        in_fab = sum(1 for log in data if log.get('fab_status') == "In-Progress")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Reports", total_count)
        m2.metric("Ready for Dispatch", dispatched)
        m3.metric("Currently in Fab", in_fab)
        st.divider()

        # --- ARCHIVE ACTIONS ---
        st.write(f"📊 Showing {len(data)} reports")
        
        st.download_button(
            label="📥 Download Filtered PDF Report",
            data=generate_pdf(data),
            file_name=f"BG_Report_{selected_cust}_{report_type}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.write("") # Spacer replacing st.ln

        # --- PROJECT CARDS ---
        for log in data:
            with st.expander(f"📦 Job: {log.get('job_code','N/A')} | {log.get('customer','Unknown')}"):
                
                # 1. VISUAL PROGRESS BAR
                total_steps = len(MILESTONE_MAP)
                done_count = sum(1 for _, s_key, _ in MILESTONE_MAP if log.get(s_key) in ["Completed", "Approved", "Submitted", "Received"])
                progress_pct = done_count / total_steps
                
                p_col1, p_col2 = st.columns([4, 1])
                p_col1.progress(progress_pct)
                p_col2.write(f"**{int(progress_pct*100)}% Complete**")
                
                st.markdown("---")

                # 2. KEY DETAILS GRID
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                t_col1.markdown(f"**Equipment**\n\n{log.get('equipment','-')}")
                t_col2.markdown(f"**PO Number**\n\n{log.get('po_no','-')}")
                t_col3.markdown(f"**Engineer**\n\n{log.get('engineer','-')}")
                t_col4.markdown(f"**Dispatch Date**\n\n{log.get('exp_dispatch_date','-')}")
                
                st.divider()

                # 3. MILESTONE TABLE (Streamlined Table Layout)
                st.markdown("#### 🏁 Milestone Tracking Details")
                
                # --- TABLE HEADER ---
                h1, h2, h3 = st.columns([1.5, 1, 2.5])
                h1.write("**Milestone Item**")
                h2.write("**Status**")
                h3.write("**Remarks**")
                st.markdown("---") # Visual separator under header

                # --- TABLE ROWS ---
                for label, s_key, n_key in MILESTONE_MAP:
                    status = log.get(s_key, 'Pending')
                    remark = log.get(n_key) if log.get(n_key) else "_NA_"
                    
                    r1, r2, r3 = st.columns([1.5, 1, 2.5])
                    
                    # Column 1: Milestone Name
                    r1.write(label)
                    
                    # Column 2: Status with Color Indicators
                    if status in ["Completed", "Approved", "Submitted", "Received"]:
                        r2.success(status)
                    elif status in ["In-Progress", "Scheduled", "Ordered"]:
                        r2.warning(status)
                    else:
                        r2.info(status)
                        
                    # Column 3: Remarks (Italicized for a clean look)
                    r3.write(f"_{remark}_")
with tab3:
    st.header("🛠️ Master Data Management")
    col_cust, col_job = st.columns(2)
    with col_cust:
        st.subheader("👥 Customers")
        with st.container(border=True):
            new_cust = st.text_input("New Customer Name", placeholder="e.g. Reliance Industries")
            if st.button("➕ Add Customer", use_container_width=True):
                if new_cust:
                    conn.table("customer_master").insert({"name": new_cust}).execute()
                    st.rerun()
        c_data = conn.table("customer_master").select("*").execute().data
        for c in sorted(c_data, key=lambda x: x['name']):
            c_row1, c_row2 = st.columns([3, 1])
            c_row1.text(f"• {c['name']}")
            if c_row2.button("🗑️", key=f"del_c_{c['id']}"):
                conn.table("customer_master").delete().eq("id", c['id']).execute()
                st.rerun()
    with col_job:
        st.subheader("🔢 Job Codes")
        with st.container(border=True):
            new_job = st.text_input("New Job Code", placeholder="e.g. BG-2024-001")
            if st.button("➕ Add Job Code", use_container_width=True):
                if new_job:
                    conn.table("job_master").insert({"job_code": new_job}).execute()
                    st.rerun()
        j_data = conn.table("job_master").select("*").execute().data
        for j in sorted(j_data, key=lambda x: x['job_code']):
            j_row1, j_row2 = st.columns([3, 1])
            j_row1.text(f"• {j['job_code']}")
            if j_row2.button("🗑️", key=f"del_j_{j['id']}"):
                conn.table("job_master").delete().eq("id", j['id']).execute()
                st.rerun()
