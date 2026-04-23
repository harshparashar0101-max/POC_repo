import os

from jira import JIRA
from datetime import datetime

import smtplib
from email.message import EmailMessage

# =========================
# JIRA CONFIGURATION
# =========================
JIRA_URL = "https://mayankkhede.atlassian.net"
EMAIL = "harsh.parashar0101@gmail.com"
API_TOKEN = os.getenv("JIRA_API_TOKEN")

JQL = """
project = LOGI
AND type IN (Bug, Story, "Tech Debt")
AND sprint = 2
AND assignee IN (6327496e14c6b4b22109a627, 712020:e0a725f4-f6ff-4a25-b5b2-6db040fa58ca)
ORDER BY created DESC
"""

COMPLETED_STATUSES = ["QA-Completed", "Closed"]


# =========================
# HELPER FUNCTIONS
# =========================
def jira_date_to_date(date_str):
    """
    Convert Jira datetime string to Python date.
    Example Jira date: 2026-04-08T10:15:22.000+0530
    """
    return datetime.strptime(date_str[:10], "%Y-%m-%d").date()


def is_today(date_str):
    """
    Check if given Jira date is today's date.
    """
    return jira_date_to_date(date_str) == datetime.now().date()


def status_changed_today(jira_conn, issue, target_statuses):
    """
    Return True if issue status changed to one of target_statuses today.
    Used only when current status is QA-Completed or Closed.
    """
    full_issue = jira_conn.issue(issue.key, expand="changelog")

    for history in full_issue.changelog.histories:
        for item in history.items:
            if item.field == "status" and item.toString in target_statuses:
                if is_today(history.created):
                    return True
    return False


def should_include_issue(jira_conn, issue):
    """
    Final inclusion rule:
    - If status is NOT QA-Completed or Closed -> always include
    - If status is QA-Completed or Closed -> include only if status changed today
    """
    current_status = issue.fields.status.name

    if current_status not in COMPLETED_STATUSES:
        return True

    return status_changed_today(jira_conn, issue, COMPLETED_STATUSES)


def get_today_subtasks(jira_conn, issue):
    """
    Get child subtasks created today under parent Story / Tech Debt.
    """
    today_subtasks = []
    subtasks = getattr(issue.fields, "subtasks", [])

    for sub in subtasks:
        sub_issue = jira_conn.issue(sub.key)

        # If needed, you can uncomment this line to strictly allow only "Sub Issue"
        # if sub_issue.fields.issuetype.name != "Sub Issue":
        #     continue

        if is_today(sub_issue.fields.created):
            today_subtasks.append(sub_issue)

    return today_subtasks


def build_report(jira_conn, issues):
    """
    Build final report text.
    """
    report_lines = []
    story_tech_section = []
    bug_section = []

    report_lines.append("Hello Team,")
    report_lines.append("")
    report_lines.append("Below are the Jira items for today:")
    report_lines.append("")

    for issue in issues:
        issue_type = issue.fields.issuetype.name
        key = issue.key
        summary = issue.fields.summary
        status = issue.fields.status.name

        # Apply main inclusion logic
        if not should_include_issue(jira_conn, issue):
            continue

        if issue_type in ["Story", "Tech Debt"]:
            subtasks_today = get_today_subtasks(jira_conn, issue)

            if subtasks_today:
                story_tech_section.append(f"{key} : {summary}")
                story_tech_section.append(f"Status: {status} and reported below issue")

                for sub in subtasks_today:
                    story_tech_section.append(f"{sub.key} : {sub.fields.summary}")

                story_tech_section.append("")

            else:
                story_tech_section.append(f"{key} : {summary}")
                story_tech_section.append(f"Status: {status}")
                story_tech_section.append("")

        elif issue_type == "Bug":
            bug_section.append(f"{key} : {summary}")
            bug_section.append(f"Status: {status}")
            bug_section.append("")

    report_lines.append("Story / Tech Debt:")
    report_lines.append("")

    if story_tech_section:
        report_lines.extend(story_tech_section)
    else:
        report_lines.append("No Story / Tech Debt items found.")
        report_lines.append("")

    report_lines.append("Standalone Bugs:")
    report_lines.append("")

    if bug_section:
        report_lines.extend(bug_section)
    else:
        report_lines.append("No Bugs found.")
        report_lines.append("")

    report_lines.append("Please let us know if any more information is required.")
    report_lines.append("")
    report_lines.append("Thanks,")
    report_lines.append("Harsh")

    return "\n".join(report_lines)


def send_email(report_text, file_name):
    sender_email = "harsh.parashar0101@gmail.com"
    sender_password = os.getenv("Email API Token")  # ⚠️ Replace this
    receiver_email = "c-harsh.parasher@on24.com"   # ⚠️ Replace this

    msg = EmailMessage()
    msg["Subject"] = f"Jira Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # Email body
    msg.set_content(report_text)

    # Attach file
    with open(file_name, "rb") as f:
        file_data = f.read()
        msg.add_attachment(file_data,
                           maintype="application",
                           subtype="octet-stream",
                           filename=file_name)

    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

    print("Email sent successfully!")


# =========================
# MAIN EXECUTION
# =========================
def main():
    try:
        print("Connecting to Jira...")
        jira_conn = JIRA(server=JIRA_URL, basic_auth=(EMAIL, API_TOKEN))
        print("Jira connection successful.")

        print("Running JQL...")
        issues = jira_conn.search_issues(JQL, maxResults=100)
        print(f"Total issues fetched from JQL: {len(issues)}")

        final_report = build_report(jira_conn, issues)

        print("\n================ FINAL REPORT ================\n")
        print(final_report)

        today_str = datetime.now().strftime("%Y-%m-%d")
        file_name = f"jira_report_{today_str}.txt"

        with open(file_name, "w", encoding="utf-8") as file:
            file.write(final_report)

        print(f"\nReport saved as: {file_name}")

        send_email(final_report, file_name)

    except Exception as e:
        print("Error occurred:")
        print(str(e))


if __name__ == "__main__":
    main()