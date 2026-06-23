#!/usr/bin/env python3
import os
import sys
import csv
import time
import random
import re
import argparse
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# File paths relative to script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
TARGETS_FILE = os.path.join(SCRIPT_DIR, 'targets.csv')
TEMPLATES_FILE = os.path.join(SCRIPT_DIR, 'email_templates.md')
ENV_FILE = os.path.join(WORKSPACE_DIR, '.env')
DRAFTS_DIR = os.path.join(SCRIPT_DIR, 'drafts')

# Load env variables manually (simple parser to avoid dependency issues)
def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        env[key.strip()] = val.strip()
                        # Also write to os.environ
                        os.environ[key.strip()] = val.strip()
    return env

# Parse templates from markdown file
def parse_templates():
    if not os.path.exists(TEMPLATES_FILE):
        print(f"❌ Error: Templates file not found at {TEMPLATES_FILE}")
        sys.exit(1)
        
    with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    templates = {}
    # Split by markdown Level 2 Headers (e.g. ## 1. Solar Manufacturers)
    sections = re.split(r'##\s+\d+\.\s+', content)
    
    for sec in sections[1:]:
        lines = sec.split('\n')
        header_title = lines[0].lower()
        
        # Extract content inside ```text ... ``` code blocks
        code_block = re.search(r'```text\n(.*?)```', sec, re.DOTALL)
        if code_block:
            body = code_block.group(1).strip()
            
            # Map section header keywords to category keys in targets.csv
            if any(k in header_title for k in ['manufacturer', 'installer', 'distributor']):
                templates['manufacturer'] = body
            elif any(k in header_title for k in ['recycling', 'recycler', 'waste']):
                templates['recycler'] = body
            elif any(k in header_title for k in ['logistics', 'transport', 'shipping']):
                templates['logistics'] = body
            elif any(k in header_title for k in ['foundation', 'grant', 'fund', 'csr']):
                templates['fund'] = body
                
    return templates

# Safe file names helper
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name.replace(' ', '_'))

