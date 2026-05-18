# ClinicalRAG Architecture

ClinicalRAG is designed as a grounded clinical decision support system rather than a general chatbot. The core product requirement is not simply to produce a fluent answer; it is to retrieve relevant clinical source material, constrain the model to that material, show the physician exactly which guidelines were used, and record a privacy-conscious audit trail of the interaction. The architecture separates those responsibilities into small, inspectable stages.

## Why LangGraph

A simple LangChain chain can work for a basic retrieval-augmented generation demo, but it becomes limiting once the application needs clinical guardrails and production behavior. ClinicalRAG uses LangGraph because the RAG flow is explicitly stateful: each request carries the original query, selected collection, retrieved documents, relevance-filtered documents, generated answer, grounding score, warning state, query identifier, and timing metadata. This makes the pipeline easier to inspect and extend than a single linear chain.

LangGraph also gives the system conditional edges. After retrieval, the relevance grading node can decide whether any retrieved guideline chunks are good enough to support an answer. If no relevant evidence is found, the graph skips generation and goes directly to grounding evaluation and response formatting. That matters clinically because the safest answer to many queries is not a best-effort guess; it is a clear statement that the available guidelines do not contain enough evidence. This graph shape also leaves room for future nodes: PHI detection before retrieval, query rewriting, specialty-specific routing, citation verification, human review queues, retry logic for model failures, and post-generation safety checks.

## Why ChromaDB

ChromaDB is used instead of Pinecone because this project is meant to be portable, low-cost, and easy to run during a technical evaluation. The vector store persists to disk, so the seeded guideline corpus and any ingested documents survive API restarts without requiring a managed vector database. For a portfolio-grade clinical AI demo, avoiding vector API spend and account setup reduces friction while still showing the correct retrieval architecture.

The implementation keeps the vector-store boundary narrow: documents are chunked, embedded with `all-MiniLM-L6-v2`, and stored with metadata such as title, document type, source URL, document ID, chunk index, total chunks, and content hash. That means a future migration to Pinecone, Weaviate, Qdrant, or a managed Postgres vector extension would not require rewriting the LangGraph pipeline. The retrieval contract can remain the same: given a query, collection, and `k`, return ranked documents with metadata and distances.

## Grounding Evaluation

ClinicalRAG computes a sentence-level grounding score using attribution checks rather than cosine similarity alone. Cosine similarity is useful for retrieval, but it is not a reliable measure of factual attribution. A hallucinated clinical statement can be semantically close to a guideline paragraph and still introduce an unsupported dosage, contraindication, or criterion. Conversely, a faithful answer may paraphrase a source rather than quote it exactly.

The evaluator splits the generated answer into substantive sentences and checks whether each sentence can be tied to at least one retrieved source chunk. Exact four-word n-gram overlap is treated as strong evidence. For paraphrased answers, the evaluator also uses normalized clinical/content-token overlap within individual source chunks. This keeps the score stricter than generic semantic similarity while avoiding false low scores when the model rephrases guideline text. It is not a replacement for formal clinical validation, but it is a practical first-pass signal for demo and development: low scores trigger warnings, medium scores invite review, and high scores indicate that the answer is mostly traceable to retrieved material.

## Retrieval and Reranking

The first retrieval pass uses ChromaDB vector search over local sentence-transformer embeddings. ClinicalRAG then applies a small deterministic reranker based on query-token overlap, exact term presence, title matches, and original vector relevance. This keeps the implementation transparent and avoids introducing another model call just to reorder citations. It also improves demo credibility: if a physician asks about SGLT2 inhibitors, the SGLT2 guideline chunk should appear before adjacent but less relevant heart-failure chunks.

## HIPAA-Aware Design

The audit log is designed around minimization. Raw queries are not stored. Instead, the logger stores a SHA-256 hash of the query, the collection name, number of sources retrieved, grounding score, latency, timestamp, and generated audit ID. This is enough for operational monitoring, incident analysis, latency tracking, retrieval-quality review, and duplicate-query detection without creating a database of physician-entered clinical text.

This design is HIPAA-aware, not a complete HIPAA compliance claim. A production deployment handling protected health information would need a Business Associate Agreement with every relevant vendor, including hosting and LLM providers; encryption at rest and in transit; strict access controls; role-based authorization; audit-log retention policies; secrets management; vulnerability management; private networking where appropriate; and a documented incident response process. If raw PHI ever needed to be stored, the storage layer would require stronger controls and clear retention rules. In many clinical AI systems, the better design is to avoid storing PHI unless there is a direct clinical or regulatory need.

## Production Scaling

The demo uses SQLite for audit logging because it is simple, reliable, and appropriate for a single Railway instance. In production, audit logs should move to PostgreSQL with indexes on timestamp, collection, query hash, and response metadata. PostgreSQL would also make retention policies, reporting, and compliance exports easier.

Query caching is a natural next step. A Redis cache keyed by normalized query plus collection plus retrieval parameters could store grounded responses for approximately one hour. That would reduce latency and model spend for repeated operational questions while still respecting the fact that ingested guidelines may change. Cache invalidation should occur on document ingestion or collection rebuild.

Ingestion should also move out of the request path. The current `/ingest` endpoint chunks and embeds immediately, which is fine for small guideline text but not for large FHIR bundles, PDFs, or institutional protocol libraries. A production version should enqueue ingestion jobs with Celery and Redis, store job state, validate document formats, and expose progress to the UI. This also prevents large ingestion tasks from blocking API workers.

Horizontal scaling requires care around the ChromaDB persistence path. A single local Chroma volume works for a demo, but multiple API instances need a shared vector database or a coordinated ingestion/indexing service. The FastAPI layer can scale horizontally once shared storage is in place and model clients are initialized per process. Read-heavy query workloads can then scale behind a load balancer, while ingestion workers run separately and update the vector store asynchronously.

The main architectural principle is that every clinical answer should be explainable from stored guideline chunks, every request should leave a minimal audit trail, and every stage should be replaceable as the system moves from demo to production.
