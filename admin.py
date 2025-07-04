# admin_app.py

import streamlit as st
import pandas as pd
import json
import os
import re
from langchain_community.document_loaders import PyPDFLoader
from ollama import Client

# --- Setup ---
st.set_page_config(page_title="Admin Evaluation Panel", layout="centered")
st.title("🛠️ Admin Panel - Candidate Evaluation")

# Ollama Client for LLM-based resume evaluation
client = Client(host='http://localhost:11434')


# --- Shared Functions for Resume Mode ---

def extract_technical_skills(docs_text):
    prompt = f"""
Extract only the technical skills (programming languages, libraries, frameworks, tools, platforms, APIs) from the resume below.

✅ RETURN FORMAT: A valid Python list like this: ["Python", "Java", "SQL"]
❌ Do NOT include any explanation, categories, or formatting.

Resume:
\"\"\"{docs_text}\"\"\"
"""
    response = client.chat(model='llama2:7b', messages=[{"role": "user", "content": prompt}])
    return response['message']['content']


def clean_skills(raw_skills_text):
    try:
        lines = raw_skills_text.strip().splitlines()
        skills = []
        for line in lines:
            match = re.match(r'^\d+\.\s*(.+)', line.strip())
            if match:
                skill = match.group(1).strip()
                skills.append(skill)
        return skills
    except Exception as e:
        return []


def extract_experience(docs_text):
    prompt = f"""
From the resume text below, extract only the total **professional experience** in years and months.

✅ RETURN FORMAT: "Total experience: X years Y months"
❌ Do NOT include anything else.

Resume:
\"\"\"{docs_text}\"\"\"
"""
    response = client.chat(model='llama2:7b', messages=[{"role": "user", "content": prompt}])
    return response['message']['content']


def extract_candidate_name(docs_text):
    prompt = f"""
Extract the full name of the candidate from the resume text below.

✅ RETURN ONLY the name, no extra text or formatting.

Resume:
\"\"\"{docs_text}\"\"\"
"""
    response = client.chat(model='llama2:7b', messages=[{"role": "user", "content": prompt}])
    return response['message']['content']


def extract_years_from_string(exp_str):
    exp_str = exp_str.lower().strip()
    exp_str = exp_str.replace("+", "").replace("plus", "").replace("approximately", "").replace("about", "")
    year_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', exp_str)
    years = float(year_match.group(1)) if year_match else 0.0
    month_match = re.search(r'(\d+)\s*months?', exp_str)
    months = int(month_match.group(1)) if month_match else 0
    return round(years + (months / 12), 2)


def evaluate_candidate(resume_skills, resume_exp, mandatory, good, min_exp):
    resume_skills_lower = [skill.lower() for skill in resume_skills]
    matched_mandatory = [s for s in mandatory if s.lower() in resume_skills_lower]
    missing_mandatory = [s for s in mandatory if s.lower() not in resume_skills_lower]
    experience_matched = resume_exp >= min_exp

    mandatory_score = len(matched_mandatory) / len(mandatory) * 100 if mandatory else 100
    experience_score = 100 if experience_matched else (resume_exp / min_exp) * 100
    fit_score = round((mandatory_score * 0.6 + experience_score * 0.4), 2)

    is_fit = not missing_mandatory and experience_matched
    reason = "Candidate is a good fit." if is_fit else "Candidate is not a good fit due to:"
    if not is_fit:
        if missing_mandatory:
            reason += f" missing mandatory skills: {missing_mandatory}."
        if not experience_matched:
            reason += f" insufficient experience ({resume_exp} < {min_exp} years)."

    return fit_score, "Fit" if is_fit else "Not Fit", reason


# --- Toggle between Skill and Resume Based Evaluation ---

mode = st.radio("Choose Evaluation Mode", ["📊 via Skills", "📄 via Resume"], horizontal=True)


