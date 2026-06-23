# NGO Kosmos Tabir — Outreach Campaign Guide

This directory contains the necessary resources to run a professional, targeted, and domain-safe email campaign to European solar developers, recycling networks, logistics firms, and corporate foundations.

---

## 📂 Directory Structure

*   [email_templates.md](file:///Users/admin/Documents/ct%20le/outreach/email_templates.md) — The raw email templates for the 4 campaign target profiles.
*   [roadmap.md](file:///Users/admin/Documents/ct%20le/outreach/roadmap.md) — Strategic roadmap detailing logistics and field deployment.
*   [presentation.html](file:///Users/admin/Documents/ct%20le/outreach/presentation.html) — Interactive 8-slide presentation deck.
*   [presentation_style.css](file:///Users/admin/Documents/ct%20le/outreach/presentation_style.css) — Stylesheet with print layout rules for PDF export.
*   [targets.csv](file:///Users/admin/Documents/ct%20le/outreach/targets.csv) — Target contact list with country codes, emails, categories, and sending status.
*   [send_outreach.py](file:///Users/admin/Documents/ct%20le/outreach/send_outreach.py) — Smart python script to generate drafts or dispatch emails.

---

## 🛠️ Step 1: Secure SMTP Setup

To enable automated sending when you are ready, add your SMTP credentials to the `.env` file in the main project directory. If the file doesn't exist, create it.

Open your main [`.env` file](file:///Users/admin/Documents/ct%20le/.env) and append:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@domain.com
SMTP_PASSWORD=your_app_password
SENDER_NAME=Nazar Botvynko
SENDER_EMAIL=denny@kosmostabir.org
```

> [!NOTE]
> If you are using Gmail, you must generate a 16-character **App Password** from your Google Account security settings rather than using your primary login password.

---

## 📑 Step 2: Export the Presentation to PDF

To attach a premium 16:9 PDF version of the presentation to your emails:
1. Open the [presentation.html](file:///Users/admin/Documents/ct%20le/outreach/presentation.html) file in Google Chrome.
2. Press **Cmd + P** (macOS) or **Ctrl + P** (Windows) to open the print dialog.
3. Apply the following settings:
    *   **Destination**: Save as PDF
    *   **Layout**: Landscape
    *   **Paper Size**: A4 or Letter (the CSS will scale the presentation dynamically)
    *   **Margins**: None
    *   **Headers and Footers**: Unchecked (Disabled)
    *   **Background Graphics**: Checked (Enabled) — *Crucial to preserve background colors*
4. Click **Save** and name it `NGO_Kosmos_Tabir_Presentation.pdf`. Save it in your files for quick attachment.

---

## 🔍 Step 3: Run in Dry-Run Mode (Preview Drafts)

Always preview your emails before sending a single byte. To render your templates with target data and generate local draft files:
1. Open your terminal in this workspace.
2. Run the following command:
    ```bash
    python outreach/send_outreach.py --dry-run --limit 20
    ```
3. Open the newly created `outreach/drafts/` folder. You will find text files containing the exact headers, subjects, and personalized email body for every company in `targets.csv`.

Review these files to make sure names, placeholders, and links look correct.

---

## 🚀 Step 4: Run the Smart Campaign

Once the materials are fully approved and you are ready to send:
1. Run the script in active mode with a controlled daily sending limit (e.g. 5 or 10 emails):
    ```bash
    python outreach/send_outreach.py --limit 5
    ```
2. The script will:
    *   Validate SMTP settings.
    *   Verify each email and prompt you for confirmation if `Priority` is `1` (High-touch targets).
    *   Send the email and immediately record `Status=sent` and `SentDate` in `targets.csv`.
    *   Apply a randomized delay (90 to 240 seconds) between sends to mimic human behavior and bypass spam filters.

If you ever need to stop the script, press **Ctrl + C**. The CSV state is saved instantly after every single email, so you will never send duplicate emails if you resume later.
