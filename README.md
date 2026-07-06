# CAREERFLOW
### AI-Powered Real-Time Entry-Level and Undergraduate Job Recommendation System

CAREERFLOW is an AI-powered job recommendation system developed as a Final Year Research Project. The system helps undergraduate students and entry-level IT professionals discover suitable job opportunities by analyzing their resumes, identifying skill gaps, and recommending relevant jobs using Machine Learning and Explainable AI.

---

## Features

- Resume Upload (PDF, DOCX, TXT)
- Resume Parsing and Skill Extraction
- IT Role Classification using Linear SVM
- Real-Time Job Scraping
  - TopJobs.lk
  - Rooster.jobs
- Hybrid Job Recommendation Engine
  - TF-IDF Similarity
  - Word2Vec Semantic Similarity
  - Skill Gap Analysis
  - Machine Learning Ranking
- Skill Gap Analysis
- Explainable AI
  - SHAP
  - LIME
- Interactive Analytics Dashboard
- FastAPI REST API
- PostgreSQL Database

---

## System Architecture

```
Resume
      │
      ▼
Resume Parser
      │
      ▼
Skill Extraction
      │
      ▼
IT Role Classification (Linear SVM)
      │
      ▼
Real-Time Job Scraping
      │
      ▼
Hybrid Recommendation Engine
      │
      ▼
Skill Gap Analysis
      │
      ▼
SHAP + LIME Explainability
      │
      ▼
React Dashboard
```

---

## Technology Stack

### Frontend

- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI

### Machine Learning

- Scikit-learn
- Linear SVM
- TF-IDF
- Word2Vec
- SMOTE

### Explainable AI

- SHAP
- LIME

### Database

- PostgreSQL
- SQLAlchemy

### Web Scraping

- Selenium
- BeautifulSoup

---

## Machine Learning Pipeline

1. Resume Upload
2. Resume Parsing
3. Skill Extraction
4. Resume Preprocessing
5. TF-IDF Feature Generation
6. IT Role Classification
7. Live Job Collection
8. Hybrid Recommendation
9. Skill Gap Analysis
10. SHAP & LIME Explanation

---

## Project Structure

```
CareerFlow
│
├── api.py
├── main.py
├── requirements.txt
│
├── database/
├── ml_model/
├── pipeline/
├── resume_parser/
├── scraping/
├── saved_models/
├── xai/
│
├── job-recommendation-ui/
│
└── Dataset_jotpars.csv
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/SenuthDeSilva/CareerFlow-Main.git
```

Move into the project

```bash
cd CareerFlow-Main
```

Create virtual environment

```bash
python -m venv venv
```

Activate environment

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Backend

```bash
python api.py
```

or

```bash
uvicorn api:app --reload
```

---

## Running the Frontend

```bash
cd job-recommendation-ui

npm install

npm start
```

---

## Machine Learning Models

The system compares multiple machine learning algorithms before selecting the final model.

- Logistic Regression
- Decision Tree
- Linear SVM ✅ (Selected)
- k-NN
- Multinomial Naive Bayes
- Random Forest
- Gradient Boosting

The selected Linear SVM model achieved approximately **81.5% classification accuracy** on the evaluation dataset.

---

## Explainable AI

CAREERFLOW improves transparency by integrating:

- SHAP (Global feature importance)
- LIME (Local prediction explanations)

Users can understand:

- Why a job was recommended
- Which resume skills influenced the recommendation
- Missing skills required for target roles

---

## Research Contributions

- AI-powered career recommendation system for Sri Lankan undergraduate IT students.
- Real-time job scraping from multiple recruitment platforms.
- Hybrid recommendation engine combining semantic similarity and skill gap analysis.
- Explainable AI integration using SHAP and LIME.
- Automatic IT role prediction using Machine Learning.

---

## Future Improvements

- LinkedIn integration
- Learning resource recommendations
- Interview preparation assistant
- Sentence-BERT embeddings
- Personalized career roadmap
- Mobile application

---

## Author

**Senuth De Silva**

BSc (Hons) Computer Science

Informatics Institute of Technology (IIT)

University of Westminster

---

## License

This project was developed for academic and research purposes.
