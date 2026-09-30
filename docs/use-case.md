# Use Case Diagram

```mermaid
flowchart LR
    U[Student / Developer]
    G[GitHub]
    AI[Gemini API]

    U -->|Configure credentials and target| S((Run Scout))
    S --> G
    U -->|Start autonomous hunt| H((Process Queue))
    H --> G
    H --> AI
    H --> P((Generate Pull Request))
    P --> G
```

## Main use cases

- Configure the system.
- Discover candidate bounty issues.
- Process a queued issue.
- Analyze and generate a patch.
- Validate and apply the patch.
- Create a Git branch, commit, and Pull Request.
