# 🤖 AI-Powered Enterprise IT Helpdesk & Triage Assistant

An intelligent, multi-agent IT support system designed to automate IT incident intake, self-service knowledge retrieval, and smart ticket triage. Powered by OpenAI, Flask, and an innovative RAG (Retrieval-Augmented Generation) pipeline using TF-IDF and Cosine Similarity, this project eliminates manual triage overhead and streamlines enterprise IT operations.

---

## 🌟 Key Features

- **Conversational Information Extraction (Agent 1: Intake Agent)**
  - Extracts key incident parameters (_User, Device, Application, Location, Impact, Urgency, Attempted Fixes_) from unstructured, casual user messages.
  - Integrates asset databases to auto-enrich user and device metadata.
  - Dynamically generates polite, concise follow-up questions asking _only_ for missing parameters.

- **Deterministic Knowledge Retrieval & Grounding (Agent 2: Knowledge Retrieval Agent)**
  - Leverages a lightweight, fast **RAG architecture** using `TfidfVectorizer` and Cosine Similarity over local Knowledge Base articles.
  - Automatically cross-checks active outages (`check_known_outages`) and duplicate active tickets (`check_duplicate_tickets`) before escalation.
  - Provides company-approved self-service steps with direct source citations to guarantee zero hallucinations.

- **Closed-Loop Resolution Feedback**
  - Tracks user resolution feedback. If self-service steps fail, the attempt is automatically appended to the diagnostic logs for human engineers.

- **Smart Triage & Ticket Routing (Agent 3: Ticket Routing Agent)**
  - Computes ticket priority (_Impact + Urgency_) via rule-based SLA matrices.
  - Uses semantic classification via LLM to assign the best **Resolver Group** with a human-readable explanation and confidence score.
  - Enforces a safety net (`CONFIDENCE_THRESHOLD = 0.80`)—flagging low-confidence tickets for L1 human review.

- **Document & Knowledge Management API**
  - Admin endpoints to dynamically upload and re-index KB articles, asset maps, priority rules, and resolver groups.

---

## 🏗️ System Architecture & Workflow

[ User Input ]
│
▼
┌───────────────────────────────┐
│ Issue Intake Agent │ ◄── Slot Extraction & Asset Lookup
└──────────────┬────────────────┘
│ (Data Complete)
▼
┌───────────────────────────────┐
│ Knowledge Retrieval Agent │ ◄── RAG (TF-IDF), Active Outages & Duplicates
└──────────────┬────────────────┘
│ (Unresolved / Escalated)
▼
┌───────────────────────────────┐
│ Ticket Routing Agent │ ◄── Priority Matrix, Resolver Matching & Audit Logs
└───────────────────────────────┘

---

## 🛠️ Tech Stack

- **Language & Framework:** Python 3.10+, Flask
- **LLM Engine:** OpenAI API (`gpt-4o` / Chat Completions)
- **Retrieval / Vectorization:** Scikit-Learn (`TfidfVectorizer`), NumPy (Cosine Similarity)
- **Configuration & Environment:** `python-dotenv`
- **Audit Logging:** Custom JSON-based Audit Logger

---

🛡️ Anti-Hallucination Guardrails:

- Grounded Answers: Self-service solutions are strictly fetched from pre-approved internal Knowledge Base documents.

- Deterministic Rules: Priority assignment and SLA target calculation are strictly rule-driven.

- Low Temperature: LLMs are invoked at temperature=0.1 to maintain deterministic behavior.

- Human Review Safety Net: Any ticket classification with a confidence score under 80% is flagged as Pending L1 Triage Review.

---