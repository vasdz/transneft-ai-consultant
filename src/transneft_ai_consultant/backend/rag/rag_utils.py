def build_rag_prompt(question: str, contexts: list, tokenizer, n_ctx_limit: int = 4096, reserved_for_answer: int = 512):
    """
    contexts: list of dicts [{'id':..., 'text':..., 'score':...}, ...] sorted by score desc
    tokenizer: function / object with .encode(text) -> list of token ids or count_tokens(text)
    """
    max_for_context = n_ctx_limit - reserved_for_answer
    selected = []
    total = 0
    for ctx in contexts:
        tcount = tokenizer.count_tokens(ctx['text']) if hasattr(tokenizer, "count_tokens") else tokenizer(ctx['text'])
        if total + tcount <= max_for_context:
            selected.append(ctx)
            total += tcount
        else:
            allowed = max_for_context - total
            if allowed > 50:
                if hasattr(tokenizer, "encode") and hasattr(tokenizer, "decode"):
                    enc = tokenizer.encode(ctx['text'])
                    truncated = tokenizer.decode(enc[:allowed])
                else:
                    truncated = " ".join(ctx['text'].split()[:allowed])
                selected.append({'id': ctx['id'], 'text': truncated, 'score': ctx.get('score')})
                total += allowed
            break
    ctx_texts = "\n\n---\n\n".join([f"[source: {c['id']}]\n{c['text']}" for c in selected])
    prompt = f"Вопрос: {question}\n\nКонтекст:\n{ctx_texts}\n\nОтветь коротко и по делу."
    return prompt, [c['id'] for c in selected]