# Social Media Agent (LangGraph + OpenAI)

An AI agent that turns a niche into ready-to-publish content. Enter a niche; the agent researches it with OpenAI web search, picks one idea, and drafts a blog post, a short-form video script, an image, and native posts for X, LinkedIn, Facebook, Instagram, TikTok and YouTube. You review and edit everything in a browser, and nothing is published until you approve.

Built with **LangGraph** (workflow and human-in-the-loop pause), **FastAPI** (backend), and a dependency-free HTML/JS front end.

## Features

- Web research with OpenAI's hosted web search
- Parallel content generation (blog, video script, image)
- Human approval gate with editable drafts, backed by a LangGraph checkpointer
- Dry run by default; live posting needs an explicit opt-in and an approval
- Run history stored in SQLite; paused runs survive a server restart
- Optional password protection for the UI and API
- Docker support, offline test suite

## Workflow

```
research -> plan -> write_blog ─┐
                 -> write_video ├-> write_posts -> approve (pauses) -> publish
                 -> make_images ┘
```

## Quick start

Requires Python 3.11+ and an OpenAI API key.

```bash
git clone https://github.com/safe51891-ai/Social-media-agent.git
cd Social-media-agent
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # set OPENAI_API_KEY
python -m server                   # open http://127.0.0.1:8000
```

If port 8000 is busy: `PORT=8001 python -m server`.

CLI alternative:

```bash
python main.py "home coffee brewing"                  # dry run
python main.py "AI agents for small business" --video clip.mp4 --live
```

## Project layout

```
agent/        AI workflow (config, llm, nodes, graph, publishers/)
server/       FastAPI app, background job runner, SQLite run store
web/          Browser UI (HTML, CSS, JS; no build step)
tests/        Offline tests with fake OpenAI responses
main.py       Command-line runner
```

## Configuration

All settings live in `.env` (see `.env.example`).

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required |
| `TEXT_MODEL`, `IMAGE_MODEL` | Models your account can use |
| `MAKE_IMAGES` | `false` to skip image generation |
| `APP_PASSWORD` | Password-protect the UI and API; set before deploying |
| `DATA_DIR`, `OUTPUT_DIR` | Database and per-run drafts |

A platform with empty credentials is skipped.

## Platform support

| Platform | Posting | Needs |
|---|---|---|
| X | Text thread | Developer app with write access |
| Facebook Page | Text or photo | Meta app, Page token |
| Instagram | Single image | Business account, public image URL (`PUBLIC_MEDIA_BASE_URL`) |
| LinkedIn | Text | `w_member_social` or organization scope |
| TikTok | Package only | Upload manually (API needs app review) |
| YouTube | Package only | Upload manually (API needs OAuth and quota approval) |

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests make no network calls and post nothing.

## Deploy

```bash
docker compose up -d --build
```

Persist `data/` and `output/` as volumes, set `APP_PASSWORD`, and serve behind HTTPS. Run a single instance: run state is in SQLite and in-process threads. To scale out, move the checkpointer and run store to Postgres.

## Notes

- Dry run is the default. Check the drafts; the blog marks unverified figures with `[verify]`.
- Automated mass posting or many accounts sharing content can violate platform rules and get accounts banned.
- Confirm model names and API versions (`GRAPH_VERSION`, `LINKEDIN_API_VERSION`) against current provider docs.

## Related

An n8n version of this agent: https://github.com/safe51891-ai/Social-medai-agent-in-n8n

## Author

Built by [safe51891-ai](https://github.com/safe51891-ai).
