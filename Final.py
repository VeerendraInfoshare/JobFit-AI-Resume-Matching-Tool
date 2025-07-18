import streamlit as st
import os
import json
import pandas as pd
import uuid
from langchain_community.document_loaders import PyPDFLoader
from ollama import Client
import re
import ast

# ====== Your Provided Model Code - DO NOT CHANGE ======

# ====== Load Resume ======
def load_resume(file_path):
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    return docs[0].page_content if docs else ""

# ====== Extract Candidate Name ======
def extract_name(resume_text, client):
    name_prompt = f"""
You are a resume parser. Extract only the full name of the candidate from the given resume text. 
✅ STRICTLY RETURN: Full name only, no titles, no salutations, no extra text.
Resume Text:
\"\"\"{resume_text}\"\"\"
"""
    name_response = client.chat(
        model="llama2:7b",
        messages=[{"role": "user", "content": name_prompt}]
    )
    return name_response['message']['content'].strip()

# ====== Extract Email ======
def extract_email(text):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else "Email not found"

# ====== Extract Skills ======
def extract_skills(resume_text, client):
    skill_prompt = f"""
Extract only the **technical skills** from the following resume text. 

✅ STRICTLY RETURN:
- A **valid Python list**
- Do NOT include explanations, numbering, or categories
- Only the skills (e.g., tools, programming languages, platforms, APIs, frameworks)

Resume:
\"\"\"{resume_text}\"\"\"
"""
    response = client.chat(
        model='llama2:7b',
        messages=[{"role": "user", "content": skill_prompt}]
    )
    return response['message']['content']

# ====== Clean Skills Output ======
def clean_skills(raw_text):
    try:
        parsed = ast.literal_eval(raw_text.strip())
        if isinstance(parsed, list):
            return [s.strip() for s in parsed if isinstance(s, str) and s.strip()]
    except Exception:
        pass
    lines = raw_text.splitlines()
    skills = []
    for line in lines:
        line = line.strip().lstrip("-•* ")
        if line.lower().startswith("note:"):
            continue
        if ":" in line:
            _, skill_str = line.split(":", 1)
            skills += [s.strip() for s in skill_str.split(",")]
        elif "," in line:
            skills += [s.strip() for s in line.split(",")]
        else:
            skills.append(line.strip())
    return list(set([s for s in skills if s]))

# ====== Check if Fresher ======
def is_fresher(text):
    if re.search(r"(b\.tech|bachelor|degree|graduation|student)", text, re.IGNORECASE):
        if re.search(r"(2023|2024|2025)", text):
            return True
    return False

