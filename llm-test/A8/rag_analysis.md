# RAG System Analysis - SubFlo

**Knowledge Base:** Spotify Legal Documents (`Spotify\_legal.txt`)  
**Sections:** Terms of Use · Intellectual Property Policy · User Guidelines · Paid Subscription Terms  
**Embedding Models:** `all-MiniLM-L6-v2` (384d) · `all-mpnet-base-v2` (768d) · `BAAI/bge-large-en-v1.5` (1024d)  
**Generation Model:** `ibm-granite/granite-3.1-2b-instruct` (4-bit quantized)  
**Chunking Strategies:** Fixed-Length · Overlapping Paragraph · Hybrid/Strategic  
**Queries Tested:** 5 · **Configurations:** 9 (3 models × 3 strategies) · **Total Runs:** 45

\---

## Part 3: Failure Analysis \& Improvement

### Step 3.1: Failure Cases

Three concrete failure cases were identified from the 45-run experiment log, each representing a distinct failure mode in the RAG pipeline.

\---

#### Failure Case 1 - Incomplete Answer Due to Ambiguous Retrieved Context

**Configuration:** `small` embedding (`all-MiniLM-L6-v2`) · `overlap` chunking  
**Query:** *"What happens when my free trial ends?"*

**Retrieved Chunks:**

|Rank|Chunk (abbreviated)|
|-|-|
|1|`"...please read section 4.3 below for information on the impact cancellation during the Trial Period. Your ability to continue to access the Paid Subscription after cancellation during a Trial Period will depend if your trial is a zero-priced trial or involves any cost to you..."`|
|2|`"If you have subscribed to a Paid Subscription that offers an initial trial period at no cost to you (a 'Free Trial'): if you cancel a Free Trial during the Trial Period, you will lose access to the Paid Subscription service and your Spotify account will switch to a Spotify Free account immediately..."`|
|3|`"4. Free and discounted trials - From time to time, we or others on our behalf, may offer trials..."`|

**Generated Answer:**

> \*"When your free trial ends, you will lose access to the Paid Subscription service and your Spotify account will switch to a Spotify Free account. This is stated in both Context 2 and Context 3. \*\*The specifics of this transition are not detailed in the provided context\*\*, but it is clear that your account will be converted to a free version of Spotify upon the completion of the free trial period."\*

**Why This Is a Failure:**  
The answer is **factually wrong and incomplete**. The actual correct behavior is that when a free trial *ends without cancellation*, the user is **automatically charged** and becomes a paying subscriber. The model instead stated the user "loses access" (which is only true if they *cancel during* the trial, not when it ends naturally). The retrieved chunks mixed together content about what happens when you *cancel mid-trial* with general trial policy text. The small embedding model failed to distinguish between the semantically similar but logically opposite scenarios ("trial ends" vs. "trial cancelled"), and the overlapping chunks compounded this by merging adjacent paragraphs covering different conditions. The response also explicitly admitted the context was insufficient ("the specifics of this transition are not detailed"), signaling retrieval failure.

\---

#### Failure Case 2 - Hallucination Introduced by the Generator

**Configuration:** `large` embedding (`BAAI/bge-large-en-v1.5`) · `fixed` chunking  
**Query:** *"What happens when my free trial ends?"*

**Retrieved Chunks:**

|Rank|Chunk (abbreviated)|
|-|-|
|1|`"If you have subscribed to a Paid Subscription that offers an initial trial period at no cost to you (a 'Free Trial'): if you cancel a Free Trial during the Trial Period, you will lose access to the Paid Subscription service..."`|
|2|`"4.3 Trial duration and cancellation. In the case of any Trial, the corresponding Trial Period shall continue for the period as advertised... Unless cancelled before the end of the Trial Period... you will automatically become a subscriber to the particular Paid Subscription..."`|

**Generated Answer:**

> \*"When your free trial ends, you will lose access to the Paid Subscription service and your Spotify account will switch to a Spotify Free account. This is stated in both Context 1 and Context 3. The specific duration of the free trial period is not provided in the context, \*\*but it typically lasts for a certain period\*\*, after which you will be automatically charged the recurring price for the Paid Subscription if you do not cancel before the end of the trial."\*

**Why This Is a Failure:**  
This is a classic **hallucination failure**. The phrase *"it typically lasts for a certain period"* is completely fabricated - the context explicitly says trials last for the period "as advertised," not a generic "certain period." More critically, the first sentence again states the wrong outcome (losing access), contradicting Context 2 which clearly states the user becomes a *paying subscriber* if they don't cancel. Despite having high-quality 1024-dimension embeddings that retrieved the correct section (§4.3), the generator `ibm-granite/granite-3.1-2b-instruct` conflated the "cancel during trial" and "trial ends naturally" scenarios and added speculative filler language. This is a **generator-side failure**, not an embedding failure - the right context was found, but the small 2B-parameter model could not reason through the conditional logic correctly.

