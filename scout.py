import json
import os
import re
import time

import requests

from config.settings import config

QUEUE_FILE = "bounty_queue.json"


def get_intelligent_bounties():
    search_queries = [
        "is:issue is:open language:python label:bounty",
        "is:issue is:open language:python label:polar",
        "is:issue is:open language:python label:algora",
        'is:issue is:open language:python "bounty"',
    ]

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI-Bounty-Hunter/1.0"}
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"

    valid_targets = []

    for query in search_queries:
        label_name = query.split("label:")[-1] if "label:" in query else 'text:"bounty"'
        print(f"Scanning radar for: {label_name}...")
        url = f"{config.github_api_base_url}/search/issues"
        params = {"q": query, "sort": "updated", "order": "desc", "per_page": 50}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=config.timeout_seconds)
            if response.status_code == 403:
                print("GitHub API rate limit hit. Waiting 10 seconds...")
                time.sleep(10)
                continue
            response.raise_for_status()
            issues = response.json().get("items", [])

            for issue in issues:
                if issue.get("comments", 0) > 10:
                    continue

                body = issue.get("body") or ""
                title = issue.get("title") or ""
                if len(body) > 4000:
                    continue

                repo_full_name = issue.get("repository_url", "").replace(
                    f"{config.github_api_base_url}/repos/", ""
                )
                repo_lower = repo_full_name.lower()
                if any(value in repo_lower for value in ("bount", "plaza", "test")):
                    continue

                title_lower = title.lower()
                forbidden_words = ["lesson", "onboarding", "tutorial", "docs", "readme", "epic", "roadmap"]
                if any(word in title_lower for word in forbidden_words):
                    continue

                text_to_search = f"{title} {body}"
                amounts = re.findall(r"\$(\d+)", text_to_search)
                bounty_label = ""
                if amounts:
                    max_amount = max(int(amount) for amount in amounts)
                    if max_amount > 50:
                        continue
                    if max_amount > 0:
                        bounty_label = f"[${max_amount} BOUNTY]"
                else:
                    bounty_label = "[Amount Hidden]"

                valid_targets.append(
                    {
                        "repo": repo_full_name,
                        "title": f"{bounty_label} {title}",
                        "url": issue.get("html_url"),
                        "issue_number": issue.get("number"),
                        "status": "pending",
                    }
                )
        except (requests.RequestException, ValueError) as exc:
            print(f"Error on {query}: {exc}")

    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "r", encoding="utf-8") as file:
                existing_queue = json.load(file)
        else:
            existing_queue = []
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read queue: {exc}")
        existing_queue = []

    if not isinstance(existing_queue, list):
        existing_queue = []

    existing_urls = {target.get("url") for target in existing_queue}
    added_count = 0

    for target in valid_targets:
        if target.get("url") and target["url"] not in existing_urls:
            existing_queue.append(target)
            existing_urls.add(target["url"])
            added_count += 1

    with open(QUEUE_FILE, "w", encoding="utf-8") as file:
        json.dump(existing_queue, file, indent=4)

    print(f"Scan complete. {added_count} new bounties found.")
    return existing_queue


if __name__ == "__main__":
    get_intelligent_bounties()
