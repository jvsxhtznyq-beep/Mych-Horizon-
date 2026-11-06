# Memory and Retrieval

Keeping the right context in the model's window, and grounding answers in the owner's documents.

## Short-term memory

- A **sliding window** keeps the most recent turns within a budget. `SlidingWindowMemory` groups each assistant tool call with its results so they are kept or dropped together; a tool result without its call confuses every provider.
- A **summary** of dropped turns (produced by a cheap model call or a template) preserves key facts: names, decisions, open questions. Label it as context, not instructions.
- Budget by characters or tokens with headroom for the answer and tool definitions.

## Long-term memory

- Store durable facts (preferences, account ids) only with the user's consent and a retention policy.
- Keep facts structured (key and value with a source and timestamp), not as free-text transcripts.
- Let users see and delete what is remembered.

## Retrieval pipeline

1. **Ingest:** extract text, keep source metadata (title, URL, owner, updated date), remove boilerplate.
2. **Chunk:** by paragraphs or headings, a few hundred to about a thousand characters, with small overlaps when context spans boundaries.
3. **Index:** keyword search (BM25, as in `KeywordIndex`) works well for names, codes and exact terms; embeddings help with paraphrases; hybrid search combines both.
4. **Retrieve and rerank:** take the top candidates; rerank when quality matters.
5. **Answer with citations:** pass chunks fenced as data with ids; require the model to cite ids for claims and to say "not found" when nothing relevant was retrieved.

## Evaluating retrieval

- Build a question set with the chunk ids that should be retrieved; measure recall at k.
- Track answer groundedness: every claim traceable to a cited chunk.
- Re-run after re-chunking, re-indexing or document updates.

## Freshness and ownership

Document owners and update cadence matter as much as the index: stale documents produce confident wrong answers. Show the source and date with answers when users rely on them.
