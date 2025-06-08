import google.generativeai as genai
import json
import os
import subprocess
import sys
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if len(sys.argv) < 2:
    print("Usage: python create_resume.py <path_to_job_description.txt>")
    sys.exit(1)
JOB_DESCRIPTION_PATH = sys.argv[1]
BASE_OUTPUT_NAME = "tailored_resume"

def sanitize_latex(text):
    """Sanitizes text to be safe for LaTeX."""
    if not isinstance(text, str): return text
    return text.replace('&', r'\&').replace('%', r'\%').replace('$', r'\$').replace('#', r'\#').replace('_', r'\_').replace('{', r'\{').replace('}', r'\}').replace('~', r'\textasciitilde{}').replace('^', r'\textasciicircum{}')

def setup_api():
    """Configures the Gemini API and handles missing API key."""
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        sys.exit(1)

def get_user_info():
    """Interactively collects resume information from the user."""
    print("--- Please provide your information ---")
    data = {}
    data['name'] = input("Full Name: ")
    data['phone'] = input("Phone Number: ")
    data['email'] = input("Email Address: ")
    data['linkedin'] = input("LinkedIn URL: ")
    data['github'] = input("GitHub URL: ")
    
    data['education'] = []
    while True:
        add_edu = input("Add an education entry? (y/n): ").lower()
        if add_edu != 'y': break
        edu = {}
        edu['university'] = input("  University/School Name: ")
        edu['location'] = input("  Location (e.g., City, State): ")
        edu['degree'] = input("  Degree (e.g., M.S. in Computer Science): ")
        edu['dates'] = input("  Dates (e.g., Aug 2023 - May 2025): ")
        edu['details'] = []
        print("  Enter details/coursework (one per line, press Enter on an empty line to finish):")
        while True:
            detail = input("    > ")
            if not detail: break
            edu['details'].append(detail)
        data['education'].append(edu)

    data['experience'] = []
    while True:
        add_exp = input("Add a work experience entry? (y/n): ").lower()
        if add_exp != 'y': break
        exp = {}
        exp['company'] = input("  Company Name: ")
        exp['location'] = input("  Location: ")
        exp['title'] = input("  Job Title: ")
        exp['dates'] = input("  Dates: ")
        exp['points'] = []
        print("  Enter bullet points/duties (one per line, press Enter on an empty line to finish):")
        while True:
            point = input("    > ")
            if not point: break
            exp['points'].append(point)
        data['experience'].append(exp)
        
    return data

def generate_creative_content(model, user_data, job_desc):
    """Asks the AI to generate the summary, skills, and projects."""
    print("\n🤖 Calling Gemini to generate creative content (Summary, Skills, Projects)...")

    prompt = f"""
    You are an expert resume writer. Your task is to take a candidate's core information and a target job description, and then generate a compelling summary, skills section, and project section to make them a perfect fit for the job.

    **Candidate's Core Information:**
    ```json
    {json.dumps(user_data, indent=2)}
    ```

    **Target Job Description:**
    ```
    {job_desc}
    ```

    **Your Task:**
    1.  **Write a `summary`:** A powerful, 2-3 line introduction that highlights the candidate's experience and aligns with the job description.
    2.  **Create a `skills` object:** Invent a list of relevant technical skills based on the job description. Group them into logical categories (e.g., "Languages", "Frameworks", "Cloud").
    3.  **Invent a `projects` list:** Create exactly 3 new, highly relevant, and plausible project descriptions. For each project, create a compelling `name`, realistic `dates`, and 2-3 detailed `points` with strong, quantifiable metrics (e.g., percentages, latency, accuracy improvements) that showcase skills mentioned in the job description.

    You MUST return ONLY a single, valid JSON object containing the `summary`, `skills`, and `projects` keys.
    """
    try:
        response = model.generate_content(prompt)
        # It's critical to clean the response to get valid JSON
        cleaned_response = response.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error calling Gemini API or parsing creative content JSON: {e}")
        return None