# --- MODE 1: Skill-based Evaluation (JSON) ---
if mode == "📊 via Skills":
    #st.subheader("📑 Evaluate Candidates Based on Skills & Experience")

    DATA_FILE = "submissions.json"

    if not os.path.exists(DATA_FILE):
        st.warning("No submissions found yet.")
        st.stop()

    with open(DATA_FILE, "r") as f:
        submissions = json.load(f)

    if not submissions:
        st.info("No candidate submissions yet.")
        st.stop()

    df = pd.DataFrame(submissions)
    #st.dataframe(df)

    st.write("### 🧠 Job Requirements")
    mandatory_skills = st.text_input("Mandatory Skills (comma-separated)")
    good_to_have_skills = st.text_input("Good to Have Skills (comma-separated)")
    required_exp = st.number_input("Required Experience (in years)", min_value=0, max_value=50)

    if st.button("🔍 Evaluate via Skills"):
        def calc_fit(candidate_skills, candidate_exp):
            skills = [s.strip().lower() for s in candidate_skills.split(",")]
            mandatory = [s.strip().lower() for s in mandatory_skills.split(",") if s]
            good = [s.strip().lower() for s in good_to_have_skills.split(",") if s]

            mand_score = sum(1 for s in mandatory if s in skills) / len(mandatory) if mandatory else 0
            good_score = sum(1 for s in good if s in skills) / len(good) if good else 0
            exp_score = min(candidate_exp / required_exp, 1) if required_exp > 0 else 1

            fit_score = (mand_score * 0.6 + good_score * 0.2 + exp_score * 0.2) * 100
            return round(fit_score, 2), mand_score, good_score, exp_score

        results = []
        for idx, row in df.iterrows():
            score, _, _, _ = calc_fit(row["Skills"], row["Experience"])
            status = "🟢 Strong Fit" if score >= 70 else "🟡 Moderate Fit" if score >= 50 else "🔴 Not a Fit"
            reason = "Meets most skills" if score >= 70 else "Some gaps exist" if score >= 50 else "Skills/Experience mismatch"
            results.append({
                "Sl.No": idx + 1,
                "Name": row["Name"],
                "Skills": row["Skills"],
                "Experience": row["Experience"],
                "Fit Score": score,
                "Fit Status": status,
                "Recommendation": reason
            })

        result_df = pd.DataFrame(results)
        st.success("✅ Evaluation complete!")
        st.dataframe(result_df)

        result_df.to_csv("evaluated_results.csv", index=False)
        with open("evaluated_results.csv", "rb") as f:
            st.download_button("⬇️ Download CSV", f, file_name="evaluated_results.csv")


# --- MODE 2: Resume-based Evaluation ---
elif mode == "📄 via Resume":
    st.subheader("📄 Evaluate Candidates Using Uploaded Resumes")

    uploaded_files = st.file_uploader("📤 Upload Multiple Resumes (PDF)", type=["pdf"], accept_multiple_files=True)
    mandatory_input = st.text_input("✅ Mandatory Skills (comma-separated)")
    good_input = st.text_input("👍 Good-to-have Skills (comma-separated)")
    min_exp = st.number_input("📆 Minimum Experience Required (in years)", min_value=0, value=2)

    if st.button("🚀 Evaluate All Resumes"):
        if not uploaded_files:
            st.warning("⚠️ Please upload at least one resume.")
        elif not mandatory_input:
            st.warning("⚠️ Please enter mandatory skills.")
        else:
            mandatory_skills = [s.strip() for s in mandatory_input.split(",")]
            good_skills = [s.strip() for s in good_input.split(",") if s.strip()]
            all_results = []

            for idx, uploaded_file in enumerate(uploaded_files, start=1):
                with st.spinner(f"Processing: {uploaded_file.name}"):
                    with open("temp_resume.pdf", "wb") as f:
                        f.write(uploaded_file.read())

                    loader = PyPDFLoader("temp_resume.pdf")
                    docs = loader.load()
                    text = " ".join([d.page_content for d in docs])

                    raw_skills = extract_technical_skills(text)
                    resume_skills = clean_skills(raw_skills)
                    exp_text = extract_experience(text)
                    resume_exp = extract_years_from_string(exp_text)
                    candidate_name = extract_candidate_name(text)

                    fit_score, fit_status, reason = evaluate_candidate(
                        resume_skills, resume_exp, mandatory_skills, good_skills, min_exp
                    )

                    all_results.append({
                        "Sl. No.": idx,
                        "Resume Name": uploaded_file.name,
                        "Candidate Name": candidate_name,
                        "Fit Score": fit_score,
                        "Fit Status": fit_status,
                        "Reason": reason
                    })

            df = pd.DataFrame(all_results)
            st.success("✅ All resumes evaluated.")
            st.dataframe(df)

            # CSV + Excel Download
            st.download_button("📥 Download CSV", df.to_csv(index=False), file_name="Resume_Evaluation.csv", mime="text/csv")

            excel_file = "Resume_Evaluation.xlsx"
            df.to_excel(excel_file, index=False)
            with open(excel_file, "rb") as f:
                st.download_button("📥 Download Excel", data=f, file_name=excel_file, mime="application/vnd.ms-excel")