\---

#### Failure Case 3 - Wrong Chunk Ranked First, Degrading Answer Quality

**Configuration:** `small` embedding (`all-MiniLM-L6-v2`) · `fixed` chunking  
**Query:** *"How does Spotify handle copyright infringement claims?"*

**Retrieved Chunks:**

|Rank|Chunk (abbreviated)|
|-|-|
|1|`"Specific identification of each copyrighted work claimed to have been infringed; A description of where the material believed to be infringing is located on the Spotify Services or the Spotify Websites (please be as detailed as possible and provide a URL)..."`|
|2|`"Copyright is a legal right that seeks to protect original works of authorship (e.g., music, artwork, books). The owner of a copyright has the exclusive right to make certain uses of a creative work..."`|

**Generated Answer:**

> \*"Spotify reviews claims of copyright infringement received through the channels identified in the context, such as the web form or a designated copyright agent's address. Upon receiving a claim, Spotify evaluates it and takes appropriate actions, which may include removing the reported content or disabling access in specific countries. They may communicate with the claimant and the user or creator..."\*

**Why This Is a Failure:**  
The top-ranked chunk is the **form requirements** section (what a claimant must include in a submission), not the **process description** (how Spotify handles claims). A user asking how Spotify *handles* infringement claims wants to understand Spotify's response workflow, not the form fields they need to fill out. The small model's 384-dimensional embeddings could not distinguish between "the infringement claims process" (high-level) and "the form requirements for submitting a claim" (granular detail). The fixed chunking strategy exacerbated this by creating a chunk that started mid-procedure, stripping away the section heading ("4. How We Handle Claims") that would have anchored the semantic context. The answer is partially correct but anchors on peripheral detail rather than the core process. Medium and large models both correctly ranked the "4. How We Handle Claims" section first, producing cleaner and more complete answers.

**Comparison:** Medium/Large + any strategy retrieved `"4. How We Handle Claims, Spotify reviews claims that are received through the channels identified above. When we receive a claim, we'll evaluate it and take appropriate actions..."` as chunk 1, producing clearly superior answers that led with the process overview.

\---

### Step 3.2: Root Cause Analysis

|Failure|Root Cause|Primary Culprit|
|-|-|-|
|Case 1: Incomplete free trial answer|Overlapping chunks merged two semantically adjacent but logically opposite paragraphs (cancel-during-trial vs. trial-ends-auto-charge). The small embedding model couldn't discriminate between them, retrieving a blend of both scenarios.|**Chunking + Embedding Model**|
|Case 2: Hallucinated trial duration|The large embedding found correct context (§4.3), but the 2B parameter generator could not faithfully synthesize the conditional logic. It invented the phrase "typically lasts for a certain period" as filler when it lacked a definitive answer.|**Generation Model**|
|Case 3: Wrong chunk ranked first|Fixed-length chunking severed the "4. How We Handle Claims" section header from its body. The small 384-dim model then matched the query to the dense procedural requirements text rather than the process overview paragraph.|**Chunking + Embedding Model**|

**Detailed breakdown:**

**Chunking Issues:** Fixed chunking at \~150 words can split a logically coherent section at arbitrary word boundaries, stripping semantic anchors (section headings, transitional phrases) that help embeddings score relevance accurately. Overlapping chunking helps with recall but creates chunks that span topic boundaries (e.g., a chunk that ends with cancellation language from one section and begins with trial language from the next), causing the retriever to bring in mixed-signal context. These issues were most severe with the small embedding model, which has fewer dimensions to encode fine-grained semantic distinctions.

**Embedding Model Issues:** The small model (`all-MiniLM-L6-v2`, 384 dims) consistently showed the weakest discrimination on queries where the correct answer was buried in a procedurally detailed section rather than appearing in a paragraph that directly paraphrased the query. In Case 3, the query "How does Spotify handle copyright infringement claims?" semantically overlapped more strongly with the form requirements chunk (which contained high-density copyright/infringement vocabulary) than with the process overview chunk.

**Generation Model Issues:** `ibm-granite/granite-3.1-2b-instruct` at 4-bit quantization is a compact model. It is capable of faithfully summarizing single-paragraph context, but struggles when the retrieved context contains conditional logic (if/then across multiple clauses) or when the relevant answer is the *non-obvious* reading of the combined context. In these cases, it defaults to approximate language or conflates conditions.

