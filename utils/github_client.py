import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

import requests

from config.settings import config

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self):
        self.token = config.github_token
        self.base_url = config.github_api_base_url.rstrip("/")
        self.timeout = config.timeout_seconds
        self.headers = self._get_headers()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AI-Bounty-Hunter/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def test_connection(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            if response.status_code == 200:
                logger.info("GitHub API connection successful.")
                return True
            logger.error("GitHub API returned status %s", response.status_code)
        except requests.RequestException as exc:
            logger.error("GitHub API connection failed: %s", exc)
        return False

    def fetch_real_issues(self, owner: str, repo: str, limit: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "open", "per_page": max(1, min(limit, 100))}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            if response.status_code == 200:
                issues = response.json()
                real_issues = [issue for issue in issues if "pull_request" not in issue]
                logger.info("Fetched %d real issues from %s/%s", len(real_issues), owner, repo)
                return real_issues
            logger.error("GitHub API error: HTTP %s", response.status_code)
        except (requests.RequestException, ValueError) as exc:
            logger.error("Failed to fetch GitHub issues: %s", exc)
        return []

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                issue = response.json()
                if "pull_request" in issue:
                    logger.error("Target %s/%s#%s is a pull request, not an issue.", owner, repo, issue_number)
                    return None
                return issue
            logger.error("GitHub issue lookup failed: HTTP %s", response.status_code)
        except (requests.RequestException, ValueError) as exc:
            logger.error("GitHub issue lookup failed: %s", exc)
        return None


    def get_repository_tree(self, owner: str, repo: str, branch: Optional[str] = None) -> List[str]:
        if branch is None:
            branch = self._get_default_branch(owner, repo)
        if not branch:
            logger.error("Could not determine repository default branch.")
            return []
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={"recursive": "1"},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                tree_data = response.json().get("tree", [])
                return [item["path"] for item in tree_data if item.get("type") == "blob"]
            logger.error("Failed to fetch repository tree: %s", response.status_code)
        except (requests.RequestException, ValueError) as exc:
            logger.error("Tree fetch error: %s", exc)
        return []

    def get_raw_file_content(self, owner: str, repo: str, file_path: str, branch: Optional[str] = None):
        branch = branch or self._get_default_branch(owner, repo)
        if not branch:
            logger.error("Could not determine repository default branch.")
            return None
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.text
            logger.error("Failed to fetch raw file: %s", response.status_code)
        except requests.RequestException as exc:
            logger.error("Raw file fetch error: %s", exc)
        return None

    def _get_default_branch(self, owner: str, repo: str) -> Optional[str]:
        try:
            response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json().get("default_branch")
        except (requests.RequestException, ValueError) as exc:
            logger.error("Could not determine default branch: %s", exc)
        return None

    def clone_repository(self, owner: str, repo: str):
        workspace_dir = "workspace"
        repo_path = os.path.join(workspace_dir, repo)
        os.makedirs(workspace_dir, exist_ok=True)

        if os.path.exists(repo_path):
            return repo_path

        clone_url = f"https://github.com/{owner}/{repo}.git"
        try:
            subprocess.run(
                ["git", "clone", "-c", "core.longpaths=true", "--depth", "1", clone_url, repo_path],
                check=True,
                timeout=self.timeout * 3,
            )
            return repo_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            logger.error("Repository clone failed: %s", exc)
            return None

    def create_pull_request(
        self,
        repository: str,
        issue_number: int,
        issue_title: str,
        pr_body: str,
    ) -> Optional[str]:
        try:
            owner, repo = repository.split("/", 1)
        except ValueError:
            logger.error("Invalid repository format: %s", repository)
            return None

        repo_path = os.path.join("workspace", repo)
        if not os.path.isdir(repo_path):
            logger.error("Repository workspace does not exist: %s", repo_path)
            return None

        default_branch = self._get_default_branch(owner, repo)
        if not branch:
            logger.error("Could not determine repository default branch.")
            return []
        new_branch = f"ai-bounty-fix-{issue_number}"

        try:
            subprocess.run(["git", "config", "user.email", "ai-bounty-hunter@bot.com"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.name", "AI Bounty Hunter"], cwd=repo_path, check=True)
            subprocess.run(["git", "checkout", "-b", new_branch], cwd=repo_path, check=True)
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Fix issue #{issue_number}: {issue_title}"],
                cwd=repo_path,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("Git commit operation failed: %s", exc)
            return None

        push_env = os.environ.copy()
        if self.token:
            push_env["GIT_ASKPASS"] = os.path.abspath(os.path.join(repo_path, ".git-askpass"))
            askpass_path = push_env["GIT_ASKPASS"]
            try:
                with open(askpass_path, "w", encoding="utf-8") as askpass:
                    askpass.write("#!/bin/sh\ncase \"$1\" in\n  *Username*) printf \"%s\\n\" x-access-token ;;\n  *) printf \"%s\\n\" \"$GITHUB_TOKEN\" ;;\nesac\n")
                os.chmod(askpass_path, 0o700)
                push_env["GITHUB_TOKEN"] = self.token
                subprocess.run(
                    ["git", "push", "origin", new_branch],
                    cwd=repo_path,
                    check=True,
                    timeout=self.timeout * 3,
                    env=push_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                logger.error("Git push failed: %s", exc)
                return None
            finally:
                try:
                    os.remove(askpass_path)
                except OSError:
                    pass
        else:
            logger.error("GITHUB_TOKEN is required to create a pull request.")
            return None

        pr_url = f"{self.base_url}/repos/{repository}/pulls"
        pr_data = {
            "title": f"Automated AI Fix for Issue #{issue_number}",
            "body": pr_body,
            "head": new_branch,
            "base": default_branch,
        }

        try:
            response = requests.post(
                pr_url,
                headers=self.headers,
                json=pr_data,
                timeout=self.timeout,
            )
            if response.status_code == 201:
                return response.json().get("html_url")
            if response.status_code == 422:
                logger.warning("Pull request may already exist for this branch.")
                return None
            logger.error("Failed to create pull request: HTTP %s", response.status_code)
        except (requests.RequestException, ValueError) as exc:
            logger.error("Pull request creation failed: %s", exc)
        return None
