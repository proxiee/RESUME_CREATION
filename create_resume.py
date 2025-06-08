import google.generativeai as genai
import json
import os
import subprocess
import sys
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
BASE_RESUME_PATH = "resume_data.json"
LATEX_TEMPLATE_PATH = "template.tex"
if len(sys.argv) < 2:
    print("Usage: python create_resume.py <path_to_job_description.txt>")
    sys.exit(1)
JOB_DESCRIPTION_PATH = sys.argv[1]
BASE_OUTPUT_NAME = "tailored_resume"

def sanitize_latex(text):
    """Sanitizes text to be safe for LaTeX."""
    if not isinstance(text, str):
        return text
    text = text.replace('&', r'\&')
    text = text.replace('%', r'\%')
    text = text.replace('$', r'\$')
    text = text.replace('#', r'\#')
    text = text.replace('_', r'\_')
    text = text.replace('{', r'\{')
    text = text.replace('}', r'\}')
    text = text.replace('~', r'\textasciitilde{}')
    text = text.replace('^', r'\textasciicircum{}')
    return text

def setup_api():
    """Configures the Gemini API and handles missing API key."""
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found.")
        print("Please ensure you have a .env file with the line: GEMINI_API_KEY=\"your-key\"")
        sys.exit(1)
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        sys.exit(1)

def generate_tailored_content(model, base_resume, job_desc):
    """Sends a prompt to Gemini and gets tailored resume content back."""
    print("🤖 Calling Gemini API to tailor resume...")

    sections_to_tailor = {
        "summary": base_resume["summary"],
        "experience": base_resume["experience"],
        "projects": base_resume["projects"]
    }

    prompt = f"""
    You are an expert resume writer specializing in AI and software engineering roles. Your task is to take a base resume's summary, experience, and projects, and a target job description, then rewrite those sections to be perfectly tailored for the job.

    **Instructions:**
    1.  Rewrite the 'summary' to be a powerful, 2-3 sentence introduction that mirrors the language of the job description and highlights the most relevant skills.
    2.  For each job in 'experience', rewrite the 'points' to use strong action verbs. Weave in keywords from the job description. Invent specific, quantifiable metrics that align with the job description (e.g., improved performance by 15%, reduced latency by 30ms, handled X requests per second).
    3.  **Re-imagine the 'projects' section.** You have creative freedom. You can either heavily rewrite the existing projects OR **replace them entirely with 1-3 new, highly relevant, and plausible project descriptions** that make the candidate a perfect match for the job. For each new project, create a compelling `name`, realistic `dates`, and detailed `points` with strong, quantifiable metrics.
    4.  **Maintain a similar length.** For each bullet point you rewrite, try to keep the new text around the same character length as the original point to preserve the resume's layout. A little longer or shorter is fine, but avoid making a one-line point into a three-line paragraph.
    5.  You MUST return ONLY a single, valid JSON object containing the updated 'summary', 'experience', and 'projects' sections. Maintain the original JSON structure for these keys perfectly, even if the content of the 'projects' array is entirely new. Do not add any text before or after the JSON object.

    **JSON to tailor:**
    ```json
    {json.dumps(sections_to_tailor, indent=2)}
    ```

    **Target Job Description:**
    ```
    {job_desc}
    ```

    **Return ONLY the tailored JSON object.**
    """

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error calling Gemini API or parsing JSON: {e}")
        print("--- Gemini's Raw Response ---")
        print(response.text)
        return None

