import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs without overwriting existing environment variables."""
    if not path.is_file():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()


class Config:
    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def timeout_seconds(self) -> int:
        try:
            return max(5, int(os.getenv("TIMEOUT_SECONDS", "30")))
        except ValueError:
            return 30

    @property
    def github_token(self) -> str | None:
        return os.getenv("GITHUB_TOKEN")

    @property
    def gemini_api_key(self) -> str | None:
        return os.getenv("GEMINI_API_KEY")

    @property
    def github_api_base_url(self) -> str:
        return os.getenv("GITHUB_API_BASE_URL", "https://api.github.com").rstrip("/")

    @property
    def target_repository(self) -> str:
        return os.getenv("TARGET_REPOSITORY", "owner/repo").strip()

    @property
    def bounty_keywords(self) -> list[str]:
        keywords = os.getenv("BOUNTY_KEYWORDS", "bounty,help-wanted")
        return [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]

    @property
    def max_issues_to_fetch(self) -> int:
        try:
            return max(1, min(int(os.getenv("MAX_ISSUES_TO_FETCH", "5")), 100))
        except ValueError:
            return 5


config = Config()
