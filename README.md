# tiktok-hackathon-2026

## Official TechJam evaluator

The organizer imports `starter.agent.Agent`. That module re-exports the team-owned implementation in `shopping_copilot/agent.py`, so local evaluation exercises this repository's code directly.

Run the 200 public sessions from the repository root:

```bash
python -m evaluator.local_evaluator --catalog catalog.jsonl
```

The command writes the ignored local artifact `results.json` and prints the aggregate and per-scenario metrics. The vendored evaluator, public sessions, API contract, and scoring configuration are kept unchanged from the official participant kit.

## Demo API

```bash
cd shopping_copilot
uvicorn app.main:app
```
