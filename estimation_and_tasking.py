
import os

print("EMAIL =", os.getenv("JIRA_EMAIL"))
print("TOKEN exists =", bool(os.getenv("JIRA_API_TOKEN")))
print("ENV KEYS SAMPLE =", [k for k in os.environ.keys() if "JIRA" in k])

import requests
from requests.auth import HTTPBasicAuth
import json

# ==========================================
# CONFIG
# ==========================================

BASE_URL = "https://mayankkhede.atlassian.net"
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
ASSIGNEE_ACCOUNT_ID = "6327496e14c6b4b22109a627"

# Final JQL for only 2 Story + 2 Tech Debt
JQL = 'project = LOGI  AND assignee = 6327496e14c6b4b22109a627 AND type IN (Story, "Tech Debt") AND sprint = 2 ORDER BY created DESC'

auth = HTTPBasicAuth(EMAIL, API_TOKEN)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# ==========================================
# SUBTASK TEMPLATES
# ==========================================

STORY_SUBTASKS = {
    "QALogiUS: Rework": None,
    "QALogiUS: Test Cases Execution to verify Data Integrity": "15h",
    "QALogiUS: Test Cases Execution on UI (desktops: on all major supported OS/browsers) to Verify functionality": "12h",
    "QALogiUS: Add features/scenarios to the acceptance criteria section": "5h",
    "QALogiUS: QA Release Readiness": None
}

TECHDEBT_SUBTASKS = {
    "QALogiTD: Rework": None,
    "QALogiTD: Test Cases Execution to verify Data Integrity": "15h",
    "QALogiTD: Test Cases Execution on UI (desktops: on all major supported OS/browsers) to Verify functionality": "12h",
    "QALogiTD: Add features/scenarios to the acceptance criteria section": "5h",
    "QALogiTD: QA Release Readiness": None
}

# ==========================================
# FETCH PARENT ISSUES
# ==========================================

def get_issues():
    url = f"{BASE_URL}/rest/api/3/search/jql"

    params = {
        "jql": JQL,
        "maxResults": 100,
        "fields": "summary,issuetype,subtasks"
    }

    response = requests.get(
        url,
        headers=headers,
        auth=auth,
        params=params
    )

    print("\n===== FETCH ISSUES DEBUG =====")
    print("Status Code:", response.status_code)
    print("Final URL:", response.url)
    print("Response:")
    print(response.text)
    print("===== END FETCH ISSUES DEBUG =====\n")

    if response.status_code != 200:
        print(" Failed to fetch issues from Jira")
        return []

    data = response.json()
    issues = data.get("issues", [])

    # Safety filter in Python
    filtered_issues = []
    for issue in issues:
        issue_type = issue.get("fields", {}).get("issuetype", {}).get("name")
        if issue_type in ["Story", "Tech Debt"]:
            filtered_issues.append(issue)

    print("Fetched issues from API:", len(issues))
    print("Filtered Story/Tech Debt issues:", len(filtered_issues))

    return filtered_issues

# ==========================================
# GET EXISTING SUBTASKS
# ==========================================

def get_existing_subtasks(issue_key):
    url = f"{BASE_URL}/rest/api/3/issue/{issue_key}"

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code != 200:
        print(f" Failed to fetch issue details for {issue_key}")
        print(response.text)
        return []

    data = response.json()
    subtasks = data.get("fields", {}).get("subtasks", [])

    existing_subtask_summaries = []
    for subtask in subtasks:
        summary = subtask.get("fields", {}).get("summary")
        if summary:
            existing_subtask_summaries.append(summary)

    return existing_subtask_summaries

# ==========================================
# CREATE SUBTASK
# ==========================================

def create_subtask(parent_key, summary):
    url = f"{BASE_URL}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {
                "key": "LOGI"
            },
            "parent": {
                "key": parent_key
            },
            "summary": summary,
            "issuetype": {
                "name": "Sub-task"
            },
            "assignee": {
                "accountId": ASSIGNEE_ACCOUNT_ID
            }
        }
    }

    response = requests.post(
        url,
        headers=headers,
        auth=auth,
        data=json.dumps(payload)
    )

    if response.status_code == 201:
        return response.json().get("key")
    else:
        print(f" Failed to create subtask: {summary} under {parent_key}")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        return None

# ==========================================
# ADD ESTIMATE
# ==========================================

def add_estimate(issue_key, estimate_value):
    if not estimate_value:
        return True

    url = f"{BASE_URL}/rest/api/3/issue/{issue_key}"

    payload = {
        "fields": {
            "timetracking": {
                "originalEstimate": estimate_value
            }
        }
    }

    response = requests.put(
        url,
        headers=headers,
        auth=auth,
        data=json.dumps(payload)
    )

    if response.status_code == 204:
        return True
    else:
        print(f" Failed to add estimate for {issue_key}")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        return False

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    issues = get_issues()

    total_created = 0
    total_skipped = 0

    print("\n===== START PROCESSING =====")

    for issue in issues:
        key = issue.get("key")
        issue_type = issue.get("fields", {}).get("issuetype", {}).get("name")
        summary = issue.get("fields", {}).get("summary")

        print(f"\n🔹 Processing Parent: {key} | {issue_type} | {summary}")

        if issue_type == "Story":
            subtask_map = STORY_SUBTASKS
        else:
            subtask_map = TECHDEBT_SUBTASKS

        existing_subtasks = get_existing_subtasks(key)

        print("Existing subtasks under parent:")
        if existing_subtasks:
            for sub in existing_subtasks:
                print("   -", sub)
        else:
            print("   - No existing subtasks")

        for subtask_summary, estimate in subtask_map.items():
            if subtask_summary in existing_subtasks:
                print(f" Skipped (already exists): {subtask_summary}")
                total_skipped += 1
                continue

            new_subtask_key = create_subtask(key, subtask_summary)

            if new_subtask_key:
                print(f" Created: {new_subtask_key} | {subtask_summary}")
                total_created += 1

                if estimate:
                    estimate_added = add_estimate(new_subtask_key, estimate)
                    if estimate_added:
                        print(f"    Estimate added: {estimate}")
                else:
                    print("    No estimate added (NA)")

    print("\n===== EXECUTION COMPLETED =====")
    print("Total parents processed:", len(issues))
    print("Total subtasks created:", total_created)
    print("Total subtasks skipped:", total_skipped)


    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, "estimation_report.txt")

    with open(report_path, "w", encoding="utf-8") as f:
     f.write("Jira Estimation Automation Report\n")
     f.write("=================================\n\n")
     f.write(f"Total parents processed: {len(issues)}\n")
     f.write(f"Total subtasks created: {total_created}\n")
     f.write(f"Total subtasks skipped: {total_skipped}\n")

# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    main()
