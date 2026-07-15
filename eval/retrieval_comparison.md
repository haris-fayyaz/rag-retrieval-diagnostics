# Retrieval Comparison: TF-IDF vs Semantic (Task 12)

## TF-IDF Results
- **Best Threshold:** 0.10
- **Overall Accuracy:** 85.7% (12/14)
- **Top-1 Accuracy:** 75.0% (6/8 answerable)
- **Recall@3:** 75.0% (6/8 answerable)
- **No-answer Accuracy:** 100.0% (6/6 unanswerable)
- **Avg Answerable Score:** 0.204
- **Avg Unanswerable Score:** 0.000

## Semantic Results
- **Best Threshold:** 0.15 or 0.30 (both 50%)
- **Overall Accuracy:** 50.0% (7/14)
- **Top-1 Accuracy:** 0-12.5% (poor ranking)
- **Recall@3:** 75.0% (same as TF-IDF)
- **No-answer Accuracy:** 0-16.7% (poor rejection)
- **Avg Answerable Score:** 0.485
- **Avg Unanswerable Score:** 0.427

## Key Observations
**Where TF-IDF performs better:**
- Top-1 ranking (75% vs 0-12.5%)
- No-answer rejection (100% vs 0-16.7%)
- Overall accuracy (85.7% vs 50%)
- Clear score separation (answerable: 0.204, unanswerable: 0.000)

**Where semantic performs better:**
- Multi-document recall (equal at 75%, but semantic finds both docs in top-3)
- Paraphrased question understanding (Q9: "work laptop" correctly identified)

**Where both fail:**
- Multi-document ranking (Q10: returns only IT, misses Finance)
- Vague question rejection (both struggle without perfect thresholding)

## What Changed from Task 11

**Task 11 finding:** TF-IDF 85.7% vs Semantic 50%

**Task 12 finding:** Still same, but now we understand why:
- **Not a threshold problem** — Semantic's issue is ranking + rejection, not just thresholding
- **Recall@3 reveals truth** — Semantic retrieves relevant docs (75% recall) but ranks them wrong (0% top-1)
- **Score distribution mismatch** — Semantic's answerable/unanswerable scores overlap (0.485 vs 0.427), making thresholding impossible

## Conclusion
**TF-IDF is safer for production right now:**
- Superior ranking (Top-1: 75% vs 12.5%)
- Superior rejection behavior (No-answer: 100% vs 16.7%)
- Clear score separation enables reliable thresholding
- Simpler and more interpretable
 
**Semantic needs improvement for this domain:**
- Requires fine-tuning on domain-specific documents
- Needs reranking stage to fix Top-1 accuracy
- Needs score calibration for better rejection
- Or: use semantic for retrieval + TF-IDF for ranking (hybrid approach)

**Next steps:**
- Stay with TF-IDF baseline for now
- Explore hybrid retrieval (semantic recall + TF-IDF ranking) if needed
- Consider fine-tuning semantic model on financial/HR/IT documents