# AI-Bounty-Hunter

AI-Bounty-Hunter is an autonomous Python system that discovers suitable GitHub issues, analyzes a selected issue through a multi-agent AI pipeline, generates a SEARCH/REPLACE patch, validates it, applies it to a cloned repository, commits the change, pushes a branch, and creates a Pull Request.

## Project workflow

GitHub Issues → Scout → `bounty_queue.json` → Auto Hunter → GitHub Client → Architect → Coder → Inspector → QA → Patch Engine → Git branch/commit → Pull Request → PR Manager

## Major functional modules

1. **Scout** - searches GitHub for open Python issues that match bounty-related criteria and stores candidates in `bounty_queue.json`.
2. **Multi-Agent AI Pipeline** - uses five AI roles: Architect, Coder, Inspector, QA Reviewer, and PR Manager.
3. **Patch and GitHub Automation** - resolves the exact target file, applies a validated patch, creates a branch, commits, pushes, and opens a Pull Request.

## Technologies

- Python 3.10+
- GitHub REST API
- Gemini API
- `requests`
- Git for branch, commit, push, and Pull Request automation
- JSON queue storage
- `unittest` for automated validation tests

## Project structure

```text
AI-Bounty-Hunter/
├── main.py
├── scout.py
├── auto_hunter.py
├── bounty_queue.json
├── requirements.txt
├── .env.example
├── .gitignore
├── run.bat
├── config/
│   ├── __init__.py
│   └── settings.py
├── utils/
│   ├── __init__.py
│   ├── api_client.py
│   ├── github_client.py
│   └── patcher.py
├── tests/
│   ├── test_auto_hunter.py
│   ├── test_main.py
│   └── test_patcher.py
└── docs/
    ├── architecture.md
    ├── workflow.md
    ├── use-case.md
    ├── sequence.md
    ├── class-diagram.md
    ├── storage-schema.md
    └── testing-results.txt
```

## Setup

1. Install Python 3.10 or newer.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Put your Gemini API key and GitHub token in `.env`.
5. Set `TARGET_REPOSITORY=owner/repository`.

Never commit `.env`. The repository `.gitignore` excludes it.

## Run

### Discover bounty issues

```bash
python scout.py
```

This updates `bounty_queue.json`.

### Process the queue

```bash
python auto_hunter.py
```

The queue processor selects pending targets and passes the repository and issue number to the main pipeline.

### Run the main pipeline directly

```bash
python main.py
```

If `TARGET_ISSUE_NUMBER` is set, the exact issue is processed. Otherwise, the first available open issue is used.

## Testing

Run the built-in unit tests:

```bash
python -m unittest discover -s tests -v
```

The tests cover patch replacement, duplicate-match protection, placeholder rejection, target-file safety, timeout classification, and successful/failed pipeline classification.

## Security

- API keys and GitHub tokens are read from environment variables or `.env`.
- `.env` is excluded from Git.
- GitHub tokens are not embedded in repository URLs.
- API error logging avoids printing response bodies that could contain sensitive data.
- Patch application rejects ambiguous SEARCH blocks.
- Target file resolution is restricted to the repository and requires an exact path.
- Pull Request creation uses the repository's detected default branch instead of assuming `main`.

## Academic deliverables

The VITyarthi design artefacts are stored in `docs/`, while `statement.md` contains the required problem statement, scope, target users, and high-level features.
