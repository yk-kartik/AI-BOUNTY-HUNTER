import logging
import os
import re
import sys

from config.settings import config
from utils.github_client import GitHubClient
from utils.api_client import BountyHunterAPI
from utils.patcher import apply_patch

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_target_file(repo_path, ai_provided_path):
    normalized_path = ai_provided_path.replace("\\\\", "/").strip().lstrip("/")
    if not normalized_path or normalized_path in {".", ".."}:
        logger.error("Invalid target file path: %s", ai_provided_path)
        return None

    repo_root = os.path.abspath(repo_path)
    candidate_abs = os.path.abspath(os.path.join(repo_root, normalized_path))

    if not candidate_abs.startswith(repo_root + os.sep):
        logger.error("Target file escapes repository root: %s", ai_provided_path)
        return None

    if os.path.isfile(candidate_abs):
        return candidate_abs

    logger.error("Target file does not exist: %s", normalized_path)
    return None


def main():
    logger.info("Starting 5-Agent Autonomous Bounty Hunter Pipeline")

    github_client = GitHubClient()
    ai_client = BountyHunterAPI()

    try:
        owner, repo = config.target_repository.split("/", 1)
    except ValueError:
        logger.error("TARGET_REPOSITORY must use the owner/repository format.")
        return 1

    target_issue_number = os.getenv("TARGET_ISSUE_NUMBER")
    issue = None

    if target_issue_number:
        try:
            issue_number = int(target_issue_number)
        except ValueError:
            logger.error("TARGET_ISSUE_NUMBER must be an integer.")
            return 1
        issue = github_client.get_issue(owner, repo, issue_number)
    else:
        issues = github_client.fetch_real_issues(owner, repo, limit=1)
        if issues:
            issue = issues[0]

    if not issue:
        logger.error("No usable target issue found.")
        return 1
    title = issue.get("title", "N/A")
    body = issue.get("body") or "No description."
    number = issue.get("number")

    print(f"\n{'-' * 70}\nHUNTING ISSUE #{number}: {title}\n{'-' * 70}\n")

    repo_tree = github_client.get_repository_tree(owner, repo)
    repo_map = "\n".join(repo_tree) if repo_tree else "Map unavailable."

    plan = ai_client.agent_1_architect(title, body, repo_map)
    if not plan:
        logger.error("Architect failed to create a plan.")
        return 1

    patch = ai_client.agent_2_coder(plan, body)
    if not patch:
        logger.error("Coder failed to write the patch.")
        return 1

    inspected_patch = ai_client.agent_3_inspector(patch)
    if not inspected_patch:
        logger.error("Inspector failed to return a result.")
        return 1

    final_patch = patch if inspected_patch.strip().upper() == "PASS" else inspected_patch
    qa_result = ai_client.agent_4_qa_reviewer(title, final_patch)
    print(f"\n--- QA REVIEW ---\n{qa_result}\n{'-' * 17}\n")

    if qa_result.strip().upper() != "APPROVED":
        logger.warning("Patch rejected by QA. Pipeline stopped.")
        return 1

    file_match = re.search(r"(?im)^FILE:\s*([^\n]+)$", final_patch)
    if not file_match:
        logger.error("Could not extract target file path from patch.")
        return 1

    raw_target_file = file_match.group(1).replace("*", "").replace("`", "").strip()
    repo_path = github_client.clone_repository(owner, repo)
    if not repo_path:
        logger.error("Failed to clone repository.")
        return 1

    full_target_path = find_target_file(repo_path, raw_target_file)
    if not full_target_path:
        return 1

    relative_target = os.path.relpath(full_target_path, repo_path).replace(os.sep, "/")
    normalized_patch_target = raw_target_file.replace("\\\\", "/").lstrip("/")
    if relative_target != normalized_patch_target:
        logger.error("Resolved target does not exactly match patch FILE path.")
        return 1

    if not apply_patch(full_target_path, final_patch):
        logger.error("Patcher failed to apply code cleanly.")
        return 1

    pr_desc = ai_client.agent_5_pr_manager(title, final_patch)
    if not pr_desc:
        logger.error("PR manager failed to create a description.")
        return 1

    pr_link = github_client.create_pull_request(
        repository=config.target_repository,
        issue_number=number,
        issue_title=title,
        pr_body=pr_desc,
    )
    if not pr_link:
        logger.error("Failed to open GitHub PR.")
        return 1

    logger.info("SUCCESS: Pull Request live at: %s", pr_link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
