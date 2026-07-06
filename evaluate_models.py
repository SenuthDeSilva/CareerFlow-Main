"""
evaluate_models.py
==================
Evaluation script for 3 NLP model configurations:
  Model A: TF-IDF Only
  Model B: TF-IDF + Word2Vec
  Model C: TF-IDF + Word2Vec + Skill Gap + Random Forest (Full System)

Metrics: Precision@K, Recall@K, F1@K, NDCG@K, MRR, Confusion Matrix

Usage:
    cd D:/Onimta_BlackJack/TopJobScraping
    python evaluate_models.py

Output:
    - Console table with all metrics
    - evaluation_results.json
    - confusion_matrix_plots.png
    - precision_recall_curve.png
"""  # noqa

import os
import sys
import json
import math
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ── Path Setup ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

print("="*65)
print("  JOB RECOMMENDATION SYSTEM — MODEL EVALUATION")
print("  TF-IDF vs TF-IDF+W2V vs BERT")
print("="*65)

# ── Imports ───────────────────────────────────────────────────
from database.db_config import SessionLocal, text as sql_text
from resume_parser.resume_analyzer import analyze_resume
from ml_model.tfidf_matching import build_tfidf_matcher, compute_tfidf_scores
from ml_model.skill_gap import compute_skill_score
from resume_parser.skill_extractor import HARD_SKILLS

print("\n[OK] Imports successful")

# ── Load DB data ──────────────────────────────────────────────
def load_data():
    db = SessionLocal()
    try:
        # Load all resumes
        resumes = db.execute(sql_text("""
            SELECT id, candidate_name, hard_skills, all_skills, raw_text
            FROM resumes
            ORDER BY uploaded_at DESC
        """)).fetchall()

        # Load all jobs
        jobs = db.execute(sql_text("""
            SELECT id, title, company, description, source, job_url
            FROM jobs
            WHERE description IS NOT NULL AND description != ''
            LIMIT 300
        """)).fetchall()

        return resumes, jobs
    finally:
        db.close()

resumes_raw, jobs_raw = load_data()
print(f"[OK] Loaded {len(resumes_raw)} resumes, {len(jobs_raw)} jobs")

if len(resumes_raw) == 0:
    print("\n[ERROR] No resumes found! Upload at least one resume first.")
    sys.exit(1)

if len(jobs_raw) == 0:
    print("\n[ERROR] No jobs found! Run scraper first.")
    sys.exit(1)

# ── Prepare data ──────────────────────────────────────────────
jobs = []
for j in jobs_raw:
    row = dict(j._mapping)
    jobs.append(row)

resumes = []
for r in resumes_raw:
    row = dict(r._mapping)
    try:
        row['hard_skills'] = json.loads(row.get('hard_skills') or '[]')
        row['all_skills']  = json.loads(row.get('all_skills')  or '[]')
    except:
        row['hard_skills'] = []
        row['all_skills']  = []
    resumes.append(row)

print(f"[OK] Using {len(resumes)} resumes for evaluation")

# ── Ground Truth Generation ───────────────────────────────────
def extract_skills_from_text(text: str) -> list:
    """Extract skills from raw text using HARD_SKILLS vocabulary."""
    import re
    text_lower = text.lower()
    found = []
    for skill in HARD_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def generate_ground_truth(resume_skills, job, skill_threshold=0.2):
    """
    Generate ground truth label for a resume-job pair.
    Label = 1 (relevant) if skill overlap >= threshold
    Label = 0 (irrelevant) otherwise

    Using skill overlap as proxy ground truth -
    standard approach when manual labels unavailable.
    """
    job_text   = ((job.get('description') or '') + ' ' + (job.get('title') or ''))
    job_skills = extract_skills_from_text(job_text)

    if not resume_skills or not job_skills:
        return 0

    result = compute_skill_score(resume_skills, job_skills)
    score  = result.get('skill_score', 0)
    return 1 if score >= skill_threshold else 0

# ── Metrics ───────────────────────────────────────────────────
def precision_at_k(y_true, y_scores, k):
    """Precision@K — fraction of top-K that are relevant"""
    if k == 0: return 0.0
    top_k_idx = np.argsort(y_scores)[::-1][:k]
    hits = sum(y_true[i] for i in top_k_idx)
    return hits / k