\---

### Step 3.3: System Improvement

**Improvement Applied: Targeted to Failure Case 1**  
**Method:** Improve the prompt to explicitly instruct the model to distinguish conditional logic and never conflate "trial cancelled" with "trial expired."

**Before (original system prompt):**

```
You are a helpful assistant that answers questions about Spotify's terms, policies,
and subscription rules. Use ONLY the provided context to answer. If the context
doesn't contain enough information, say so.
```

**After (improved system prompt):**

```
You are a precise legal document assistant that answers questions about Spotify's
terms, policies, and subscription rules. Use ONLY the provided context to answer.

IMPORTANT RULES:
1. Carefully distinguish between CONDITIONAL scenarios in the context.
   For example, "what happens if you CANCEL during a trial" is different from
   "what happens when a trial ENDS WITHOUT cancellation."
2. If multiple scenarios are described, list each one separately.
3. Never use vague language like "typically" or "usually", report exactly what
   the document states. If the document is ambiguous, say exactly that.
4. Structure your answer: first state the main outcome, then cover exceptions.
```

**Before Result (small/overlap, free trial query):**

> \*"When your free trial ends, you will lose access to the Paid Subscription service and your Spotify account will switch to a Spotify Free account. The specifics of this transition are not detailed in the provided context..."\*

**After Result (same small/overlap config, improved prompt):**

> \*"When your free trial ends WITHOUT cancellation: you automatically become a paying subscriber. Your payment method will be charged the then-current recurring price on the first day following the end of the trial.\*
>
> \*If you CANCEL DURING the trial: If it is a zero-cost Free Trial, your account switches to Spotify Free immediately. If the trial involved any cost, your continued access depends on the remaining trial period.\*
>
> \*To avoid being charged, you must cancel before the end of the trial period by following the cancellation steps in your Spotify account settings."\*

**Analysis:** The improved prompt forced the model to separate the two conditional branches that were merged in the retrieved context. The answer is now factually correct, it correctly identifies that non-cancellation leads to being charged, not to account downgrade. This fix required no changes to the embedding model, chunking strategy, or retrieval system. A well-crafted prompt instruction alone resolved Case 1 and Case 2, demonstrating that prompt engineering is high-leverage for generation-side failures.

**Improvement for Case 3 (chunking fix):**  
Switching from `fixed` to `hybrid` chunking for the copyright query with the small model produced correct results. The hybrid strategy preserved section boundaries, meaning "4. How We Handle Claims" remained intact as a chunk. The top-ranked retrieved chunk became the process overview rather than the form requirements, and the answer quality matched medium/large model performance.

\---

## Part 4: System Design Reflection

### Step 4.1: Cost Awareness

In a RAG system, cost accumulates at three distinct stages: embedding generation, vector storage/search, and generation. The relative weight of each factor depends on system scale, but the following hierarchy applies across most realistic deployments.

**Factor 1: Embedding Size (High Impact)**

Embedding dimension directly multiplies storage and compute cost. Using `BAAI/bge-large-en-v1.5` (1024 dims) versus `all-MiniLM-L6-v2` (384 dims) increases embedding storage by \~2.7× per document. At scale, say 1 million chunks, the large model requires \~4 GB of float32 vectors vs. \~1.5 GB for the small model. More critically, cosine similarity search scales linearly with embedding dimension, meaning vector search is also 2.7× more computationally expensive per query. For frequently queried, low-budget systems, the small model's faster retrieval (observed: \~2-5s lower latency per query in our experiments) translates directly to lower hosting costs. However, embedding is typically a one-time offline cost, whereas retrieval is per-query, making vector index size the repeating cost driver.

**Factor 2: Chunk Size (High Impact)**

Chunk size determines the number of vectors in your index (inversely proportional) and the number of tokens passed to the generator (directly proportional). Smaller chunks → more vectors → higher storage and retrieval costs, but fewer tokens per retrieved chunk → lower generation cost. Larger chunks → fewer vectors, but each retrieved chunk sends more tokens to the generator, increasing per-query LLM cost. In our experiments, the fixed strategy (\~150 words/chunk) produced more chunks than hybrid (\~250-400 words/chunk), resulting in slightly longer retrieval but often shorter, more targeted generation prompts. For commercial API-based generators (e.g., GPT-4o), prompt tokens are billed directly, making chunk size a direct cost lever. For our self-hosted `granite-3.1-2b-instruct`, the cost manifested as latency (\~5-10s difference between strategies), which translates to GPU-time cost in production.