# Read the contacts CSV database
def read_targets():
    if not os.path.exists(TARGETS_FILE):
        print(f"❌ Error: Targets CSV not found at {TARGETS_FILE}")
        sys.exit(1)
        
    targets = []
    with open(TARGETS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(row)
    return targets

# Save/Update the contacts CSV database (preserves headers and writes immediately)
def save_targets(targets):
    if not targets:
        return
    headers = list(targets[0].keys())
    with open(TARGETS_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(targets)

# Create SMTP Connection
def get_smtp_connection(env):
    host = env.get('SMTP_HOST')
    port = env.get('SMTP_PORT', '587')
    user = env.get('SMTP_USER')
    password = env.get('SMTP_PASSWORD')
    
    if not host or not user or not password:
        print("\n❌ Error: SMTP Configuration is incomplete in your .env file.")
        print("Please check that SMTP_HOST, SMTP_USER, and SMTP_PASSWORD are set.")
        sys.exit(1)
        
    port = int(port)
    print(f"Connecting to SMTP server {host}:{port}...")
    
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()
            
        server.login(user, password)
        return server
    except Exception as e:
        print(f"❌ SMTP Connection failed: {e}")
        sys.exit(1)

# Main orchestrator
def main():
    parser = argparse.ArgumentParser(description='Smart Email Outreach Sender for NGO Kosmos Tabir')
    parser.add_argument('--dry-run', action='store_true', help='Generate local drafts in outreach/drafts/ without sending')
    parser.add_argument('--limit', type=int, default=5, help='Max number of emails to send in this session')
    parser.add_argument('--delay-min', type=int, default=90, help='Min delay between emails in seconds')
    parser.add_argument('--delay-max', type=int, default=240, help='Max delay between emails in seconds')
    parser.add_argument('--interactive', action='store_true', help='Ask for confirmation before sending each email')
    args = parser.parse_args()

    # Load environment
    env = load_env()
    
    # Load templates and targets
    templates = parse_templates()
    targets = read_targets()
    
    print("=" * 70)
    print(f"🚀 NGO Kosmos Tabir — Outreach Automation (Mode: {'DRY RUN' if args.dry_run else 'ACTIVE SEND'})")
    print(f"📋 Loaded {len(targets)} targets. Limit for this run: {args.limit} emails.")
    print("=" * 70)
    
    # Counts
    processed_count = 0
    pending_count = sum(1 for t in targets if t.get('Status') == 'pending')
    
    if pending_count == 0:
        print("🎉 No pending targets in database. All emails sent or skipped!")
        return
        
    print(f"Found {pending_count} pending targets.")
    
    # Initialize SMTP only if active send
    smtp_server = None
    if not args.dry_run:
        smtp_server = get_smtp_connection(env)
        
    try:
        for idx, target in enumerate(targets):
            if target.get('Status') != 'pending':
                continue
                
            if processed_count >= args.limit:
                print(f"\n⚠️ Reached limit of {args.limit} emails for this session. Stopping.")
                break
                
            company = target.get('Company')
            email = target.get('Email')
            category = target.get('Category')
            contact_name = target.get('ContactName', 'Partnership Coordinator')
            priority = target.get('Priority', '2')
            
            # Load matching template
            template = templates.get(category)
            if not template:
                print(f"⚠️ Warning: No template found for category '{category}' (Company: {company}). Skipping.")
                continue
                
            # Fallback for contact name
            if not contact_name.strip():
                contact_name = "Partnership Coordinator"
                
            # Compile email content by parsing variables
            body = template.replace('{company_name}', company).replace('{contact_name}', contact_name)
            
            # Extract Subject Line from the template text (first line starting with 'Subject:')
            subject = "Partnership Inquiry — NGO Kosmos Tabir"
            match_subject = re.match(r'^Subject:\s*(.*)', body)
            if match_subject:
                subject = match_subject.group(1).strip()
                # Remove Subject line from the body
                body = body[match_subject.end():].strip()
                
            if args.dry_run:
                # Dry run: Write draft to local file
                os.makedirs(DRAFTS_DIR, exist_ok=True)
                safe_company = sanitize_filename(company)
                draft_path = os.path.join(DRAFTS_DIR, f"draft_{safe_company}.txt")
                
                with open(draft_path, 'w', encoding='utf-8') as df:
                    df.write(f"TO: {email}\n")
                    df.write(f"SUBJECT: {subject}\n")
                    df.write(f"CATEGORY: {category} | PRIORITY: {priority}\n")
                    df.write("-" * 50 + "\n")
                    df.write(body)
                    
                print(f"📝 [DRY RUN] Generated draft for {company} ({email}) -> outreach/drafts/draft_{safe_company}.txt")
                processed_count += 1
                
            else:
                # Active Send Mode
                sender_name = env.get('SENDER_NAME', 'Nazar Botvynko')
                sender_email = env.get('SENDER_EMAIL', env.get('SMTP_USER'))
                
                print(f"\n[{processed_count + 1}/{args.limit}] Preparing email to: {company} ({email})")
                print(f"Subject: {subject}")
                print(f"Priority: {priority} (1=High, 2=Medium, 3=Low)")
                
                # Double check for Priority 1 or Interactive mode
                if args.interactive or priority == '1':
                    confirm = input(f"❓ Confirm sending email to {company}? (y/n/skip): ").strip().lower()
                    if confirm != 'y':
                        if confirm == 'skip':
                            print(f"Skipped {company}.")
                            target['Status'] = 'skipped'
                            save_targets(targets)
                        else:
                            print("Send cancelled. Exiting script.")
                            break
                        continue
                
                # Build Email Message
                msg = MIMEMultipart()
                msg['From'] = f"{sender_name} <{sender_email}>"
                msg['To'] = email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                # Send email
                try:
                    smtp_server.sendmail(sender_email, [email], msg.as_string())
                    print(f"✅ Email successfully sent to {company}!")
                    
                    # Update status in CSV immediately
                    target['Status'] = 'sent'
                    target['SentDate'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_targets(targets)
                    processed_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to send to {company}: {e}")
                    # Update status as failed (so we don't loop infinitely, or keep pending to retry)
                    # For safety, let's keep it pending but stop execution
                    print("Stopping campaign to verify SMTP settings.")
                    break
                    
                # Delay between sends to protect domain reputation
                if processed_count < args.limit and idx < len(targets) - 1:
                    sleep_time = random.randint(args.delay_min, args.delay_max)
                    print(f"⏱ Sleeping for {sleep_time} seconds before next send...")
                    time.sleep(sleep_time)
                    
    finally:
        # Close SMTP connection if active
        if smtp_server:
            try:
                smtp_server.quit()
                print("\n🔐 Closed SMTP connection.")
            except:
                pass
                
    print("=" * 70)
    print(f"🏁 Campaign Session Finished. Processed {processed_count} targets.")
    if args.dry_run:
        print(f"📂 Review generated drafts in: {DRAFTS_DIR}/")
    print("=" * 70)

if __name__ == '__main__':
    main()