def recall_at_k(y_true, y_scores, k):
    """Recall@K — fraction of all relevant found in top-K"""
    total_relevant = sum(y_true)
    if total_relevant == 0: return 0.0
    top_k_idx = np.argsort(y_scores)[::-1][:k]
    hits = sum(y_true[i] for i in top_k_idx)
    return hits / total_relevant

def f1_at_k(y_true, y_scores, k):
    """F1@K"""
    p = precision_at_k(y_true, y_scores, k)
    r = recall_at_k(y_true, y_scores, k)
    if p + r == 0: return 0.0
    return 2 * p * r / (p + r)

def ndcg_at_k(y_true, y_scores, k):
    """NDCG@K — ranking quality metric"""
    top_k_idx  = np.argsort(y_scores)[::-1][:k]
    dcg        = sum(y_true[i] / math.log2(j+2) for j, i in enumerate(top_k_idx))
    ideal_hits = sorted(y_true, reverse=True)[:k]
    idcg       = sum(v / math.log2(j+2) for j, v in enumerate(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0

def mrr_score(y_true, y_scores):
    """Mean Reciprocal Rank"""
    ranked = np.argsort(y_scores)[::-1]
    for rank, idx in enumerate(ranked):
        if y_true[idx] == 1:
            return 1.0 / (rank + 1)
    return 0.0

def confusion_matrix_vals(y_true_all, y_pred_all):
    """Binary confusion matrix values"""
    tp = sum(1 for t,p in zip(y_true_all, y_pred_all) if t==1 and p==1)
    fp = sum(1 for t,p in zip(y_true_all, y_pred_all) if t==0 and p==1)
    tn = sum(1 for t,p in zip(y_true_all, y_pred_all) if t==0 and p==0)
    fn = sum(1 for t,p in zip(y_true_all, y_pred_all) if t==1 and p==0)
    return tp, fp, tn, fn

# ── Model A: TF-IDF Only ──────────────────────────────────────
def run_tfidf_only(resume, jobs_list, top_k=20):
    job_texts = [
        (j.get('title','') + ' ' + j.get('description','')).strip()
        for j in jobs_list
    ]
    resume_text = resume.get('raw_text') or ' '.join(resume.get('all_skills', []))

    try:
        vectorizer, job_matrix = build_tfidf_matcher(job_texts)
        scores = compute_tfidf_scores(resume_text, vectorizer, job_matrix)
    except Exception as e:
        scores = np.zeros(len(jobs_list))

    return np.array(scores, dtype=float)

# ── Model B: TF-IDF + Word2Vec ────────────────────────────────
def run_tfidf_w2v(resume, jobs_list, top_k=20):
    from ml_model.word2vec_matching import compute_word2vec_scores

    tfidf_scores = run_tfidf_only(resume, jobs_list, top_k)

    resume_text = resume.get('raw_text') or ' '.join(resume.get('all_skills', []))
    job_texts   = [
        (j.get('title','') + ' ' + j.get('description','')).strip()
        for j in jobs_list
    ]

    try:
        w2v_scores = compute_word2vec_scores(resume_text, job_texts)
        w2v_arr    = np.array(w2v_scores, dtype=float)
    except Exception as e:
        print(f"  [WARN] W2V error: {e}")
        w2v_arr = np.zeros(len(jobs_list))

    # Combine: TF-IDF 60% + Word2Vec 40%
    combined = tfidf_scores * 0.60 + w2v_arr * 0.40
    return combined

# ── Model C: BERT (sentence-transformers) ────────────────────
def run_bert(resume, jobs_list, top_k=20):
    """
    Uses sentence-transformers (BERT-based) for semantic similarity.
    Install: pip install sentence-transformers
    Model: all-MiniLM-L6-v2 (lightweight, fast)
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim
    except ImportError:
        print("  [WARN] sentence-transformers not installed!")
        print("         Run: pip install sentence-transformers")
        print("         Using TF-IDF as fallback for BERT model...")
        return run_tfidf_only(resume, jobs_list, top_k)

    resume_text = resume.get('raw_text') or ' '.join(resume.get('all_skills', []))
    job_texts   = [
        (j.get('title','') + ' ' + j.get('description',''))[:512].strip()
        for j in jobs_list
    ]

    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("    [BERT] Encoding resume...", end=' ', flush=True)
        resume_emb = model.encode([resume_text[:512]])
        print("Encoding jobs...", end=' ', flush=True)
        job_embs   = model.encode(job_texts, batch_size=32, show_progress_bar=False)
        scores     = cos_sim(resume_emb, job_embs)[0]
        print("Done")
        return np.array(scores, dtype=float)
    except Exception as e:
        print(f"\n  [WARN] BERT error: {e}")
        return run_tfidf_only(resume, jobs_list, top_k)

# ── Run Evaluation ────────────────────────────────────────────
K_VALUES = [5, 10, 20]
MODELS   = {
    'TF-IDF Only':       run_tfidf_only,
    'TF-IDF + Word2Vec': run_tfidf_w2v,
    'BERT (MiniLM)':     run_bert,
}

results = {m: {
    'precision': {k: [] for k in K_VALUES},
    'recall':    {k: [] for k in K_VALUES},
    'f1':        {k: [] for k in K_VALUES},
    'ndcg':      {k: [] for k in K_VALUES},
    'mrr':       [],
    'y_true_all':[],
    'y_pred_all':[],
} for m in MODELS}

print(f"\n{'='*65}")
print(f"  Running evaluation on {len(resumes)} resumes × {len(jobs)} jobs")
print(f"{'='*65}\n")

for r_idx, resume in enumerate(resumes):
    name = resume.get('candidate_name') or resume.get('email') or f"Resume #{resume['id']}"
    print(f"[{r_idx+1}/{len(resumes)}] {name} ({len(resume['hard_skills'])} skills)")

    # Generate ground truth labels for this resume
    y_true = np.array([
        generate_ground_truth(resume['hard_skills'], job)
        for job in jobs
    ])
    n_relevant = sum(y_true)
    print(f"       Ground truth: {int(n_relevant)} relevant / {len(jobs)} total jobs")

    if n_relevant == 0:
        print("       [SKIP] No relevant jobs found — skipping this resume")
        continue

    for model_name, model_fn in MODELS.items():
        print(f"       [{model_name}]...", end=' ', flush=True)
        try:
            scores = model_fn(resume, jobs)

            # Metrics at K
            for k in K_VALUES:
                results[model_name]['precision'][k].append(precision_at_k(y_true, scores, k))
                results[model_name]['recall'][k].append(recall_at_k(y_true, scores, k))
                results[model_name]['f1'][k].append(f1_at_k(y_true, scores, k))
                results[model_name]['ndcg'][k].append(ndcg_at_k(y_true, scores, k))

            results[model_name]['mrr'].append(mrr_score(y_true, scores))

            # For confusion matrix — top 20 as predicted positive
            pred_binary = np.zeros(len(jobs), dtype=int)
            top20_idx   = np.argsort(scores)[::-1][:20]
            pred_binary[top20_idx] = 1
            results[model_name]['y_true_all'].extend(y_true.tolist())
            results[model_name]['y_pred_all'].extend(pred_binary.tolist())

            p10 = precision_at_k(y_true, scores, 10)
            f10 = f1_at_k(y_true, scores, 10)
            print(f"P@10={p10:.3f} F1@10={f10:.3f}")

        except Exception as e:
            print(f"ERROR: {e}")

# ── Print Results Table ───────────────────────────────────────
print(f"\n{'='*65}")
print("  FINAL RESULTS — MODEL COMPARISON")
print(f"{'='*65}\n")

summary = {}

for model_name in MODELS:
    r = results[model_name]
    if not r['mrr']:
        print(f"[{model_name}] No valid results\n")
        continue

    print(f"{'─'*65}")
    print(f"  Model: {model_name}")
    print(f"{'─'*65}")

    row = {'model': model_name}

    for k in K_VALUES:
        p  = np.mean(r['precision'][k]) if r['precision'][k] else 0
        rc = np.mean(r['recall'][k])    if r['recall'][k]    else 0
        f  = np.mean(r['f1'][k])        if r['f1'][k]        else 0
        nd = np.mean(r['ndcg'][k])      if r['ndcg'][k]      else 0
        print(f"  @K={k:2d}  Precision={p:.4f}  Recall={rc:.4f}  F1={f:.4f}  NDCG={nd:.4f}")
        row[f'precision@{k}'] = round(p, 4)
        row[f'recall@{k}']    = round(rc, 4)
        row[f'f1@{k}']        = round(f, 4)
        row[f'ndcg@{k}']      = round(nd, 4)

    mrr_val = np.mean(r['mrr'])
    print(f"  MRR   = {mrr_val:.4f}")
    row['mrr'] = round(mrr_val, 4)

    # Confusion matrix
    tp, fp, tn, fn = confusion_matrix_vals(r['y_true_all'], r['y_pred_all'])
    prec   = tp/(tp+fp) if (tp+fp) > 0 else 0
    recall = tp/(tp+fn) if (tp+fn) > 0 else 0
    f1_cm  = 2*prec*recall/(prec+recall) if (prec+recall) > 0 else 0
    print(f"\n  Confusion Matrix (Top-20 as Predicted Positive):")
    print(f"    TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    print(f"    Precision={prec:.4f}  Recall={recall:.4f}  F1={f1_cm:.4f}")
    row.update({'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn,
                'precision_cm': round(prec,4), 'recall_cm': round(recall,4), 'f1_cm': round(f1_cm,4)})
    print()
    summary[model_name] = row

# ── Save JSON ─────────────────────────────────────────────────
out_path = os.path.join(BASE_DIR, 'evaluation_results.json')
with open(out_path, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"[OK] Results saved to {out_path}")

# ── Generate Charts ───────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="darkgrid", palette="muted")
    colors = ['#3b82f6', '#a78bfa', '#34d399']

    # ── Chart 1: Precision@K, Recall@K, F1@K bar chart ───────
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Model Comparison: Precision, Recall & F1 @ K', fontsize=14, fontweight='bold')

    model_names  = list(summary.keys())
    x            = np.arange(len(K_VALUES))
    bar_width    = 0.25

    for metric_idx, (metric, ax, title) in enumerate([
        ('precision', axes[0], 'Precision@K'),
        ('recall',    axes[1], 'Recall@K'),
        ('f1',        axes[2], 'F1@K'),
    ]):
        for i, mname in enumerate(model_names):
            vals = [summary[mname].get(f'{metric}@{k}', 0) for k in K_VALUES]
            bars = ax.bar(x + i*bar_width, vals, bar_width,
                         label=mname, color=colors[i % len(colors)], alpha=0.85)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                        f'{v:.3f}', ha='center', va='bottom', fontsize=8)

        ax.set_xlabel('K value')
        ax.set_ylabel(metric.capitalize())
        ax.set_title(title)
        ax.set_xticks(x + bar_width)
        ax.set_xticklabels([f'K={k}' for k in K_VALUES])
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8)

    plt.tight_layout()
    chart1 = os.path.join(BASE_DIR, 'eval_precision_recall_f1.png')
    plt.savefig(chart1, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Chart saved: eval_precision_recall_f1.png")

    # ── Chart 2: Confusion Matrices ───────────────────────────
    fig, axes = plt.subplots(1, len(model_names), figsize=(5 * len(model_names), 4))
    if len(model_names) == 1:
        axes = [axes]
    fig.suptitle('Confusion Matrices (Top-20 Predictions)', fontsize=13, fontweight='bold')

    for ax, (mname, color) in zip(axes, zip(model_names, colors)):
        r   = summary[mname]
        cm  = np.array([[r['TN'], r['FP']], [r['FN'], r['TP']]])
        sns.heatmap(cm, annot=True, fmt='d', ax=ax,
                    cmap=sns.light_palette(color, as_cmap=True),
                    xticklabels=['Pred Neg', 'Pred Pos'],
                    yticklabels=['Actual Neg', 'Actual Pos'],
                    linewidths=0.5)
        ax.set_title(f'{mname}\nP={r["precision_cm"]:.3f}  R={r["recall_cm"]:.3f}  F1={r["f1_cm"]:.3f}',
                     fontsize=10)

    plt.tight_layout()
    chart2 = os.path.join(BASE_DIR, 'eval_confusion_matrices.png')
    plt.savefig(chart2, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Chart saved: eval_confusion_matrices.png")

    # ── Chart 3: NDCG + MRR comparison ───────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Ranking Quality: NDCG@K and MRR', fontsize=13, fontweight='bold')

    # NDCG@K
    for i, mname in enumerate(model_names):
        ndcg_vals = [summary[mname].get(f'ndcg@{k}', 0) for k in K_VALUES]
        ax1.plot(K_VALUES, ndcg_vals, marker='o', label=mname,
                color=colors[i % len(colors)], linewidth=2, markersize=7)
        for k, v in zip(K_VALUES, ndcg_vals):
            ax1.annotate(f'{v:.3f}', (k, v), textcoords="offset points",
                        xytext=(0, 8), ha='center', fontsize=8)

    ax1.set_xlabel('K')
    ax1.set_ylabel('NDCG@K')
    ax1.set_title('NDCG@K Comparison')
    ax1.set_xticks(K_VALUES)
    ax1.set_ylim(0, 1.05)
    ax1.legend()

    # MRR
    mrr_vals = [summary[m].get('mrr', 0) for m in model_names]
    bars = ax2.bar(model_names, mrr_vals, color=colors[:len(model_names)], alpha=0.85, width=0.5)
    for bar, v in zip(bars, mrr_vals):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')
    ax2.set_ylabel('MRR Score')
    ax2.set_title('Mean Reciprocal Rank (MRR)')
    ax2.set_ylim(0, 1.05)

    plt.tight_layout()
    chart3 = os.path.join(BASE_DIR, 'eval_ndcg_mrr.png')
    plt.savefig(chart3, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Chart saved: eval_ndcg_mrr.png")

    # ── Chart 4: Summary comparison table ────────────────────
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('off')
    cols   = ['Model', 'P@5', 'P@10', 'R@10', 'F1@10', 'NDCG@10', 'MRR']
    rows   = []
    for mname in model_names:
        s = summary[mname]
        rows.append([
            mname,
            f"{s.get('precision@5',0):.4f}",
            f"{s.get('precision@10',0):.4f}",
            f"{s.get('recall@10',0):.4f}",
            f"{s.get('f1@10',0):.4f}",
            f"{s.get('ndcg@10',0):.4f}",
            f"{s.get('mrr',0):.4f}",
        ])
    table = ax.table(cellText=rows, colLabels=cols, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2)
    # Highlight header
    for j in range(len(cols)):
        table[0, j].set_facecolor('#1e293b')
        table[0, j].set_text_props(color='white', fontweight='bold')
    # Highlight best values in each column
    for j in range(1, len(cols)):
        vals = [float(rows[i][j]) for i in range(len(rows))]
        best_i = np.argmax(vals)
        table[best_i+1, j].set_facecolor('#dcfce7')
        table[best_i+1, j].set_text_props(fontweight='bold')

    ax.set_title('Model Comparison Summary Table\n(Green = Best)', fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    chart4 = os.path.join(BASE_DIR, 'eval_summary_table.png')
    plt.savefig(chart4, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Chart saved: eval_summary_table.png")

except ImportError as e:
    print(f"[WARN] matplotlib/seaborn not available: {e}")
    print("       Install: pip install matplotlib seaborn")

print(f"\n{'='*65}")
print("  EVALUATION COMPLETE")
print(f"{'='*65}")
print("\nFiles generated:")
print("  evaluation_results.json      ← All metrics")
print("  eval_precision_recall_f1.png ← P/R/F1 bar chart")
print("  eval_confusion_matrices.png  ← Confusion matrices")
print("  eval_ndcg_mrr.png            ← NDCG + MRR charts")
print("  eval_summary_table.png       ← Summary table")
print("\nUse these figures directly in your research paper!")