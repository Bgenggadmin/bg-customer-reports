st.divider()
        st.subheader("📸 Shop Floor Media")
        
        # 1. Camera Input (For live snapshots)
        cam_photo = st.camera_input("Take a Live Photo")
        
        # 2. File Uploader (For existing gallery photos)
        gallery_photos = st.file_uploader("Upload from Gallery", accept_multiple_files=True)
        
        submit = st.form_submit_button("🚀 Sync to Cloud & Save")

        if submit:
            if not cust or not job:
                st.error("Please select a Customer and Job Code.")
            else:
                # 1. Save Text Data
                res = conn.table("progress_logs").insert({
                    "customer": cust, "engineer": eng, "equipment": eq,
                    "job_code": job, "po_no": po, "target_date": str(target),
                    "fab_status": status, "remarks": remarks
                }).execute()
                
                log_id = res.data[0]['id']

                # 2. Consolidate all photos (Camera + Gallery)
                all_pics = []
                if cam_photo:
                    all_pics.append(cam_photo)
                if gallery_photos:
                    all_pics.extend(gallery_photos)

                # 3. Upload to Storage
                if all_pics:
                    for i, pic in enumerate(all_pics):
                        # Generate a unique name if it's from the camera
                        fname = pic.name if hasattr(pic, 'name') else f"camera_{i}.jpg"
                        path = f"reports/{log_id}/{fname}"
                        conn.storage.from_("progress-photos").upload(path, pic.getvalue())
                
                st.success(f"✅ Report for {eq} successfully archived with {len(all_pics)} photos!")
                st.rerun()