def build_latex_from_data(template_content, data):
    """Populates the LaTeX template with the final data."""
    
    populated_template = template_content.replace("{%%-NAME-%%}", sanitize_latex(data['name']))
    populated_template = populated_template.replace("{%%-PHONE-%%}", sanitize_latex(data['phone']))
    populated_template = populated_template.replace("{%%-EMAIL-%%}", data['email'])
    populated_template = populated_template.replace("{%%-LINKEDIN-%%}", data['linkedin']) 
    populated_template = populated_template.replace("{%%-GITHUB-%%}", data['github']) 
    populated_template = populated_template.replace("{%%-SUMMARY-%%}", sanitize_latex(data['summary']))

    # FIX: Loop through the list of education entries
    edu_blocks = []
    for edu in data['education']:
        edu_details_list = []
        for line in edu['details']:
            if ':' in line:
                parts = line.split(':', 1)
                sanitized_title = sanitize_latex(parts[0])
                sanitized_content = sanitize_latex(parts[1])
                edu_details_list.append(f"\\resumeItem{{\\textbf{{{sanitized_title}:}}{sanitized_content}}}")
            else:
                edu_details_list.append(f"\\resumeItem{{{sanitize_latex(line)}}}")
        edu_details = "\\resumeItemListStart\n" + "\n".join(edu_details_list) + "\n\\resumeItemListEnd"
        edu_blocks.append(f"\\resumeSubheading{{{sanitize_latex(edu['university'])}}}{{\\textbf{{{sanitize_latex(edu['location'])}}}}}{{{sanitize_latex(edu['degree'])}}}{{{sanitize_latex(edu['dates'])}}}\n{edu_details}")
    
    populated_template = populated_template.replace("%%%-EDUCATION_BLOCK-%%%", "\\resumeSubHeadingListStart\n" + "\n".join(edu_blocks) + "\n\\resumeSubHeadingListEnd")

    exp_blocks = []
    for exp in data['experience']:
        points_latex = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(point)}}}" for point in exp['points']]) + "\n\\resumeItemListEnd"
        exp_blocks.append(f"\\resumeSubheading{{{sanitize_latex(exp['company'])}}}{{\\textbf{{{sanitize_latex(exp['location'])}}}}}{{{sanitize_latex(exp['title'])}}}{{{sanitize_latex(exp['dates'])}}}\n{points_latex}")
    populated_template = populated_template.replace("%%%-EXPERIENCE_BLOCK-%%%", "\\resumeSubHeadingListStart\n" + "\n".join(exp_blocks) + "\n\\resumeSubHeadingListEnd")

    proj_blocks = []
    for proj in data['projects']:
        points_latex = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(point)}}}" for point in proj['points']]) + "\n\\resumeItemListEnd"
        proj_blocks.append(f"\\resumeProjectHeading{{\\textbf{{{sanitize_latex(proj['name'])}}}}}{{\\textit{{{sanitize_latex(proj['dates'])}}}}}\n{points_latex}")
    populated_template = populated_template.replace("%%%-PROJECTS_BLOCK-%%%", "\\resumeSubHeadingListStart\n" + "\\vspace{-6pt}\n".join(proj_blocks) + "\n\\resumeSubHeadingListEnd")
    
    act_blocks = []
    for act in data['activities']:
        roles_latex = "\\resumeItemListStart\n" + "\n".join([f"\\resumeItem{{{sanitize_latex(role['title'])}}} \\hfill \\textit{{{sanitize_latex(role['dates'])}}}" for role in act['roles']]) + "\n\\resumeItemListEnd"
        act_blocks.append(f"\\resumeSubheading{{{sanitize_latex(act['organization'])}}}{{\\textbf{{{sanitize_latex(act['location'])}}}}}{{}}{{}}\n\\vspace{{-17pt}}\n{roles_latex}")
    populated_template = populated_template.replace("%%%-ACTIVITIES_BLOCK-%%%", "\\resumeSubHeadingListStart\n" + "\n".join(act_blocks) + "\n\\resumeSubHeadingListEnd")

    skills_latex = "\\vspace{-7pt}\n".join([f"\\resumeItem{{\\textbf{{{sanitize_latex(category)}:}} {sanitize_latex(skills)}}}" for category, skills in data['skills'].items()])
    populated_template = populated_template.replace("%%%-SKILLS_BLOCK-%%%", "\\resumeSubHeadingListStart\n" + skills_latex + "\n\\resumeSubHeadingListEnd")
    
    return populated_template

def find_unique_filename(base_name):
    """Finds a unique filename by appending a number if necessary."""
    counter = 0
    while True:
        if counter == 0:
            tex_filename = f"{base_name}.tex"
        else:
            tex_filename = f"{base_name}_{counter}.tex"
        
        if not os.path.exists(tex_filename):
            pdf_filename = tex_filename.replace('.tex', '.pdf')
            return tex_filename, pdf_filename
        
        counter += 1

def main():
    """Main function to run the resume generation process."""
    print("--- Starting Resume Tailor ---")
    
    model = setup_api()

    with open(BASE_RESUME_PATH, 'r', encoding='utf-8') as f:
        base_resume_data = json.load(f)
    with open(JOB_DESCRIPTION_PATH, 'r', encoding='utf-8') as f:
        job_description_text = f.read()

    tailored_sections = generate_tailored_content(model, base_resume_data, job_description_text)
    if not tailored_sections:
        print("❌ Exiting due to API error.")
        return

    final_resume_data = base_resume_data.copy()
    final_resume_data.update(tailored_sections)
    
    print("📄 Populating LaTeX template...")
    with open(LATEX_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_string = f.read()

    final_latex = build_latex_from_data(template_string, final_resume_data)

    output_latex_file, output_pdf_file = find_unique_filename(BASE_OUTPUT_NAME)

    with open(output_latex_file, 'w', encoding='utf-8') as f:
        f.write(final_latex)

    print(f"📜 Compiling {output_pdf_file}... (This may take a moment)")
    for i in range(2): 
        process = subprocess.run(['pdflatex', '-interaction=nonstopmode', output_latex_file], capture_output=True, text=True, encoding='utf-8')

    if process.returncode == 0:
        print(f"✅ Successfully created {output_pdf_file}")
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
