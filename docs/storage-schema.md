# Storage / Schema Design

The project uses a lightweight JSON queue rather than a relational database.

File: `bounty_queue.json`

Each queue item follows this logical schema:

| Field | Type | Purpose |
|---|---|---|
| `repo` | string | GitHub `owner/repository` name |
| `title` | string | Issue title, optionally prefixed with bounty amount |
| `url` | string | GitHub issue URL |
| `issue_number` | integer | Exact GitHub issue number |
| `status` | string | `pending`, `completed`, `failed`, `skipped`, or `rate_limited` |
| `reason` | string | Optional processing result explanation |

The JSON file is intentionally simple because the project needs a small persistent work queue rather than relational queries.