# ====== Extract Experience Section ======
def extract_professional_experience_section(text):
    match = re.search(
        r"(Work Experience|Professional Experience|Employment History|Experience Summary|Employment Experience|Career Summary)(.*?)(Education|Projects|Skills|Certifications|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )
    experience_section = match.group(2) if match else text
    filtered_lines = [
        line for line in experience_section.splitlines()
        if not re.search(r"(intern|internship|project|capstone|academic|training|volunteer)", line, re.IGNORECASE)
    ]
    return "\n".join(filtered_lines).strip()

# ====== Extract Years from Experience ======
def extract_years_and_months(exp_str):
    years = months = 0
    year_match = re.search(r'(\d+)\s*years?', exp_str.lower())
    month_match = re.search(r'(\d+)\s*months?', exp_str.lower())
    if year_match:
        years = int(year_match.group(1))
    if month_match:
        months = int(month_match.group(1))
    return years

# ====== Experience Extraction Logic ======
def extract_experience(resume_text, client):
    if is_fresher(resume_text):
        return "Total experience: 0 years 0 months", 0
    else:
        filtered_text = extract_professional_experience_section(resume_text)
        exp_prompt = f"""
From the following text, extract only the **total number of years and months of full-time professional work experience** (in industry/company jobs only).

🚫 Do NOT count:
- internships
- academic/capstone/freelance/training experience
- college or research projects

✅ Only count professional jobs (e.g., Software Engineer, Developer, etc.)

Format:
"Total experience: X years Y months"

Text:
\"\"\"{filtered_text}\"\"\"
"""
        response = client.chat(
            model='llama2:7b',
            messages=[{"role": "user", "content": exp_prompt}]
        )
        exp_data = response['message']['content']
        years = extract_years_and_months(exp_data)
        return exp_data, years

# ====== Master Function ======
def parse_resume(file_path):
    resume_text = load_resume(file_path)
    client = Client(host='http://localhost:11434')

    name = extract_name(resume_text, client)
    email = extract_email(resume_text)
    raw_skills = extract_skills(resume_text, client)
    skills = clean_skills(raw_skills)
    experience_text, years = extract_experience(resume_text, client)

    return {
        "name": name,
        "email": email,
        "skills_cleaned": skills,
        "Experience": years
    }


# ================= Streamlit App Starts Here =================

st.set_page_config(page_title="Candidate Hiring Recommendation System", layout="centered")
os.makedirs("resumes", exist_ok=True)
DATA_FILE = "submissions.json"
client = Client(host='http://localhost:11434')

if "page" not in st.session_state:
    st.session_state.page = "home"

def go_home():
    st.session_state.page = "home"

def go_user():
    st.session_state.page = "user"

def go_admin():
    st.session_state.page = "admin"


# --- HOME PAGE ---
if st.session_state.page == "home":
    st.markdown("<h2 style='text-align: center;'>Candidate Hiring Recommendation System</h2>", unsafe_allow_html=True)
    st.markdown("##")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("USER", use_container_width=True, on_click=go_user):
            pass
        if st.button("ADMIN", use_container_width=True, on_click=go_admin):
            pass

# --- USER PAGE ---
elif st.session_state.page == "user":
    if st.button("⬅️ Back to Home", on_click=go_home):
        pass
    st.title("Job Application Form")
    with st.form("application_form"):
        name = st.text_input("Full Name *")
        email = st.text_input("Email *")
        skills = st.text_input("Skills (comma-separated) *")
        experience = st.number_input("Years of Experience *", min_value=0, max_value=50)
        motivation = st.text_area("Why should we hire you? (optional)")
        resume = st.file_uploader("Upload Resume (PDF or DOCX) *", type=["pdf", "docx"])
        submitted = st.form_submit_button("Submit Application")

        if submitted:
            if name.strip() and email.strip() and skills.strip() and resume is not None:
                # Generate unique filename for resume
                ext = os.path.splitext(resume.name)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                resume_path = os.path.join("resumes", unique_filename)
                with open(resume_path, "wb") as f:
                    f.write(resume.read())

                # Load existing data
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, "r") as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                        else:
                            data = []
                else:
                    data = []

                # Check if email exists and update
                updated = False
                for i, item in enumerate(data):
                    if item.get("Email", "").strip().lower() == email.strip().lower():
                        # Remove old resume file if exists
                        old_resume = item.get("ResumePath", "")
                        if old_resume and os.path.exists(old_resume):
                            os.remove(old_resume)

                        # Update data
                        data[i] = {
                            "Name": name.strip(),
                            "Email": email.strip(),
                            "Skills": skills.strip(),
                            "Experience": experience,
                            "Motivation": motivation.strip(),
                            "ResumePath": resume_path
                        }
                        updated = True
                        break

                if not updated:
                    data.append({
                        "Name": name.strip(),
                        "Email": email.strip(),
                        "Skills": skills.strip(),
                        "Experience": experience,
                        "Motivation": motivation.strip(),
                        "ResumePath": resume_path
                    })

                with open(DATA_FILE, "w") as f:
                    json.dump(data, f, indent=4)

                st.success("✅ Application submitted and saved successfully!")
            else:
                st.error("❌ Please fill all mandatory fields and upload a resume.")

