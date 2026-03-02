def header(self):
        # Professional B&G Branding
        import os
        
        # This line helps the app find the logo regardless of the folder structure
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        else:
            # If logo is missing, we write the name in bold text so it doesn't crash
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'B&G ENGINEERING INDUSTRIES', ln=True)
        
        self.set_font('Arial', 'B', 15)
        self.cell(80) 
        self.cell(110, 10, 'B&G ENGINEERING INDUSTRIES', ln=True, align='R')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'PROJECT PROGRESS REPORT', ln=True, align='R')
        self.ln(20)
