# JobFit-AI-Resume-Matching-Tool
An AI-powered tool that compares resume with job descriptions to calculate fit scores and recommend candidates for hiring.
# 🧠 Job Application and Resume Evaluation System

This is a two-part Streamlit application that allows job seekers to submit applications and lets recruiters evaluate those applications based on either:
- Skills & experience (from a JSON database)
- Resume content (via AI-based analysis using LangChain & Ollama)

## 🚀 Features

### 👤 User Side (Job Application)
- Submit name, skills, experience, motivation
- Upload resume (PDF/DOCX)
- All submissions stored in `submissions.json`
- Resumes stored under the `resumes/` folder

### 🛠️ Admin Panel
- **Skill-based evaluation** from submitted JSON data
- **Resume-based evaluation** using:
  - Ollama-powered LLM (e.g. `llama2`)
  - LangChain PDF parsing
  - Fit scoring based on mandatory skills, good-to-have skills, and experience
- Download evaluation results in CSV or Excel

## 📁 Project Structure

```
.
├── resumes/                     # Folder to store uploaded resumes
├── submissions.json             # JSON file with candidate submissions
├── evaluated_results.csv        # Generated skill-based evaluation results
├── Resume_Evaluation.xlsx       # Generated resume-based evaluation results
├── user_app.py                  # Candidate application submission app
├── admin_app.py                 # Admin evaluation panel
├── README.md                    # You're reading this!
```

## 🧠 Requirements

- Python 3.8+
- Streamlit
- pandas
- LangChain
- PyPDFLoader (from `langchain_community`)
- Ollama running locally (`llama2:7b` or any compatible model)

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/job-evaluation-app.git
cd job-evaluation-app

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> ✏️ You may need to manually install `ollama`, `langchain_community`, and `streamlit` if not already installed.

## 🏁 Running the Apps

1. **Start Ollama locally** with the required model:
   ```bash
   ollama run llama2
   ```

2. **Run the User Submission App**:
   ```bash
   streamlit run user_app.py
   ```

3. **Run the Admin Evaluation Panel**:
   ```bash
   streamlit run admin_app.py
   ```

## 📄 Example LLM Usage

The Admin Panel uses prompts like:
```text
Extract only the technical skills (programming languages, libraries, frameworks, tools, platforms, APIs) from the resume below...
```

## 📌 Notes

- Ensure `ollama` server is running before using the Admin Panel.
- All resume files are saved to `resumes/` directory.
- Admin evaluations are non-destructive and support multiple resume uploads.

## ✨ Future Enhancements

- Add authentication for admin panel
- Support DOCX resume parsing
- Use cloud storage and databases (e.g., Firebase, PostgreSQL)

## 📬 Contact

For any questions or contributions, feel free to open an issue or pull request.

---

Made with ❤️ using Streamlit, Ollama, and LangChain
