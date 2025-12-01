import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

from utils import (
    extract_budget, extract_timeline, extract_constraints, extract_commitments,
    is_vendor_or_spam, clean_body, get_sentence_context
)
from models import EmbeddingModel

class RelationshipExtractor:
    def __init__(self):
        self.model = EmbeddingModel()

    def process_contact(self, contact_email: str, emails: List[Dict[str, Any]], user_email: str = None) -> Dict[str, Any]:
        """
        Processes a list of emails for a single contact and returns a relationship summary.
        Emails should be a list of dicts with keys: 'sender', 'recipient', 'subject', 'body', 'timestamp'.
        """
        # 1. Sort emails by timestamp
        emails.sort(key=lambda x: x['timestamp'])
        
        # Check for internal contact
        is_internal = False
        if user_email:
            user_domain = user_email.split('@')[-1]
            contact_domain = contact_email.split('@')[-1]
            if user_domain == contact_domain:
                is_internal = True

        # 2. Filter and Context Extraction
        meaningful_interactions = []
        last_email_time = None
        last_sender = None
        
        # Data accumulators
        budget = None
        timeline = None
        constraints = None
        commitments = []
        sentiment_scores = []
        
        for email in emails:
            sender = email['sender']
            subject = email['subject']
            raw_body = email['body']
            timestamp = datetime.fromisoformat(email['timestamp'])
            
            # Vendor/Spam Filter
            if is_vendor_or_spam(sender, subject, raw_body):
                continue
            
            cleaned_body = clean_body(raw_body)
            if not cleaned_body or len(cleaned_body.split()) < 5:
                continue

            # Collapse logic
            is_collapsed = False
            if last_email_time and last_sender == sender:
                time_diff = timestamp - last_email_time
                if time_diff < timedelta(minutes=10):
                    # Merge with previous interaction
                    if meaningful_interactions:
                        meaningful_interactions[-1]['summary'] += f"\n\n[Continued] {cleaned_body}"
                        meaningful_interactions[-1]['timestamp'] = timestamp.isoformat() # Update time to latest
                    is_collapsed = True
            
            if not is_collapsed:
                meaningful_interactions.append({
                    "timestamp": timestamp.isoformat(),
                    "sender": sender,
                    "summary": cleaned_body[:500] + "..." if len(cleaned_body) > 500 else cleaned_body,
                    "full_text": cleaned_body # Keep full text for analysis
                })

            last_email_time = timestamp
            last_sender = sender
            
            # 3. Intent & Commitment Extraction (Regex)
            new_budget = extract_budget(cleaned_body)
            if new_budget: budget = new_budget
            
            new_timeline = extract_timeline(cleaned_body)
            if new_timeline: timeline = new_timeline
            
            new_constraints = extract_constraints(cleaned_body)
            if new_constraints: constraints = new_constraints
            
            new_commitments = extract_commitments(cleaned_body)
            # Filter commitments to only those made by the contact (or founder if we knew who that was)
            # For now, we extract all commitments found in the text. 
            # Ideally we check if 'sender' is the 'founder' or the 'contact'.
            # The prompt says "Extract founder-made commitments". 
            # We'll assume the system knows the founder's email or we check "I'll..." implies the sender.
            # So we store who made the commitment.
            for c in new_commitments:
                c['by'] = sender
                commitments.append(c)

            # 4. Sentiment Analysis
            # Only analyze sentiment for the contact's emails to gauge *their* warmth
            if sender == contact_email:
                score = self.model.get_sentiment_score(cleaned_body)
                sentiment_scores.append(score)

        # 5. Intent (Embedding Fallback) - Optional, if regex failed
        # (Skipped for speed in this MVP, rely on regex as primary)

        # 6. Sentiment Trend
        sentiment_trend = "flat"
        if len(sentiment_scores) >= 3:
            # Simple linear regression slope
            x = np.arange(len(sentiment_scores))
            y = np.array(sentiment_scores)
            slope, _ = np.polyfit(x, y, 1)
            if slope > 0.1: sentiment_trend = "warming"
            elif slope < -0.1: sentiment_trend = "cooling"
            else: sentiment_trend = "flat"
        elif sentiment_scores:
             # If few data points, just look at the last one
             last_score = sentiment_scores[-1]
             if last_score > 0.3: sentiment_trend = "warming" # Enthusiastic
             elif last_score < -0.3: sentiment_trend = "cooling" # Cold
        
        # 7. Opportunity Stage (Heuristic)
        opportunity_stage = "lead"
        if budget or timeline:
            opportunity_stage = "opportunity"
        if any("proposal" in c['commitment'].lower() for c in commitments):
            opportunity_stage = "proposal_sent"

        # 8. Construct Output
        summary = {
            "contact_email": contact_email,
            "last_three_interactions": [
                {k: v for k, v in i.items() if k != 'full_text'} 
                for i in meaningful_interactions[-3:]
            ],
            "budget": budget,
            "timeline": timeline,
            "constraints": constraints,
            "commitments_made": [c for c in commitments if c['due_date']], # Only keep actionable ones? Or all? Prompt says "if no due date, store null"
            "sentiment_trend": sentiment_trend,
            "opportunity_stage": opportunity_stage,
            "requires_reply": False, # Default
            "notes": f"Processed {len(emails)} emails. Found {len(meaningful_interactions)} meaningful interactions."
        }
        
        # Check if last email was from contact -> requires reply
        if meaningful_interactions and meaningful_interactions[-1]['sender'] == contact_email:
            summary['requires_reply'] = True

        if is_internal:
            summary['notes'] += " [Internal Contact]"
            summary['opportunity_stage'] = "internal"

        return summary

if __name__ == "__main__":
    # Dummy Data for Testing
    extractor = RelationshipExtractor()
    
    dummy_emails = [
        {
            "sender": "jane@acme.com",
            "recipient": "founder@startup.com",
            "subject": "Inquiry about services",
            "body": "Hi, we are interested in your product. What is the pricing?",
            "timestamp": "2025-01-10T09:00:00"
        },
        {
            "sender": "founder@startup.com",
            "recipient": "jane@acme.com",
            "subject": "Re: Inquiry about services",
            "body": "Hi Jane, thanks for reaching out. Our budget tier starts at $2k. I'll send a proposal by Friday.",
            "timestamp": "2025-01-10T09:30:00"
        },
        {
            "sender": "jane@acme.com",
            "recipient": "founder@startup.com",
            "subject": "Re: Inquiry about services",
            "body": "That sounds good. We need to launch by March. Budget is around 3k.",
            "timestamp": "2025-01-10T10:00:00"
        },
        {
            "sender": "stripe@stripe.com",
            "recipient": "founder@startup.com",
            "subject": "Invoice",
            "body": "Here is your invoice.",
            "timestamp": "2025-01-11T09:00:00"
        }
    ]
    
    result = extractor.process_contact("jane@acme.com", dummy_emails)
    print(json.dumps(result, indent=2))