# --- ADMIN PAGE ---
elif st.session_state.page == "admin":
    if st.button("⬅️ Back to Home", on_click=go_home):
        pass
    st.title("Admin Panel - Candidate Evaluation")

    mandatory_input = st.text_input("Mandatory Skills *")
    good_input = st.text_input("Good-to-Have Skills *")
    min_exp = st.number_input("Required Experience (in years) *", min_value=0, value=2)
    uploaded_files = st.file_uploader("Upload Resumes (PDF) (Optional)", type=["pdf"], accept_multiple_files=True)

    def evaluate_candidate(resume_skills, resume_exp, mandatory, good, min_exp):
        resume_skills_lower = [s.lower() for s in resume_skills]
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

    if st.button("Evaluate Candidates"):
        mandatory_skills = [s.strip() for s in mandatory_input.split(",") if s.strip()]
        good_skills = [s.strip() for s in good_input.split(",") if s.strip()]

        if not mandatory_skills or not good_skills:
            st.warning("⚠️ Please fill all required fields.")
        else:
            all_results = []

            if uploaded_files:
                for idx, uploaded_file in enumerate(uploaded_files, start=1):
                    with st.spinner(f"Processing: {uploaded_file.name}"):
                        ext = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{uuid.uuid4().hex}{ext}"
                        resume_path = os.path.join("resumes", unique_filename)
                        with open(resume_path, "wb") as f:
                            f.write(uploaded_file.read())

                        parsed = parse_resume(resume_path)
                        candidate_name = parsed["name"]
                        candidate_email = parsed["email"]
                        resume_skills = parsed["skills_cleaned"]
                        resume_exp = parsed["Experience"]

                        fit_score, fit_status, reason = evaluate_candidate(
                            resume_skills, resume_exp, mandatory_skills, good_skills, min_exp
                        )

                        # Load existing data for update or add
                        if os.path.exists(DATA_FILE):
                            with open(DATA_FILE, "r") as f:
                                content = f.read().strip()
                                if content:
                                    data = json.loads(content)
                                else:
                                    data = []
                        else:
                            data = []

                        updated = False
                        for i, item in enumerate(data):
                            if item.get("Email", "").strip().lower() == candidate_email.strip().lower():
                                old_resume = item.get("ResumePath", "")
                                if old_resume and os.path.exists(old_resume):
                                    os.remove(old_resume)
                                data[i] = {
                                    "Name": candidate_name,
                                    "Email": candidate_email,
                                    "Skills": ", ".join(resume_skills),
                                    "Experience": resume_exp,
                                    "Motivation": "Imported via Resume",
                                    "ResumePath": resume_path
                                }
                                updated = True
                                break
                        if not updated:
                            data.append({
                                "Name": candidate_name,
                                "Email": candidate_email,
                                "Skills": ", ".join(resume_skills),
                                "Experience": resume_exp,
                                "Motivation": "Imported via Resume",
                                "ResumePath": resume_path
                            })

                        with open(DATA_FILE, "w") as f:
                            json.dump(data, f, indent=4)

                        all_results.append({
                            "Candidate Name": candidate_name,
                            "Email": candidate_email,
                            "Fit Score": fit_score,
                            "Fit Status": fit_status,
                            "Reason": reason,
                            "Resume File": uploaded_file.name
                        })

                st.success("✅ All uploaded resumes evaluated.")

            else:
                if not os.path.exists(DATA_FILE):
                    st.warning("No candidate data found.")
                else:
                    with open(DATA_FILE, "r") as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                        else:
                            data = []

                    if not data:
                        st.info("No submissions yet.")
                    else:
                        all_results = []
                        for idx, item in enumerate(data, start=1):
                            skills_list = [s.strip().lower() for s in item.get("Skills", "").split(",")]
                            mand = [s.lower() for s in mandatory_skills]
                            good = [s.lower() for s in good_skills]

                            mand_score = sum(1 for s in mand if s in skills_list) / len(mand) if mand else 0
                            good_score = sum(1 for s in good if s in skills_list) / len(good) if good else 0
                            exp_score = min(item.get("Experience", 0) / min_exp, 1) if min_exp > 0 else 1

                            fit_score = round((mand_score * 0.6 + good_score * 0.2 + exp_score * 0.2) * 100, 2)
                            fit_status = "Fit" if fit_score >= 70 else "Moderate Fit" if fit_score >= 50 else "Not Fit"

                            reason = "Candidate meets requirements." if fit_status == "Fit" else "Candidate does not fully meet requirements."

                            all_results.append({
                                "Candidate Name": item.get("Name", ""),
                                "Email": item.get("Email", ""),
                                "Fit Score": fit_score,
                                "Fit Status": fit_status,
                                "Reason": reason,
                                "Resume File": os.path.basename(item.get("ResumePath", "N/A"))
                            })

            if all_results:
                df = pd.DataFrame(all_results)
                st.success("✅ Candidate evaluation completed from stored data.")
                st.dataframe(df)
                st.download_button("⬇️ Download CSV", df.to_csv(index=False), file_name="Evaluation_Results.csv", mime="text/csv")