def build_latex_from_data(data):
    """Builds the entire LaTeX document from scratch using the provided data."""
    
    latex_parts = [r"""
\documentclass[letterpaper,11pt]{article}
\usepackage{latexsym}\usepackage[empty]{fullpage}\usepackage{titlesec}\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}\usepackage{verbatim}\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}\usepackage{fancyhdr}\usepackage[english]{babel}
\usepackage{tabularx}\usepackage{fontawesome5}\usepackage{multicol}
\setlength{\multicolsep}{-3.0pt}\setlength{\columnsep}{-1.0pt}\input{glyphtounicode}
\pagestyle{fancy}\fancyhf{}\fancyfoot{}\renewcommand{\headrulewidth}{0pt}\renewcommand{\footrulewidth}{0pt}
\addtolength{\oddsidemargin}{-0.5in}\addtolength{\evensidemargin}{-0.5in}\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}\addtolength{\textheight}{1.0in}
\urlstyle{same}\raggedbottom\raggedright\setlength{\tabcolsep}{0in}
\titleformat{\section}{\vspace{-4pt}\scshape\raggedright\large}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]
\pdfgentounicode=1
\newcommand{\resumeItem}[1]{\item\small{{#1 \vspace{-3pt}}}}
\newcommand{\resumeSubheading}[4]{\vspace{-2pt}\item\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}\textbf{#1} & #2 \\\textit{\small#3} & \textit{\small #4} \\\end{tabular*}\vspace{-7pt}}
\newcommand{\resumeProjectHeading}[2]{\item\begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}\small#1 & #2 \\\end{tabular*}\vspace{-7pt}}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}
\begin{document}
"""]
    name = sanitize_latex(data.get('name', ''))
    phone = sanitize_latex(data.get('phone', ''))
    email = data.get('email', '')
    linkedin = data.get('linkedin', '')
    github = data.get('github', '')
    linkedin_user = linkedin.split('/')[-1] if 'linkedin.com' in linkedin else linkedin
    github_user = github.split('/')[-1] if 'github.com' in github else github
    latex_parts.append(f"""
\\begin{{center}}
    \\textbf{{\\Huge \\scshape {{\\fontsize{{15pt}}{{20pt}}\\selectfont {name}}}}} \\\\ \\vspace{{1pt}}
    \\small \\raisebox{{-0.1\\height}}\\faPhone\\ {phone} ~ \\href{{mailto:{email}}}{{\\raisebox{{-0.2\\height}}\\faEnvelope\\  \\underline{{{email}}}}} ~ 
    \\href{{{linkedin}}}{{\\raisebox{{-0.2\\height}}\\faLinkedin\\ \\underline{{[linkedin.com/in/](https://linkedin.com/in/){linkedin_user}}}}} ~ 
    \\href{{{github}}}{{\\raisebox{{-0.2\\height}}\\faGithub\\ \\underline{{[github.com/](https://github.com/){github_user}}}}}
    \\vspace{{-8pt}}
\\end{{center}}
""")

    section_order = ['summary', 'education', 'experience', 'projects', 'skills']
    for key in section_order:
        if key in data and data[key]:
            value = data[key]
            section_title = key.upper()
            latex_parts.append(f"\\section{{{{\\fontsize{{9pt}}{{20pt}}\\selectfont \\textbf{{{section_title}}}}}}}")
            latex_parts.append(r"\resumeSubHeadingListStart")

            if key == 'summary':
                latex_parts.append(f"\\resumeItem{{{sanitize_latex(value)}}}")
            elif key == 'education':
                for edu in value:
                    details_list = edu.get('details', [])
                    details = ""
                    if details_list: details = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(line)}}}" for line in details_list]) + "\n\\resumeItemListEnd"
                    latex_parts.append(f"\\resumeSubheading{{{sanitize_latex(edu.get('university'))}}}{{\\textbf{{{sanitize_latex(edu.get('location'))}}}}}{{{sanitize_latex(edu.get('degree'))}}}{{{sanitize_latex(edu.get('dates'))}}}\n{details}")
            elif key == 'experience':
                for exp in value:
                    points_list = exp.get('points', [])
                    points = ""
                    if points_list: points = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(point)}}}" for point in points_list]) + "\n\\resumeItemListEnd"
                    latex_parts.append(f"\\resumeSubheading{{{sanitize_latex(exp.get('company'))}}}{{\\textbf{{{sanitize_latex(exp.get('location'))}}}}}{{{sanitize_latex(exp.get('title'))}}}{{{sanitize_latex(exp.get('dates'))}}}\n{points}")
            elif key == 'projects':
                project_parts = []
                for proj in value:
                    points_list = proj.get('points', [])
                    points = ""
                    if points_list: points = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(point)}}}" for point in points_list]) + "\n\\resumeItemListEnd"
                    project_parts.append(f"\\resumeProjectHeading{{\\textbf{{{sanitize_latex(proj.get('name'))}}}}}{{\\textit{{{sanitize_latex(proj.get('dates'))}}}}}\n{points}")
                latex_parts.append("\\vspace{-6pt}\n".join(project_parts))
            elif key == 'skills' and isinstance(value, dict):
                items = "\\vspace{-7pt}\n".join([f"\\resumeItem{{\\textbf{{{sanitize_latex(cat)}:}} {sanitize_latex(items)}}}" for cat, items in value.items()])
                latex_parts.append(items)
            
            latex_parts.append(r"\resumeSubHeadingListEnd\vspace{-15pt}")
    
    latex_parts.append(r"\end{document}")
    return "\n".join(latex_parts)


