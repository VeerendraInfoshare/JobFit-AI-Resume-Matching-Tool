import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from ollama import Client
import re
import os
import pandas as pd

# Ollama Client
client = Client(host='http://localhost:11434')

# --- Extraction Functions ---

def extract_technical_skills(docs_text):
    prompt = f"""
Extract only the technical skills (programming languages, libraries, frameworks, tools, platforms, APIs) from the resume below.

✅ RETURN FORMAT: A valid Python list like this: ["Python", "Java", "SQL"]
❌ Do NOT include any explanation, categories, or formatting.

Resume:
\"\"\"
{docs_text}
\"\"\"
"""
    response = client.chat(
        model='llama2:7b',
        messages=[{"role": "user", "content": prompt}]
    )
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
        print("Error while cleaning skills:", e)
        return []

def extract_experience(docs_text):
    prompt = f"""
From the resume text below, extract only the total **professional experience** in years and months.

✅ RETURN FORMAT: "Total experience: X years Y months"
❌ Do NOT include anything else.

Resume:
\"\"\"
{docs_text}
\"\"\"
"""
    response = client.chat(
        model='llama2:7b',
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content']

def extract_candidate_name(docs_text):
    prompt = f"""
Extract the full name of the candidate from the resume text below.

✅ RETURN ONLY the name, no extra text or formatting.

Resume:
\"\"\"
{text}
\"\"\"
"""
    response = client.chat(
        model='llama2:7b',
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content']

def clean_candidate_name(name_response):
    # Remove common leading phrases
    cleaned = re.sub(r'(?i)^(the\s+)?full\s+name\s+of\s+the\s+candidate\s+is[:\-]?\s*', '', name_response.strip())
    # Keep only the first line (in case there's extra)
    return cleaned.split('\n')[0].strip()


#def extract_years_from_string(exp_str):
    #match = re.search(r'(\d+)(?:\.\d+)?\s*years?', exp_str.lower())
    #if match:
        #return int(match.group(1))
    #return 0"""

def extract_years_from_string(exp_str):
    # Lowercase and clean up common formatting issues
    exp_str = exp_str.lower().strip()
    
    # Remove symbols like '+' and words like 'plus'
    exp_str = exp_str.replace("+", "").replace("plus", "").replace("approximately", "").replace("about", "")

    # Match year patterns like: 14, 14.5, 14 years, 14.5 years
    year_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', exp_str)
    years = float(year_match.group(1)) if year_match else 0.0

    # Match months if available
    month_match = re.search(r'(\d+)\s*months?', exp_str)
    months = int(month_match.group(1)) if month_match else 0

    # Final result
    total_years = round(years + (months / 12), 2)
    return total_years

# --- Evaluation Function ---

def evaluate_candidate(resume_skills, resume_exp, mandatory, good, min_exp):
    resume_skills_lower = [skill.lower() for skill in resume_skills]

    matched_mandatory = [s for s in mandatory if s.lower() in resume_skills_lower]
    missing_mandatory = [s for s in mandatory if s.lower() not in resume_skills_lower]
    matched_good = [s for s in good if s.lower() in resume_skills_lower]
    missing_good = [s for s in good if s.lower() not in resume_skills_lower]

    experience_matched = resume_exp >= min_exp

    mandatory_score = len(matched_mandatory) / len(mandatory) * 100 if mandatory else 100
    good_score = len(matched_good) / len(good) * 100 if good else 0
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

# --- Streamlit UI ---

st.set_page_config(page_title="Resume Evaluator", layout="centered")
st.title("📄 Job Fit AI")

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

                # Extract candidate details
                raw_skills = extract_technical_skills(text)
                resume_skills = clean_skills(raw_skills)
                exp_text = extract_experience(text)
                resume_exp = extract_years_from_string(exp_text)
                candidate_name = extract_candidate_name(text)

                # Evaluate
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

        st.success("✅ All resumes evaluated.")

        # Display table
        st.subheader("📊 Evaluation Results")
        df = pd.DataFrame(all_results)
        st.dataframe(df)

        # Download as CSV
        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", data=csv, file_name="Resume_Evaluation.csv", mime="text/csv")

        # Download as Excel
        excel_file = "Resume_Evaluation.xlsx"
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button("📥 Download Excel", data=f, file_name=excel_file, mime="application/vnd.ms-excel")
