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
    ("QC Status", "qc_stat", "qc_note"),
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
        
        # 1. DRAW BACKGROUND FIRST
        pdf.set_fill_color(0, 51, 102) # Dark Blue
        pdf.rect(0, 0, 210, 35, 'F')
        
        # 2. PLACE LOGO ON TOP OF BACKGROUND
        try:
            # Attempt to download logo.png from the bucket
            logo_bytes = conn.client.storage.from_("progress-photos").download("logo.png")
            if logo_bytes:
                # Place at x=10, y=5, with height 22
                pdf.image(BytesIO(logo_bytes), x=10, y=5, h=22)
        except Exception as e:
            # If it fails, we leave the area blank or add a small placeholder text for debugging
            pdf.set_xy(10, 5)
            pdf.set_font("Arial", "I", 6)
            pdf.set_text_color(200, 200, 200)
            # pdf.cell(30, 10, "Logo Load Error") # Uncomment this to see if the script is failing to find the file

        # 3. HEADER TEXT
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 18)
        pdf.set_xy(40, 10) 
        pdf.cell(130, 10, "B&G ENGINEERING INDUSTRIES", 0, 1, "C")
        pdf.set_font("Arial", "I", 10)
        pdf.set_x(40)
        pdf.cell(130, 5, "PROJECT PROGRESS REPORT", 0, 1, "C")
        pdf.ln(15)

        # 4. JOB INFO HEADER
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 10)
        pdf.set_xy(10, 38)
        pdf.cell(0, 8, f" JOB: {log.get('job_code','')} | ID: {log.get('id','')}", "B", 1, "L")
        pdf.ln(3)
        
        # 5. HEADER FIELDS TABLE
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        for i in range(0, len(HEADER_FIELDS), 2):
            f1, f2 = HEADER_FIELDS[i], HEADER_FIELDS[i+1]
            pdf.cell(30, 7, f" {f1.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f1,''))}", 1, 0, 'L')
            pdf.cell(30, 7, f" {f2.replace('_',' ').title()}", 1, 0, 'L', True)
            pdf.cell(65, 7, f" {str(log.get(f2,''))}", 1, 1, 'L')

        pdf.ln(5)

        # 6. MILESTONE TABLE
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
            elif status in ["In-Progress", "Hold"]:
                pdf.set_fill_color(255, 255, 204)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(60, 7, f" {label}", 1)
            pdf.cell(35, 7, f" {status}", 1, 0, 'C', True)
            pdf.cell(95, 7, f" {str(log.get(n_key,'-'))}", 1, 1)

        # 7. PROGRESS PHOTO
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

# --- REST OF THE STREAMLIT APP (TABS 1, 2, 3) REMAINS EXACTLY THE SAME ---
# [Keep your existing Tab logic here]