def find_unique_filename(base_name):
    counter = 0
    while True:
        if counter == 0: tex_filename = f"{base_name}.tex"
        else: tex_filename = f"{base_name}_{counter}.tex"
        if not os.path.exists(tex_filename):
            return tex_filename, tex_filename.replace('.tex', '.pdf')
        counter += 1

def main():
    print("--- Starting Interactive Resume Builder ---")
    model = setup_api()

    # Step 1: Get user's core information
    user_data = get_user_info()
    
    # Step 2: Get AI-generated creative content
    with open(JOB_DESCRIPTION_PATH, 'r', encoding='utf-8') as f:
        job_description_text = f.read()

    creative_content = generate_creative_content(model, user_data, job_description_text)
    if not creative_content:
        print("❌ Could not generate creative content. Exiting.")
        return
        
    # Step 3: Merge user data and AI content
    final_resume_data = user_data.copy()
    final_resume_data.update(creative_content)
    
    # Step 4: Build and compile the final PDF
    print("\n📄 Building final LaTeX document...")
    final_latex = build_latex_from_data(final_resume_data)
    
    output_latex_file, output_pdf_file = find_unique_filename(BASE_OUTPUT_NAME)

    with open(output_latex_file, 'w', encoding='utf-8') as f:
        f.write(final_latex)

    print(f"📜 Compiling {output_pdf_file}...")
    # Run twice to ensure all references (like page numbers) are correct.
    process = subprocess.run(['pdflatex', '-interaction=nonstopmode', output_latex_file], capture_output=True, text=True, encoding='utf-8')
    process = subprocess.run(['pdflatex', '-interaction=nonstopmode', output_latex_file], capture_output=True, text=True, encoding='utf-8')

    if process.returncode == 0:
        print(f"\n✅ Successfully created {output_pdf_file}!")
        print("🚀 Opening preview...")
        if sys.platform == "win32":
            os.startfile(output_pdf_file)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, output_pdf_file])
    else:
        log_file = os.path.basename(output_latex_file).replace('.tex', '.log')
        print(f"❌ Error: PDF compilation failed. Check the '{log_file}' file for details.")

if __name__ == "__main__":
    main()
