# Retrieval Comparison: TF-IDF vs Semantic

## TF-IDF Results

- **Best Accuracy:** 85.7% (min_score = 0.10)
- **Passed:** 12/14
- **Failed cases:**
  - Q10: Multi-document question (expected Finance + IT, got None)
  - Q12: "payment approvals" (expected Finance, got None)

## Semantic Results

- **Best Accuracy:** 50.0% (min_score = 0.15 or 0.30)
- **Passed:** 7/14
- **Failed cases:**
  - Q3: Meals (returned IT instead of Finance)
  - Q4, Q5, Q6: Vague questions (returned results instead of None)
  - Q7: Bitcoin vacation (returned HR instead of None)
  - Q10: Multi-doc (returned only IT, not Finance)
  - Q12: Access permission (returned None instead of IT)
  - Q14: Vacation + equipment (returned IT instead of None)

## Observations

**Where TF-IDF performs better:**
- Exact keyword matching (Q1, Q2, Q3, Q8)
- Rejection of vague questions with thresholding
- Questions with specific terminology

**Where semantic performs better:**
- Paraphrased questions (Q9: "work laptop" understood)
- Multi-document questions (Q10: got IT correctly)
- Access/security questions (Q13: correctly identifies IT)

**Where both fail:**
- Vague questions need better rejection logic
- Multi-document questions need ranking both docs
- Domain-specific overlap (finance vs IT reimbursement)

**Recommendation:**
TF-IDF is safer for this project right now (85.7% vs 50%). Semantic needs:
- Larger training dataset
- Domain-specific fine-tuning
- Better threshold calibration
- Multi-document ranking support