# Email Relationship Extractor

An offline, privacy-first system that automatically generates high-value relationship summaries from email threads. It uses local embeddings (MiniLM), deterministic heuristics, and regex to extract budget, timeline, commitments, and sentiment without sending data to external AI APIs.

## 🚀 Features

* **Thread Context Extraction**: Identifies meaningful exchanges, collapsing rapid-fire replies and filtering out signatures/quotes.
* **Intent & Budget Detection**: Extracts hard numbers (budget), dates (timeline), and constraints using robust regex and heuristic analysis.
* **Commitment Tracking**: Automatically flags promises made by the founder (e.g., "I'll send the proposal by Friday").
* **Sentiment Trend Analysis**: Tracks whether a relationship is "warming" or "cooling" over time using local embedding similarity.
* **Internal & Vendor Filtering**: Automatically classifies contacts as Internal, Vendor, or External Opportunity to reduce noise.
* **Privacy-First**: Runs 100% locally on CPU. No data leaves your machine.

## 🛠️ Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/pnutnam/relationship_summary-.git
    cd relationship_summary-
    ```

2. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    # Or manually: pip install sentence-transformers sqlalchemy psycopg2-binary numpy
    ```

3. **Configure Database**:
    Update the `CONNECTION_STRING` in `analyze_data.py` with your Postgres credentials.

## 💻 Usage

### Analyze Real Data

Run the analysis script to process emails from your database and generate a JSON/CSV report.

```bash
python analyze_data.py
```

This will output:

* `real_data_analysis.json`: Detailed hierarchical data.
* `real_data_analysis.csv`: Flattened summary for spreadsheet viewing.

### Run Demo

Run the standalone extractor with synthetic data to test logic changes.

```bash
python extractor.py
```

## 🏗️ Architecture

The system is designed as a linear pipeline:

1. **Ingestion**: Fetches raw emails from Postgres.
2. **Filtering**: Excludes vendors (Stripe, AWS) and spam.
3. **Context Extraction**: Cleans bodies, removes signatures, and merges adjacent messages.
4. **Entity Extraction**: Uses Regex for Budget/Timeline and MiniLM embeddings for Intent.
5. **Sentiment Scoring**: Computes cosine similarity against positive/negative anchors.
6. **Aggregation**: Compiles all signals into a `RelationshipSummary` object.

## 🔮 Potential Improvements (Roadmap)

* **Advanced NER**: Integrate a lightweight NER model (like GLiNER or Spacy) to better extract company names and specific project entities.
* **Vector Storage**: Store message embeddings in a local vector DB (Chroma/FAISS) to enable semantic search (e.g., "Show me everyone who asked about 'pricing' last month").
* **Dynamic Thresholds**: Automatically adjust sentiment thresholds based on the baseline "warmth" of a specific contact.
* **Calendar Cross-Reference**: Check extracted "due dates" against the user's actual calendar availability.
* **LLM "Plugin"**: Add an optional hook to call a local LLM (Llama 3 8B) for summarizing extremely long/complex threads that heuristics miss.

## 🚀 Next Things to Build

Using this engine as a backbone, here are the high-value applications to build next:

### 1. The "Morning Briefing" Dashboard

A simple UI (Streamlit/React) that shows **only** the contacts requiring attention today.

* **Filter**: `requires_reply = True` AND `opportunity_stage != 'internal'`.
* **Sort**: By `budget` (value) or `sentiment_trend` (urgency).
* **Action**: One-click "Draft Reply" using the extracted context.

### 2. Auto-Drafting Agent

Use the extracted `budget`, `timeline`, and `constraints` to pre-fill reply templates.

* *If budget is missing*: Draft a reply asking for budget.
* *If timeline is tight*: Draft a reply checking for flexibility.
* *If commitment made*: Draft a calendar invite for the due date.

### 3. CRM Bi-Directional Sync

Instead of a static JSON file, push these insights directly into HubSpot/Salesforce.

* Map `opportunity_stage` to CRM Deal Stage.
* Map `budget` to Deal Amount.
* Log `commitments` as CRM Tasks.

### 4. "Ghosting" Detector

Identify high-value opportunities that have gone silent.

* Logic: `opportunity_stage = 'proposal_sent'` AND `last_interaction > 7 days ago` AND `last_sender = 'me'`.
* Action: Trigger a "Bump" email draft.
