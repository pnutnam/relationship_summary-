import re
from datetime import datetime
from typing import List, Optional

# Regex Patterns
BUDGET_PATTERN = re.compile(r"(?i)(budget|cost|price|quote|rate)\s*(?:is|of|around|approx|~|\s+)*[\$€£]?\d+(?:[kK]|\d{3})?")
TIMELINE_PATTERN = re.compile(r"(?i)(start|begin|launch|live|deadline)\s*(by|in|on|before|after)\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|next week|next month|Q[1-4])")
CONSTRAINT_PATTERN = re.compile(r"(?i)(need|must|have to|blocking|waiting on|approval|sign-off)")

COMMITMENT_PATTERN = re.compile(r"(?i)(I'll|I will|Let me|I can)\s+(send|provide|check|draft|update|follow up)")
COMMITMENT_NOUN_PATTERN = re.compile(r"(?i)(expect|look for)\s+(a|the)\s+(draft|proposal|update)")

DUE_DATE_PATTERN = re.compile(r"(?i)(by|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|next week|next month|tomorrow|tonight|\d{1,2}[/-]\d{1,2})")

# Vendor/Spam Filters
VENDOR_DOMAINS = {
    "aws.amazon.com", "stripe.com", "notion.so", "slack.com", "github.com",
    "squarespace.com", "hubspot.com", "mailchimp.com", "paypal.com",
    "linkedin.com", "atlassian.com", "zoom.us", "calendly.com"
}

SPAM_SUBJECTS = [
    "receipt", "alert", "confirmation", "invoice", "verification", "security code",
    "digest", "newsletter", "weekly", "daily", "update from"
]

def extract_budget(text: str) -> Optional[str]:
    match = BUDGET_PATTERN.search(text)
    return match.group(0) if match else None

def extract_timeline(text: str) -> Optional[str]:
    match = TIMELINE_PATTERN.search(text)
    return match.group(0) if match else None

def extract_constraints(text: str) -> Optional[str]:
    match = CONSTRAINT_PATTERN.search(text)
    return match.group(0) if match else None

def extract_commitments(text: str) -> List[dict]:
    commitments = []
    # Check verb-based commitments
    for match in COMMITMENT_PATTERN.finditer(text):
        sentence = get_sentence_context(text, match.start(), match.end())
        due_date = extract_due_date(sentence)
        commitments.append({
            "commitment": sentence.strip(),
            "due_date": due_date
        })
    
    # Check noun-based commitments if no verb-based found (to avoid duplicates if they overlap)
    if not commitments:
        for match in COMMITMENT_NOUN_PATTERN.finditer(text):
            sentence = get_sentence_context(text, match.start(), match.end())
            due_date = extract_due_date(sentence)
            commitments.append({
                "commitment": sentence.strip(),
                "due_date": due_date
            })
            
    return commitments

def extract_due_date(text: str) -> Optional[str]:
    match = DUE_DATE_PATTERN.search(text)
    return match.group(0) if match else None

def get_sentence_context(text: str, start: int, end: int, window: int = 50) -> str:
    """Extracts the surrounding sentence or a window of text."""
    # Simple heuristic: find nearest punctuation
    sent_start = text.rfind('.', 0, start) + 1
    if sent_start < 0: sent_start = 0
    
    sent_end = text.find('.', end)
    if sent_end < 0: sent_end = len(text)
    
    return text[sent_start:sent_end+1]

def is_vendor_or_spam(sender_email: str, subject: str, body: str) -> bool:
    domain = sender_email.split('@')[-1].lower()
    if domain in VENDOR_DOMAINS:
        return True
    
    subject_lower = subject.lower()
    for spam_sub in SPAM_SUBJECTS:
        if spam_sub in subject_lower:
            return True
            
    if "unsubscribe" in body.lower()[-200:]: # Check footer
        return True
        
    return False

def clean_body(body: str) -> str:
    """Removes replies, signatures, and extra whitespace."""
    if not body: return ""
    
    lines = body.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Stop at standard signature delimiters
        if stripped in ["--", "__", "---"]:
            break
        # Stop at "On ... wrote:" or "From: ... Sent: ..." (Reply headers)
        if re.search(r"On .* wrote:", line):
            break
        if re.search(r"From:.*Sent:.*To:.*", line):
            break
        if re.search(r"[-]+\s*Forwarded message\s*[-]+", line, re.IGNORECASE):
            break
            
        # Heuristic for "Thanks,\nName" signature
        if stripped.lower() in ["thanks,", "best,", "regards,", "sincerely,", "cheers,"]:
            # If the next few lines are short, it's likely a signature. 
            # We'll just stop here for safety to avoid clutter.
            break
            
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines).strip()
