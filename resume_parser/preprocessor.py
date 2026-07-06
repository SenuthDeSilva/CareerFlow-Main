"""
preprocessor.py
===============
Cleans and preprocesses raw resume text for NLP processing.
FIXED:
    - Name extraction: searches broader lines + email-based fallback
    - Experience: detects date ranges like "2023 - Present"
    - Better section splitting
"""

import re
from datetime import datetime


SECTION_PATTERNS = {
    "skills":       r"(skills?|technical skills?|core competencies|technologies|expertise|tools)",
    "experience":   r"(experience|work experience|employment|career history|professional experience)",
    "education":    r"(education|academic|qualifications?|degrees?|certifications?)",
    "projects":     r"(projects?|personal projects?|academic projects?|portfolio)",
    "summary":      r"(summary|objective|profile|about me|professional summary)",
    "languages":    r"(languages?|programming languages?)",
    "achievements": r"(achievements?|awards?|honors?|accomplishments?)",
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.encode("ascii", errors="ignore").decode()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\.\,\-\+\#\@\/\(\)]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_email(text: str) -> str:
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    match   = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    pattern = r"(\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
    match   = re.search(pattern, text)
    return match.group(0).strip() if match else ""


def extract_name(text: str) -> str:
    """
    Name extraction — handles PDF layouts where text runs together.
    1. Find ALL-CAPS name line (e.g. "HARINDI NIKESHALA")
    2. Search newline-separated lines for 2-3 word name
    3. Fallback: email prefix
    """
    # Skip words that are definitely not names
    SKIP = {
        "professional", "summary", "objective", "profile", "education",
        "experience", "skills", "contact", "references", "projects",
        "technical", "web", "development", "html", "css", "javascript",
        "intern", "software", "engineer", "manager", "developer",
        "basic", "languages", "database", "frameworks", "operating",
        "systems", "certifications", "achievements", "interests",
        "hobbies", "volunteering", "leadership", "communication",
    }

    # Strategy 1: FIRST ALL-CAPS line with 2-3 words = name
    # Skip job title words like INTERN, ENGINEER, SOFTWARE etc.
    JOB_TITLE_WORDS = {
        "intern", "engineer", "developer", "manager", "analyst", "designer",
        "officer", "executive", "specialist", "consultant", "coordinator",
        "software", "senior", "junior", "lead", "head", "director",
        "marketing", "finance", "accounting", "sales", "support",
        "instructor", "trainee", "associate", "assistant", "web",
        "development", "html", "css", "java", "python", "data",
    }
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(w.isupper() and w.replace("-","").isalpha() and len(w) > 1 for w in words):
                if not any(w.lower() in JOB_TITLE_WORDS for w in words):
                    return line.title()  # "HARINDI NIKESHALA" → "Harindi Nikeshala"

    # Strategy 2: newline-separated lines — Title Case, not job title
    for line in text.split("\n")[:20]:
        line = line.strip()
        words = line.split()
        if 2 <= len(words) <= 3:
            if all(w.replace("-","").isalpha() for w in words):
                if not any(w.lower() in SKIP for w in words):
                    if not any(w.lower() in JOB_TITLE_WORDS for w in words):
                        if all(w[0].isupper() for w in words):
                            return line.title()

    # Strategy 3: spaced tokens fallback
    raw_lines = [l.strip() for l in text.replace("\n", "  ").split("  ") if l.strip()]
    for line in raw_lines[:15]:
        words = line.split()
        if 2 <= len(words) <= 3:
            if all(w.replace("-","").replace(".","").isalpha() for w in words):
                if not any(w.lower() in SKIP for w in words):
                    if not any(w.lower() in JOB_TITLE_WORDS for w in words):
                        if all(w[0].isupper() for w in words):
                            return line.title()

    # Strategy 4: fallback from email
    email = extract_email(text)
    if email:
        prefix = email.split("@")[0]
        prefix = re.sub(r"\d+", "", prefix)
        parts  = re.split(r"[._]", prefix)
        parts  = [p.capitalize() for p in parts if len(p) > 1]
        if 2 <= len(parts) <= 3:
            return " ".join(parts)

    return ""


def extract_years_of_experience(text: str) -> int:
    """
    Experience extraction — Student CV safe.
    1. Explicit "X years experience" patterns
    2. Date ranges with Present: "2022 - Present" (only WORK experience sections)
    3. Cap: student CVs max 6 years, others max 30
    """
    current_year = datetime.now().year
    text_lower   = text.lower()

    # Strategy 1: explicit mention — most reliable
    explicit_patterns = [
        r"(\d+)\+?\s*years?\s*(of)?\s*experience",
        r"experience\s*of\s*(\d+)\+?\s*years?",
        r"(\d+)\+?\s*years?\s*(in|of)\s*(the\s*)?(industry|field|software|it)",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            val = int(match.group(1))
            if 0 < val <= 30:
                return val

    # Strategy 2: "YYYY - Present" in WORK EXPERIENCE section only
    # Extract work section to avoid education dates polluting result
    work_section = ""
    work_markers = ["experience", "employment", "work history", "career"]
    edu_markers  = ["education", "academic", "qualification", "degree", "university",
                    "school", "college", "institute", "gpa", "grade"]

    lines = text.split("\n")
    in_work = False
    for line in lines:
        ll = line.lower().strip()
        if any(m in ll for m in work_markers) and len(ll) < 30:
            in_work = True
        elif any(m in ll for m in edu_markers) and len(ll) < 30:
            in_work = False
        if in_work:
            work_section += line + " "

    # Search in work section for Present patterns
    search_text = work_section if work_section.strip() else text

    present_pattern = r"(20\d{2})\s*[-–]\s*(present|current|now)"
    present_matches = re.findall(present_pattern, search_text.lower())
    if present_matches:
        start_years = [int(m[0]) for m in present_matches]
        # Only use years that are reasonable work start years (≥ 2015)
        valid_starts = [y for y in start_years if y >= 2015]
        if valid_starts:
            oldest    = min(valid_starts)
            estimated = current_year - oldest
            if 0 < estimated <= 10:   # cap at 10 for safety
                return estimated

    # Strategy 3: date range spans e.g. "2022 – 2024" (work only)
    range_pattern = r"(20\d{2})\s*[-–]\s*(20\d{2})"
    range_matches = re.findall(range_pattern, search_text)
    if range_matches:
        total_months = 0
        for start, end in range_matches:
            s, e = int(start), int(end)
            if 2015 <= s <= current_year and s < e <= current_year:
                total_months += (e - s) * 12
        if total_months > 0:
            years = round(total_months / 12)
            if 0 < years <= 10:
                return years

    # Strategy 4: last resort — find years >= 2018 only (recent grads)
    all_years = re.findall(r"\b(20\d{2})\b", text)
    if all_years:
        years = [int(y) for y in all_years if int(y) >= 2018]
        if years:
            oldest    = min(years)
            estimated = current_year - oldest
            if 0 < estimated <= 8:    # student cap
                return estimated

    return 0


def extract_sections(text: str) -> dict:
    sections    = {key: "" for key in SECTION_PATTERNS}
    sections["other"] = ""
    lines       = text.split("\n")
    current_sec = "other"
    buffer      = []

    for line in lines:
        line_lower = line.lower().strip()
        matched    = False
        for sec_name, pattern in SECTION_PATTERNS.items():
            if re.search(pattern, line_lower) and len(line.strip()) < 50:
                sections[current_sec] += " ".join(buffer) + " "
                buffer      = []
                current_sec = sec_name
                matched     = True
                break
        if not matched:
            buffer.append(line)

    sections[current_sec] += " ".join(buffer)
    sections = {k: clean_text(v) for k, v in sections.items()}
    return sections


def preprocess(raw_text: str) -> dict:
    cleaned  = clean_text(raw_text)
    sections = extract_sections(cleaned)

    result = {
        "raw_text":         cleaned,
        "name":             extract_name(raw_text),   # use raw for better name detection
        "email":            extract_email(cleaned),
        "phone":            extract_phone(cleaned),
        "years_experience": extract_years_of_experience(raw_text),
        "sections":         sections,
    }

    print(f"✓  Preprocessed resume")
    print(f"   Name    : {result['name'] or 'Not found'}")
    print(f"   Email   : {result['email'] or 'Not found'}")
    print(f"   Phone   : {result['phone'] or 'Not found'}")
    print(f"   Exp     : {result['years_experience']} years")

    return result