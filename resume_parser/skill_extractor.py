"""
skill_extractor.py
==================
Extracts hard skills and soft skills from resume text.
FIXED: Expanded soft skills database to cover more resume patterns.
"""

import re


# ── Hard Skills Database ──────────────────────────────────────
HARD_SKILLS = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "go", "golang", "rust", "scala",
    "r", "matlab", "perl", "dart", "flutter",

    # Web Development
    "html", "css", "react", "reactjs", "angular", "vue", "vuejs",
    "nodejs", "node.js", "express", "django", "flask", "fastapi",
    "spring", "spring boot", "laravel", "asp.net", "next.js", "nuxt",
    "tailwind", "bootstrap", "jquery", "sass", "webpack", "socket.io",
    "jwt", "rest api", "graphql", "soap",

    # Databases
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis",
    "elasticsearch", "cassandra", "oracle", "dynamodb", "firebase",
    "mariadb", "neo4j", "supabase", "chromadb", "timescaledb",

    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "terraform", "ansible", "jenkins", "ci/cd", "github actions",
    "linux", "bash", "shell scripting", "nginx", "apache",
    "google cloud", "firebase", "streamlit",

    # AI / ML / Data Science
    "machine learning", "deep learning", "natural language processing",
    "nlp", "computer vision", "tensorflow", "pytorch", "keras",
    "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn",
    "huggingface", "bert", "openai", "langchain", "llm",
    "data science", "data analysis", "data engineering",
    "power bi", "tableau", "excel", "spark", "hadoop",
    "yolo", "yolov8", "opencv", "roboflow", "kaggle",
    "rag", "prompt engineering", "generative ai", "gemini",
    "ollama", "llama", "tf-idf", "feature engineering",
    "model deployment", "transformers",

    # Mobile
    "android", "ios", "react native", "flutter", "swift", "kotlin",
    "xamarin",

    # Tools & Version Control
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "figma", "photoshop", "illustrator", "postman", "swagger",
    "vs code", "intellij", "eclipse", "netbeans", "codeblocks",
    "atmel studio", "proteus", "blender", "canva", "adobe photoshop",
    "mssql", "ms sql", "sql server",

    # Testing
    "selenium", "jest", "pytest", "junit", "cypress", "playwright",
    "unit testing", "integration testing", "tdd",

    # Networking & Security
    "networking", "cybersecurity", "ethical hacking", "penetration testing",
    "firewalls", "vpn", "tcp/ip",

    # Methodologies
    "agile", "scrum", "kanban", "devops", "microservices",
    "oop", "mvc", "solid", "design patterns", "spring aop",
    "jpa", "hibernate",

    # Other Technical
    "blockchain", "iot", "embedded systems", "arduino", "raspberry pi",
    "sap", "erp", "salesforce", "wordpress", "shopify",
    "ocr", "license plate recognition", "recharts", "spring aop",
}

# ── Soft Skills Database — EXPANDED ──────────────────────────
SOFT_SKILLS = {
    # Core
    "communication", "teamwork", "leadership", "problem solving",
    "critical thinking", "time management", "adaptability", "creativity",
    "collaboration", "attention to detail", "project management",
    "analytical skills", "presentation", "negotiation", "mentoring",
    "decision making", "conflict resolution", "self motivated",
    "multitasking", "organizational skills", "interpersonal skills",
    "customer service", "research", "documentation", "planning",

    # Extra — commonly found in IT resumes
    "fast learner", "quick learner", "self-motivated", "proactive",
    "innovative", "passionate", "dedicated", "motivated",
    "team player", "detail oriented", "result oriented",
    "analytical thinking", "logical thinking", "strategic thinking",
    "business analysis", "requirements gathering", "stakeholder",
    "use case", "user story", "uml", "agile methodologies",
    "verbal communication", "written communication",
    "problem-solving", "self-learning", "continuous learning",
    "work under pressure", "deadline", "initiative",
}


def load_spacy_model():
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✓  spaCy model loaded (en_core_web_sm)")
        return nlp
    except ImportError:
        print("⚠  spaCy not installed.")
        return None
    except OSError:
        print("⚠  spaCy model not found. Run: python -m spacy download en_core_web_sm")
        return None


def extract_skills_by_keyword(text: str) -> dict:
    text_lower  = text.lower()
    found_hard  = set()
    found_soft  = set()

    for skill in HARD_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_hard.add(skill)

    for skill in SOFT_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_soft.add(skill)

    return {
        "hard_skills": sorted(list(found_hard)),
        "soft_skills": sorted(list(found_soft)),
    }


def extract_skills_by_spacy(text: str, nlp) -> list:
    doc      = nlp(text[:100000])
    entities = []
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART"]:
            val = ent.text.strip().lower()
            if len(val) > 1 and val in HARD_SKILLS:
                entities.append(val)
    return list(set(entities))


def extract_skills(text: str, sections: dict = None) -> dict:
    print("\n🔍  Extracting skills...")

    skills_text = text
    if sections and sections.get("skills"):
        skills_text = sections["skills"] + " " + text

    # Primary: keyword matching
    keyword_results = extract_skills_by_keyword(skills_text)
    hard_skills     = set(keyword_results["hard_skills"])
    soft_skills     = set(keyword_results["soft_skills"])

    # Supplementary: spaCy NER
    nlp = load_spacy_model()
    if nlp:
        spacy_skills = extract_skills_by_spacy(skills_text, nlp)
        hard_skills.update(spacy_skills)

    hard_list  = sorted(list(hard_skills))
    soft_list  = sorted(list(soft_skills))
    all_skills = hard_list + soft_list

    print(f"✓  Hard skills found : {len(hard_list)}")
    print(f"✓  Soft skills found : {len(soft_list)}")
    print(f"✓  Total skills      : {len(all_skills)}")
    print(f"\n   Hard: {', '.join(hard_list[:10])}{'...' if len(hard_list)>10 else ''}")
    print(f"   Soft: {', '.join(soft_list[:5])}{'...' if len(soft_list)>5 else ''}")

    return {
        "hard_skills":  hard_list,
        "soft_skills":  soft_list,
        "all_skills":   all_skills,
        "skills_count": len(all_skills),
    }