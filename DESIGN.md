# Email Relationship Extractor - System Design

## 1. Architecture Overview

The system is designed as a linear pipeline that processes emails for a single contact (aggregated by email address). It operates entirely offline, using CPU-optimized embeddings and deterministic heuristics.

**Pipeline Stages:**

1. **Ingestion**: Load raw email threads for a specific contact.
2. **Filtering (Vendor/Spam)**: Apply strict allow/block lists and heuristic checks to exclude non-human interactions.
3. **Context Extraction**: Identify "meaningful" human-written messages, collapsing rapid-fire exchanges.
4. **Intent & Commitment Extraction**:
    - **Regex Pass**: Fast, deterministic extraction of budget, timeline, and explicit commitments.
    - **Embedding Pass**: Use `all-MiniLM-L6-v2` to classify intent and soft commitments if regex fails.
5. **Sentiment Analysis**: Compute embedding-based sentiment scores to determine the relationship trend (warming/cooling).
6. **Summary Generation**: Aggregate findings into a structured JSON object.

## 2. Extraction Rules & Heuristics

### 2.1. Thread Context (Meaningful Exchanges)

- **Filter**: Exclude emails with headers `List-Unsubscribe`, `X-GitHub-Sender`, etc.
- **Heuristic**: "Meaningful" = Body length > 10 words AND NOT (template patterns like "Unsubscribe", "View in browser").
- **Collapse**: If `Time(Msg_N) - Time(Msg_N-1) < 10 mins` AND `Sender(Msg_N) == Sender(Msg_N-1)`, merge bodies.

### 2.2. Budget, Timeline, Intent

**Regex Patterns (High Precision):**

- **Budget**: `(?i)(budget|cost|price|quote|rate)\s*(is|of|around|approx|~)?\s*[\$€£]?\d+(?:[kK]|\d{3})?`
- **Timeline**: `(?i)(start|begin|launch|live|deadline)\s*(by|in|on|before|after)\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|next week|next month|Q[1-4])`
- **Constraints**: `(?i)(need|must|have to|blocking|waiting on|approval|sign-off)`

**Embedding Classification (Recall):**

- Encode sentence. Calculate cosine similarity with anchors:
  - "We have a budget of..."
  - "We need to launch by..."
  - "We are ready to buy."
- Threshold: > 0.6 similarity.

### 2.3. Commitment Tracking

**Founder Commitments (Regex):**

- `(?i)(I'll|I will|Let me|I can)\s+(send|provide|check|draft|update|follow up)`
- `(?i)(expect|look for)\s+(a|the)\s+(draft|proposal|update)`

**Due Date Extraction:**

- Parse "by [Date]", "on [Date]", "next [Day]".

### 2.4. Sentiment Trend

- **Model**: `all-MiniLM-L6-v2`.
- **Anchors**:
  - Positive: "Great", "Sounds good", "Excited", "Thanks", "Looking forward".
  - Negative: "Unsubscribe", "Stop", "Not interested", "Too expensive", "Bad".
  - Neutral: "Received", "Okay", "Will check".
- **Trend**: Calculate moving average of sentiment scores (last 5 messages).
  - Slope > +0.1 → "warming"
  - Slope < -0.1 → "cooling"
  - Else → "flat"

## 3. Lightweight ML Components

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
  - Size: ~80MB.
  - Inference: ~10-20ms per sentence on CPU.
  - Usage: Intent classification, Sentiment scoring.
- **Tokenizer**: Standard HuggingFace tokenizer for the model.
- **No external APIs**.

## 4. JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "contact_email": { "type": "string", "format": "email" },
    "last_three_interactions": {
      "type": "array",
      "maxItems": 3,
      "items": {
        "type": "object",
        "properties": {
          "timestamp": { "type": "string", "format": "date-time" },
          "sender": { "type": "string" },
          "summary": { "type": "string" }
        }
      }
    },
    "budget": { "type": ["string", "null"] },
    "timeline": { "type": ["string", "null"] },
    "constraints": { "type": ["string", "null"] },
    "commitments_made": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "commitment": { "type": "string" },
          "due_date": { "type": ["string", "null"] }
        }
      }
    },
    "sentiment_trend": { "type": "string", "enum": ["warming", "cooling", "flat", "oscillating"] },
    "opportunity_stage": { "type": "string" },
    "requires_reply": { "type": "boolean" },
    "notes": { "type": "string" }
  },
  "required": ["contact_email"]
}
```

## 5. Failure-Mode Analysis

| Failure Case | Detection | Mitigation |
| :--- | :--- | :--- |
| **Missing Data** | Regex returns no matches. | Field set to `null`. System does not guess. |
| **Ambiguous Date** | "Next Tuesday" vs "Tuesday". | Parse relative to email timestamp. Default to nearest future date. |
| **False Positive Commitment** | "I'll see what I can do" (vague). | Filter out low-confidence matches or mark as "potential". |
| **Spam Leakage** | Vendor email passes filter. | Sentiment likely "neutral". No commitments found. Low impact. |
| **Slow Processing** | Thread > 100 messages. | Process only last 20 messages for sentiment/context. Full scan only for hard facts (budget). |

## 6. Benchmarks (Target)

- **Load Time**: < 50ms (Model loading).
- **Inference**: < 20ms per sentence.
- **Throughput**: > 100 contacts/minute on standard laptop CPU.
- **Memory**: < 500MB RAM peak.

## 7. Integration Notes

- **Input**: Stream rows from Postgres `emails` table.
  - Query: `SELECT * FROM emails WHERE contact_email = :email ORDER BY timestamp ASC`.
- **Trigger**: Run on new email arrival (webhook or polling).
- **Storage**: Save JSON to local disk `relationships/{email_hash}.json` or update a `jsonb` column in Postgres.
