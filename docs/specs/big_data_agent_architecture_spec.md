# Specification: Production-Grade Big Data & Heavy-Compute Agent Architecture

**Status:** APPROVED (Post War-Room Consensus)  
**Version:** 3.0.0  
**Target Subsystems:** `data_pipeline`, `distributed_queue`, `tri_modal_router`, `memory_layer`

---

## 1. Architectural Foundations

This specification formalizes the production-grade decoupling between **Cognition (LLM Planning & Synthesis)** and **Computation (Vectorized Out-of-Core Compute & Message Queuing)** to solve big-data workloads (multi-GB files, millions of records, heavy ETL) without context blowups, token waste, or OOM crashes.

```
[ Master Agent / Lead Architect ] ──(Metadata Only)──> [ Task Splitter (Quote-Aware) ]
                                                                │
                                                  (Metadata Chunks: <200B)
                                                                ▼
                                                  [ Message Queue (Celery/Redis) ]
                                                                │
                                            ┌───────────────────┴───────────────────┐
                                            ▼                                       ▼
                               [ Worker (DuckDB Spill) ]               [ Worker (DuckDB Spill) ]
                                            │                                       │
                                            └───────────────────┬───────────────────┘
                                                                ▼
                                                  [ Data Aggregator (Pure Code) ]
                                                                │
                                                  [ Post-Task Pipeline (memory_layer) ]
                                                    ├── S3 / Shared Storage (Raw)
                                                    ├── State / Graph DB (Checkpoints)
                                                    └── Milvus Lite (Dual-Tier Insight)
```

---

## 2. Subsystem Specifications

### 2.1 Subsystem A: `data_pipeline` (Chunking & Bounded Compute Engine)

#### A.1 `QuoteAwareChunker`
* **Invariant:** Never split inside an RFC 4180 multiline quoted field (`"..."`).
* **Algorithm:** 2-pass byte stream scanner tracking `in_quotes` parity (`0x22`). A chunk boundary at target byte size $S$ is valid **only if** byte is `0x0A` (`\n`) and `in_quotes == False`.
* **Output:** Deterministic slice list `[(start_byte, end_byte, chunk_index), ...]`.

#### A.2 `DuckDBWorker`
* **Invariant:** Worker memory allocation is strictly bounded by buffer pool manager; excess spills to disk without Linux `SIGKILL (OOM 137)`.
* **Configuration:**
  - `PRAGMA max_memory = '2GB';`
  - `PRAGMA temp_directory = '/tmp/duckdb_spill';`
  - `PRAGMA threads = 2;`
* **Execution:** Reads assigned byte ranges or Parquet row groups directly with predicate/projection pushdown, emits Arrow/Parquet partitions.

---

### 2.2 Subsystem B: `distributed_queue` (Hardened Celery & Redis Protocol)

#### B.1 Acknowledgment & Failure Semantics
* `task_acks_late = True`: Message is acknowledged only AFTER successful execution.
* `task_reject_on_worker_lost = True`: If worker process dies (OOM/segfault), Kombu immediately requeues the task.
* `worker_prefetch_multiplier = 1`: Workers consume exactly 1 task at a time (with `-O fair`), eliminating starvation.

#### B.2 Invariant Timeout Inequality
$$\mathbf{visibility\_timeout} \;(86400\text{s}) \;\gg\; \mathbf{task\_time\_limit} \;(7500\text{s}) \;>\; \mathbf{task\_soft\_time\_limit} \;(7200\text{s})$$
* Completely neutralizes Redis ghost duplicate redelivery on long-running ETL partitions.

#### B.3 Proactive Memory Recycling
* `worker_max_memory_per_child = 2097152` (2GB): Child process gracefully exits between tasks if RSS exceeds 2GB.
* `worker_max_tasks_per_child = 50`: Eliminates heap fragmentation.

---

### 2.3 Subsystem C: `tri_modal_router` (Token Economics & Routing Gate)

Every data task is routed across 3 mutually exclusive tiers:
1. **Tier 0 (Pure Code - DuckDB/Polars):**
   - Applies to: Math, aggregations, filtering, regex, deduplication, schema validation.
   - Cost: $0.00 (0 tokens). Speed: $10\text{M+}$ rows/sec. Zero hallucination.
2. **Tier 1 (Real-Time Worker Pool - `flash_lite` / `flash`):**
   - Applies to: Multi-turn agent loops (ReAct/Reflexion), interactive user commands, CI/CD blocking quality gates.
   - Latency: $500\text{ms} - 5\text{s}$.
3. **Tier 2 (Asynchronous Batch API):**
   - Applies to: Bulk semantic operations ($>1,000$ items or $>5\text{M}$ tokens), offline background processing.
   - Economics: Flat 50% discount, separate token quotas, 24-hour turnaround window.

---

### 2.4 Subsystem D: Upgraded `memory_layer` (Dual-Tier `SourceChunkPointer`)

#### D.1 Epistemic Provenance Invariant
To eliminate Cosine Blindness from lossy $<200$-character condensation:
* Every insight vector in Milvus Lite includes a mandatory `source_pointer` mapping:
  - `storage_uri`: S3 / Local storage path of raw source dataset.
  - `file_path`: Path to the source file.
  - `chunk_id`: Partition/chunk identifier.
  - `line_range`: Exact `[start_line, end_line]` in the source document.
  - `git_commit_sha`: Exact repository commit state.
* **Retrieval Protocol:** Global agent loads the short insight (<3KB prompt); implementer subagent dereferences `source_pointer` on demand for bit-for-bit raw truth.

#### D.2 Idempotent Upsert & Content-Addressable UID
$$\text{UID} = \text{BLAKE3}\Big( \text{tenant\_id} \parallel \text{task\_id} \parallel \text{insight\_type} \parallel \text{Normalize}(\text{insight\_text}) \Big)$$
* Upsert eliminates duplicate embedding drift across Reflexion retries.
