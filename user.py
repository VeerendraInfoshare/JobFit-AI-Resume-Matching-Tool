# user_app.py

import streamlit as st
import os
import json

# Ensure folders exist
os.makedirs("resumes", exist_ok=True)

DATA_FILE = "submissions.json"

st.title("📝 Job Application Form")

# Form for user submission
with st.form("application_form"):
    name = st.text_input("Full Name")
    skills = st.text_input("Skills (comma-separated)")
    experience = st.number_input("Years of Experience", min_value=0, max_value=50)
    motivation = st.text_area("Why do you want to join the company?")
    resume = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
    
    submitted = st.form_submit_button("Submit Application")

    if submitted:
        if name and skills and motivation and resume:
            # Save resume file
            resume_path = os.path.join("resumes", resume.name)
            with open(resume_path, "wb") as f:
                f.write(resume.read())

            # Create submission dict
            submission = {
                "Name": name,
                "Skills": skills,
                "Experience": experience,
                "Motivation": motivation,
                "ResumePath": resume_path
            }

            # Read existing data
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = []

            # Append new submission and save
            data.append(submission)
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)

            st.success("✅ Application submitted and saved successfully!")
        else:
            st.error("❌ Please fill all fields and upload a resume.")
