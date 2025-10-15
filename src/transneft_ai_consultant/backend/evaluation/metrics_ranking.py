import math

def dcg_at_k(relevances, k):
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        denom = math.log2(i + 2)  # i starts at 0
        dcg += rel / denom
    return dcg

def ndcg_at_k(true_set, retrieved_list, k):
    # binary relevance: 1 if in true_set else 0
    rels = [1 if doc in true_set else 0 for doc in retrieved_list[:k]]
    dcg = dcg_at_k(rels, k)
    # ideal DCG = all relevant at top
    ideal_rels = sorted(rels, reverse=True)
    idcg = dcg_at_k(ideal_rels, k)
    return dcg / idcg if idcg > 0 else 0.0

def reciprocal_rank(true_set, retrieved_list, k):
    for i, doc in enumerate(retrieved_list[:k]):
        if doc in true_set:
            return 1.0 / (i + 1)
    return 0.0

def mrr_at_k(qid_to_truth, qid_to_retrieved, k=10):
    s = 0.0
    n = 0
    for qid, truth in qid_to_truth.items():
        retrieved = qid_to_retrieved[qid]
        s += reciprocal_rank(truth, retrieved, k)
        n += 1
    return s / n if n else 0.0

def average_precision(true_set, retrieved_list, k=100):
    hits = 0.0
    sum_prec = 0.0
    for i, doc in enumerate(retrieved_list[:k]):
        if doc in true_set:
            hits += 1.0
            sum_prec += hits / (i + 1.0)
    return sum_prec / hits if hits > 0 else 0.0

def map_at_k(qid_to_truth, qid_to_retrieved, k=100):
    s = 0.0
    n = 0
    for qid, truth in qid_to_truth.items():
        retrieved = qid_to_retrieved[qid]
        s += average_precision(truth, retrieved, k)
        n += 1
    return s / n if n else 0.0

def ndcg_mean_at_k(qid_to_truth, qid_to_retrieved, k=10):
    s = 0.0
    n = 0
    for qid, truth in qid_to_truth.items():
        retrieved = qid_to_retrieved[qid]
        s += ndcg_at_k(truth, retrieved, k)
        n += 1
    return s / n if n else 0.0