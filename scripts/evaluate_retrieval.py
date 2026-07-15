import json
from eval.evaluator import RetrieverEvaluator

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def evaluate_retrieval(min_score=0.0, mode="tfidf", top_k=3):
    """Run retrieval evaluation using RetrieverEvaluator."""
    
    # Load data
    docs_data = load_json("eval/sample_documents.json")
    questions_data = load_json("eval/eval_questions.json")
    
    print("Loading documents...")
    print(f"Loaded {len(docs_data['documents'])} documents\n")
    
    # Create evaluator and run
    evaluator = RetrieverEvaluator(min_score=min_score, mode=mode, top_k=top_k)
    result = evaluator.evaluate(questions_data, docs_data)
    
    # Print results
    result.print_summary()

if __name__ == "__main__":
    import sys
    mode = "tfidf"
    min_score = 0.0
    top_k = 3
    
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    if "--min-score" in sys.argv:
        min_score = float(sys.argv[sys.argv.index("--min-score") + 1])
    if "--top-k" in sys.argv:
        top_k = int(sys.argv[sys.argv.index("--top-k") + 1])
    
    evaluate_retrieval(min_score=min_score, mode=mode, top_k=top_k)