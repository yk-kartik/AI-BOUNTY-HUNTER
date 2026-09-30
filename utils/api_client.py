import logging
import time

import requests

from config.settings import config

logger = logging.getLogger(__name__)


class BountyHunterAPI:
    def __init__(self):
        self.api_key = config.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.timeout = config.timeout_seconds
        self.model_name = self._auto_detect_model()

    def _auto_detect_model(self):
        if not self.api_key:
            return "gemini-3.8-flash"

        try:
            response = requests.get(
                f"{self.base_url}/models",
                params={"key": self.api_key},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [model["name"].replace("models/", "") for model in models]
                priorities = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]

                for priority in priorities:
                    if priority in available_models:
                        logger.info("API model selected: %s", priority)
                        return priority

                for model in available_models:
                    if "gemini" in model and "vision" not in model:
                        logger.info("API fallback model selected: %s", model)
                        return model
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.error("Model discovery failed: %s", exc)

        return "gemini-3.8-flash"

    def _call_gemini(self, system_prompt, prompt, attempts=3):
        if not self.api_key:
            logger.error("GEMINI_API_KEY is missing.")
            return None

        url = f"{self.base_url}/models/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json"}
        combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{prompt}"
        data = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }

        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    params={"key": self.api_key},
                    json=data,
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    candidates = response.json().get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0]["text"]
                    logger.error("Gemini returned an empty response.")
                    return None

                logger.error("Gemini API error (%s): HTTP %s", self.model_name, response.status_code)
                if response.status_code not in {429, 500, 502, 503, 504}:
                    return None
            except requests.RequestException as exc:
                logger.error("Gemini request failed on attempt %d: %s", attempt, exc)

            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

        return None

    def agent_1_architect(self, issue_title, issue_body, repo_map):
        logger.info("Agent 1: Architect")
        system = "You are a Software Architect. Analyze the issue and repository map. Output a step-by-step technical plan specifying exactly which files need changes."
        prompt = f"Issue: {issue_title}\nDetails: {issue_body}\nRepo Map:\n{repo_map}"
        return self._call_gemini(system, prompt)

    def agent_2_coder(self, plan, issue_body):
        logger.info("Agent 2: Coder")
        system = "You are an Elite Developer. Write the exact code patch. Use the SEARCH/REPLACE block format. Never use placeholders or ellipsis. The SEARCH block must match the original file lines character-for-character.\nFormat:\nFILE: path/to/file.py\n<<<< SEARCH\nexact lines from original file\n====\nnew modified lines\n>>>> REPLACE"
        prompt = f"Plan: {plan}\nIssue Details: {issue_body}"
        return self._call_gemini(system, prompt)

    def agent_3_inspector(self, patch):
        logger.info("Agent 3: Inspector")
        system = "You are a strict Linter. Check the patch for syntax errors, missing brackets, bad imports, and malformed SEARCH/REPLACE blocks. If perfect, reply exactly PASS. If errors exist, return a corrected patch."
        return self._call_gemini(system, patch)

    def agent_4_qa_reviewer(self, original_issue, patch):
        logger.info("Agent 4: QA")
        system = "You are a Senior QA Engineer. Check whether the code changes solve the issue without breaking logic. If correct, reply exactly APPROVED. Otherwise reply exactly REJECTED: followed by the reason."
        prompt = f"Issue: {original_issue}\nPatch:\n{patch}"
        return self._call_gemini(system, prompt)

    def agent_5_pr_manager(self, issue_title, patch):
        logger.info("Agent 5: PR Manager")
        system = "You are a DevRel Manager. Write a professional, concise GitHub PR description for this patch. Include sections: Fix Description, Changes Made, and Checklist."
        prompt = f"Issue: {issue_title}\nPatch:\n{patch}"
        return self._call_gemini(system, prompt)