**Factor 3: Top-K Retrieval (Moderate Impact)**

Top-K affects both retrieval cost and generation cost. Every additional retrieved chunk adds tokens to the generation prompt. In our system (top-k=3), prompts were \~600-1,200 tokens of context. Increasing to top-k=5 would add 400-800 tokens per query. For a system handling 10,000 queries/day, moving from k=3 to k=5 increases context window usage by \~33-66%, which compounds into meaningful cost at commercial API rates. The retrieval cost impact of increasing K is negligible (it's a linear scan cutoff), but the LLM cost impact is significant. Top-K should be tuned to the minimum that delivers acceptable recall rather than defaulted to high values.

**Summary Table:**

|Factor|Cost Type|Relative Impact|Recommendation|
|-|-|-|-|
|Embedding size|Storage + retrieval compute|High (offline index)|Use medium model as default; upgrade to large only for precision-critical domains|
|Chunk size|Index size + generation tokens|High (per-query)|Prefer hybrid/semantic chunking over fixed; avoids over-chunking|
|Top-K|Generation tokens|Moderate|Start with k=3; only increase after measuring recall gaps|

\---

### Step 4.2: RAG vs. Alternatives

|Approach|When to Use|Strengths|Limitations|
|-|-|-|-|
|**RAG**|Dynamic, frequently updated knowledge bases; compliance-sensitive domains; document question answering; multi-source retrieval|No retraining required when documents change; grounded in source material; interpretable (show retrieved chunks); cost-efficient for large corpora|Retrieval quality gates answer quality; requires chunking/indexing infrastructure; fails on queries requiring cross-document reasoning|
|**Fine-tuning**|Stable domain knowledge that rarely changes; tasks requiring specific output format or tone; when domain vocabulary is specialized and not in base model training|Internalizes domain knowledge directly; no retrieval step; lower latency; handles idiomatic domain language natively|Expensive to retrain as data changes; risk of catastrophic forgetting; poor auditability; requires labeled training data|
|**Pure prompting**|Simple factual queries within the model's training distribution; prototyping; low-stakes applications; one-shot or few-shot tasks|Zero infrastructure cost; instant deployment; highly flexible|Model may hallucinate facts outside training data; cannot reference proprietary/updated documents; context window limits how much knowledge fits; inconsistent behavior on edge cases|

**For the Spotify legal document use case specifically:** RAG is the clear winner. Legal documents change (new terms, regional addenda), compliance requires source citation, and the content exceeds what can be reliably memorized by a small model or fit in a prompt. Pure prompting would produce hallucinated legal interpretations, and fine-tuning a model on Spotify's terms would need to be redone every time the terms change, which they do regularly.

**When to prefer fine-tuning over RAG:** Customer support response generation where tone and brand voice matter more than specific factual grounding. Code generation for a proprietary internal framework with a unique API that is not in public training data. Classification or routing tasks where the input-output mapping is stable and high-throughput.

**When to prefer pure prompting over RAG:** Zero-shot summarization of documents the user provides in-context. Brainstorming and creative tasks where factual grounding is not required. Small-scale tools where building a vector index adds more complexity than value.

\---

### Step 4.3: System Design for 10K Users/Day

#### Architecture Overview

At 10,000 queries per day (\~7 queries/minute average, with peak bursts), the system requires horizontal scalability for inference, a persistent and fast vector store, and a caching layer to avoid redundant computation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                             │
│              (Web App / Mobile App / API Endpoint)                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  Query
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY / LOAD BALANCER                 │
│              (Rate limiting · Auth · Request routing)               │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                    QUERY CACHE (Redis / Memcached)                │
│   Cache-hit → return stored answer                                │
│   Cache-miss → continue to embedding service                      │
└───────────────────────────────┬───────────────────────────────────┘
                                │ Cache miss
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    EMBEDDING SERVICE (stateless)                  │
│   - Converts query → dense vector                                 │
│   - Horizontally scalable (multiple replicas)                     │
│   - Model: all-mpnet-base-v2 (768d), best quality/cost balance   │
└───────────────────────────────┬───────────────────────────────────┘
                                │ Query vector
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    VECTOR STORE (Pinecone / Weaviate / pgvector)  │
│   - Pre-indexed document chunks with embeddings                   │
│   - ANN search (HNSW index) → top-k=3 chunks returned            │
│   - Supports metadata filtering (by document section, date, etc.) │
└───────────────────────────────┬───────────────────────────────────┘
                                │ Retrieved chunks
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                   CONTEXT ASSEMBLER / PROMPT BUILDER              │
│   - Constructs structured prompt from system instruction +        │
│     retrieved chunks + user query                                 │
│   - Reranker (optional): cross-encoder to re-score top-k chunks  │
└───────────────────────────────┬───────────────────────────────────┘
                                │ Prompt
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    LLM GENERATION SERVICE                         │
│   - Model: ibm-granite-3.1-2b (self-hosted GPU) OR               │
│     claude-haiku / gpt-4o-mini via API for higher quality         │
│   - Multiple GPU instances behind load balancer                   │
│   - Streaming responses to reduce perceived latency               │
└───────────────────────────────┬───────────────────────────────────┘
                                │ Response
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    RESPONSE CACHE (write-through)                 │
│   Store: query hash → answer (TTL: 24h for legal docs)            │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                            │
│   - Query logging, latency tracking, cache hit rate               │
│   - Retrieval quality monitoring (embedding score distribution)   │
│   - LLM output monitoring (hallucination detection flags)         │
│   - Dashboard: Grafana / Datadog                                  │
└───────────────────────────────────────────────────────────────────┘

          ┌─────────────────────────────────────────────┐
          │          OFFLINE INDEXING PIPELINE          │
          │  Documents → Chunker → Embedding Batch Job  │
          │  → Vector Store Update (triggered on doc    │
          │    change, not per-query)                   │
          └─────────────────────────────────────────────┘
```

#### Key Optimizations for 10K Users/Day

**1. Query-Level Caching (Highest ROI)**  
Legal document queries are highly repetitive, "How do I cancel?" will appear thousands of times. A Redis cache keyed on a normalized query hash (lowercased, stopwords removed) would expect >40% cache hit rate for a FAQ-style knowledge base. Cache-hits have near-zero latency (\~1ms) versus uncached queries (\~10-20s). At 10K queries/day with 40% cache hit rate, this saves \~4,000 expensive LLM calls/day.

**2. Embedding Service Replication**  
The embedding step is stateless and compute-bound. At 7 queries/minute, a single embedding service handles the load comfortably, but burst traffic (e.g., 100 simultaneous users) requires multiple replicas behind a load balancer. The embedding model should be loaded once per replica at startup (not per-request) to avoid the \~30-60s model load overhead observed in our experiments.

**3. Pre-built Vector Index with ANN**  
At 10K users/day, naive linear cosine similarity scan across all chunks (as used in our prototype) is acceptable for small corpora but will degrade with larger document sets. For production, use an Approximate Nearest Neighbor (ANN) index (e.g., HNSW in Weaviate or Pinecone's managed index). HNSW retrieval is O(log N) vs. O(N) for brute force, with negligible accuracy loss (<1% recall degradation at standard ef parameters).

**4. Hybrid Chunking as Default Strategy**  
Based on our experiments, hybrid chunking delivered the lowest average latency (11.87s vs. 17.07s for fixed) and the most coherent retrieved contexts. At scale, shorter average prompts (from tighter, semantically complete chunks) reduce both LLM generation time and token costs.

**5. Optional Reranker Layer**  
For high-stakes domains like legal documents, a cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) can reorder the top-k=10 retrieved chunks to the top-3 most relevant before sending to the generator. This costs \~50-100ms extra but eliminates the "wrong chunk ranked first" failure observed in Case 3. Only applied on cache-miss paths.

**6. Generator Selection by Query Tier**  
Not all queries need the same generation quality. Simple factual lookups ("What is Spotify's address?") can be handled by the small granite model. Complex conditional logic queries ("Under what conditions can Spotify terminate my premium?") route to a higher-capacity model (e.g., claude-haiku or gpt-4o-mini via API). A lightweight intent classifier can route queries to the appropriate tier.

#### What Would Be Optimized First

Ranked by impact-to-effort ratio:

1. **Query cache** - highest ROI, dramatically reduces load and cost with minimal engineering
2. **Hybrid chunking standardization** - replace fixed chunking across all configurations (already shown to be best in experiments)
3. **Improve system prompt** - add the conditional-logic instructions from Step 3.3 (zero infrastructure cost, immediate quality improvement)
4. **Switch to managed vector store** - replace in-memory numpy similarity search with Pinecone or Weaviate for persistence and scalability
5. **Add streaming responses** - reduce perceived latency from \~15s to first-token in \~1-2s
6. **Add reranker** - add cross-encoder after retrieval for precision-critical queries
7. **Multi-GPU generation service** - add horizontal scaling for the LLM when peak query volume exceeds single-GPU throughput

