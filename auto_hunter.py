import json
import os
import subprocess
import shutil
import sys
import time

QUEUE_FILE = "bounty_queue.json"
ENV_FILE = ".env"
MAX_EXECUTION_TIME = 300


def clean_workspace():
    workspace_dir = "workspace"
    if os.path.exists(workspace_dir):
        try:
            shutil.rmtree(workspace_dir)
            print("Workspace cleared.")
        except OSError as exc:
            print(f"Could not fully clear workspace: {exc}")
    else:
        print("Workspace is already clean.")


def ensure_env_health(repo_name, issue_number=None):
    env_content = []
    found_repository = False

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as file:
            lines = file.readlines()
    else:
        lines = ["GEMINI_API_KEY=\n", "GITHUB_TOKEN=\n"]

    for line in lines:
        if line.startswith("TARGET_REPOSITORY="):
            env_content.append(f"TARGET_REPOSITORY={repo_name}\n")
            found_repository = True
        else:
            env_content.append(line)

    if not found_repository:
        env_content.append(f"TARGET_REPOSITORY={repo_name}\n")

    env_content = [
        line for line in env_content
        if not line.startswith("TARGET_ISSUE_NUMBER=")
    ]
    if issue_number is not None:
        env_content.append(f"TARGET_ISSUE_NUMBER={issue_number}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as file:
        file.writelines(env_content)


def run_main_process():
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        output, _ = process.communicate(timeout=MAX_EXECUTION_TIME)
        return process.returncode, output, False
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
        return None, output, True


def classify_result(return_code, output, timed_out):
    if timed_out:
        return "failed", "Execution took longer than 5 minutes"

    if "API Rate Limit" in output or "403" in output:
        return "rate_limited", "GitHub API rate limit detected"

    if "No open bounties found" in output or "404" in output:
        return "skipped", "No usable issue or repository was found"

    if return_code == 0 and "Pull Request live at:" in output:
        return "completed", "Pull request created successfully"

    return "failed", "Pipeline did not complete successfully"


def start_autonomous_hunt():
    print("AUTO-HUNTER ACTIVATED")
    print("=" * 70)

    if not os.path.exists(QUEUE_FILE):
        print("bounty_queue.json not found. Run python scout.py first.")
        return

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as file:
            queue = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load bounty queue: {exc}")
        return

    if not isinstance(queue, list):
        print("bounty_queue.json must contain a JSON list.")
        return

    pending_targets = [target for target in queue if target.get("status") == "pending"]

    if not pending_targets:
        print("Queue is empty. Run python scout.py to find new targets.")
        return

    print(f"Total pending targets: {len(pending_targets)}.\n")

    for target in pending_targets:
        repo = target.get("repo")
        if not repo or "/" not in repo:
            target["status"] = "failed"
            target["reason"] = "Invalid repository name"
            continue

        print(f"Starting target: {repo}")
        issue_number = target.get("issue_number")
        if issue_number is None:
            issue_url = target.get("url", "")
            issue_number = issue_url.rstrip("/").split("/")[-1] if issue_url else None
            if str(issue_number).isdigit():
                issue_number = int(issue_number)
            else:
                issue_number = None

        ensure_env_health(repo, issue_number)
        clean_workspace()

        try:
            return_code, output_log, timed_out = run_main_process()
            print(output_log, end="")
        except OSError as exc:
            return_code = None
            output_log = f"[SYSTEM] Process launch failed: {exc}"
            timed_out = False
            print(output_log)

        status, reason = classify_result(return_code, output_log, timed_out)

        if status == "rate_limited":
            print("GitHub API rate limit detected. Waiting 60 seconds.")
            target["status"] = "pending"
            target["reason"] = reason
            with open(QUEUE_FILE, "w", encoding="utf-8") as file:
                json.dump(queue, file, indent=4)
            time.sleep(60)
            continue

        target["status"] = status
        target["reason"] = reason

        with open(QUEUE_FILE, "w", encoding="utf-8") as file:
            json.dump(queue, file, indent=4)

        time.sleep(3)

    print("All pending targets processed.")


if __name__ == "__main__":
    start_autonomous_hunt()
