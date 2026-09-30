# System Architecture

```mermaid
flowchart TD
    A[GitHub Issues] --> B[Scout]
    B --> C[bounty_queue.json]
    C --> D[Auto Hunter]
    D --> E[GitHub Client]
    E --> F[Repository Clone]
    E --> G[Issue + Repository Metadata]
    G --> H[Agent 1 Architect]
    H --> I[Agent 2 Coder]
    I --> J[Agent 3 Inspector]
    J --> K[Agent 4 QA]
    K -->|APPROVED| L[Patch Engine]
    L --> M[Git Branch + Commit]
    M --> N[Push to GitHub]
    N --> O[Pull Request]
    O --> P[Agent 5 PR Manager]
```

## Components

- **Scout:** discovers candidate issues.
- **Auto Hunter:** manages the queue and execution timeout/status.
- **GitHub Client:** handles GitHub API calls, repository cloning, Git operations, and Pull Requests.
- **BountyHunterAPI:** wraps Gemini API calls and exposes the five agent roles.
- **Patch Engine:** applies only unambiguous SEARCH/REPLACE blocks.
- **Config:** loads environment configuration without storing secrets in source code.

The design uses modular components so GitHub operations, AI operations, configuration, patching, and orchestration can be tested or changed independently.
