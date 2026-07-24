# Reproducibility Findings

`scripts/check_reproducibility.py` - same question run 5x, identical
documents and settings each time. Goal: separate retrieval variation from
generation variation, since Task 17/18 saw inconsistent answers but never
confirmed which layer caused it.

Provider: real Ollama (`qwen3:1.7b`). No LLM judge - results read directly.

## Scenario 1 - Simple Question, One Clear Fact

- Question: "What is the laptop reimbursement limit?"
- One document, one unambiguous answer ($2000 USD)

**Retrieval stable: Yes**
- Same chunk ID, same score (`0.3994395017823609`, exact float match), all 5 runs

**Generation stable: No**
- The fact was correct and identical every run
- Only the sentence wording changed (2 distinct phrasings across 5 runs)
- Cosmetic variation, not a correctness issue

## Scenario 2 - Conflicting Sources

- Question: "How many days does expense reimbursement take to process?"
- 3 documents, each with a genuinely different number (5 days / 10 days / 3-5 days) - mirrors case 4 from the Task 17 groundedness eval

**Retrieval stable: Yes**
- Same 3 chunk IDs, same 3 scores, exact float match, all 5 runs

**Generation stable: No - and substantively, not just cosmetically**

| Run | Answer given |
|---|---|
| 1 | 5 days (picked HR policy) |
| 2 | Leans 5 days, hedges |
| 3 | 3-5 business days (picked Finance policy - contradicts run 1) |
| 4 | 5 days, plus an invented justification not present in the source text |
| 5 | Refuses to pick one, lists both |

- The actual number given to the user changed between runs - not just phrasing
- Run 4 is a separate concern on its own: the model fabricated a
  distinction ("Finance's number is approval, not processing") that the
  source text never states, to justify its pick

## Conclusion

- **Retrieval: fully reproducible in both scenarios.** Chunk IDs and
  scores matched to exact float precision across every run tested.
  TF-IDF behaved exactly as a deterministic algorithm should.
- **Generation: not reproducible in either scenario**, but the severity
  differs:
  - Simple questions: unstable wording, stable substance
  - Conflicting-source questions: unstable substance - same evidence,
    different final answer each time
- **Direct answer to Task 18's open question:** the variation observed
  in Task 17/18 comes from LLM generation, not retrieval. Confirmed with
  evidence (identical scores to full float precision), not assumption.

## Caveat

- Only 2 scenarios tested, 5 runs each. This establishes the *pattern*
  (retrieval solid, generation not) - it doesn't re-verify every case
  from Task 17 individually (e.g. the injection cases weren't re-run
  here). Worth running more scenarios through this same script if a
  specific case needs its own reproducibility proof.