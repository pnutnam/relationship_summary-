import json
from sqlalchemy import create_engine, text
from collections import defaultdict
from extractor import RelationshipExtractor
import re

# Configuration
CONNECTION_STRING = 'postgresql://ueemr8ld2rv7jl:pbd758327b7bcfbf2eb04abaf31f6ef6fe52f44b274d267927767b0e0ea3b359b@ec2-34-201-142-49.compute-1.amazonaws.com:5432/dcqh91qqh57r0v'
TARGET_USER_IDS = [2082, 2080, 2025, 2019, 2011]

def get_email_address(raw_string):
    """Extracts email from 'Name <email@domain.com>' or just 'email@domain.com'"""
    if not raw_string: return ""
    match = re.search(r'<([^>]+)>', raw_string)
    if match:
        return match.group(1).lower()
    return raw_string.strip().lower()

def analyze_data():
    engine = create_engine(CONNECTION_STRING)
    extractor = RelationshipExtractor()
    
    all_summaries = {}

    with engine.connect() as connection:
        for user_id in TARGET_USER_IDS:
            print(f"Processing User ID: {user_id}...")
            
            # Fetch messages
            query = text("SELECT * FROM account_message WHERE user_id = :uid")
            result = connection.execute(query, {"uid": user_id})
            rows = result.fetchall()
            
            if not rows:
                print(f"  No messages found for user {user_id}")
                continue
                
            # Group by contact
            # First, identify the user's email (heuristic: most frequent sender/recipient)
            email_counts = defaultdict(int)
            parsed_messages = []
            
            for row in rows:
                meta = row.metadata
                if not meta: continue
                
                sender = get_email_address(meta.get('sender', ''))
                recipient = get_email_address(meta.get('recipient', ''))
                
                email_counts[sender] += 1
                email_counts[recipient] += 1
                
                parsed_messages.append({
                    "sender": sender,
                    "recipient": recipient,
                    "subject": meta.get('subject_line', ''),
                    "body": row.body or "",
                    "timestamp": row.sent_date.isoformat() if row.sent_date else ""
                })
            
            if not email_counts:
                continue
                
            user_email = max(email_counts, key=email_counts.get)
            print(f"  Identified User Email: {user_email}")
            
            # Group messages by the *other* person
            contact_threads = defaultdict(list)
            for msg in parsed_messages:
                other = msg['recipient'] if msg['sender'] == user_email else msg['sender']
                if other and other != user_email:
                    contact_threads[other].append(msg)
            
            print(f"  Found {len(contact_threads)} contacts.")
            
            # Process top 5 contacts with most messages to save time/output space
            sorted_contacts = sorted(contact_threads.keys(), key=lambda k: len(contact_threads[k]), reverse=True)[:5]
            
            user_summaries = []
            for contact in sorted_contacts:
                print(f"    Analyzing contact: {contact} ({len(contact_threads[contact])} msgs)")
                summary = extractor.process_contact(contact, contact_threads[contact], user_email=user_email)
                if summary: # process_contact might return None if filtered
                    user_summaries.append(summary)
            
            all_summaries[user_id] = user_summaries

    # Save results to JSON
    with open("real_data_analysis.json", "w") as f:
        json.dump(all_summaries, f, indent=2)
    print("Analysis complete. Saved to real_data_analysis.json")

    # Save results to CSV
    import csv
    with open("real_data_analysis.csv", "w", newline='') as csvfile:
        fieldnames = ['user_id', 'contact_email', 'opportunity_stage', 'budget', 'timeline', 'constraints', 'sentiment_trend', 'requires_reply', 'notes', 'last_interaction_summary', 'commitments']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for user_id, summaries in all_summaries.items():
            for summary in summaries:
                last_interaction = summary['last_three_interactions'][-1]['summary'] if summary['last_three_interactions'] else ""
                commitments_str = "; ".join([f"{c['commitment']} (Due: {c['due_date']})" for c in summary['commitments_made']])
                
                writer.writerow({
                    'user_id': user_id,
                    'contact_email': summary['contact_email'],
                    'opportunity_stage': summary['opportunity_stage'],
                    'budget': summary['budget'],
                    'timeline': summary['timeline'],
                    'constraints': summary['constraints'],
                    'sentiment_trend': summary['sentiment_trend'],
                    'requires_reply': summary['requires_reply'],
                    'notes': summary['notes'],
                    'last_interaction_summary': last_interaction.replace('\n', ' ')[:200], # Truncate for CSV readability
                    'commitments': commitments_str
                })
    print("CSV export complete. Saved to real_data_analysis.csv")

if __name__ == "__main__":
    analyze_data()
