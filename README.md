# exadel-ai-monitor

Tracks Exadel AI's visibility across two channels:

1. **AI assistants** — queries ChatGPT, Claude, and Gemini with a set of prompts and checks whether "Exadel AI" is mentioned (and at what rank, for numbered-list answers), plus which tracked competitors are mentioned.
2. **Google search** — queries SerpApi with keyword-style search terms and checks whether `exadel.com` appears in the top 10 organic results, plus which competitor domains show up.

Results are appended to dated JSONL files in `results/`, and `report.py` summarizes mention/appearance rates, competitor frequency, and a keyword-gap table (which non-branded search terms Exadel doesn't rank for and which competitor holds the top spot instead).

## Setup

1. **Clone and enter the repo**

   ```bash
   git clone https://github.com/connectwithkatianna-ctrl/exadel-ai-monitor.git
   cd exadel-ai-monitor
   ```

2. **Create a virtualenv and install dependencies**

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. **Configure API keys**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in:

   | Key | Used for | Notes |
   |---|---|---|
   | `OPENAI_API_KEY` | ChatGPT queries | required for the ChatGPT channel |
   | `ANTHROPIC_API_KEY` | Claude queries | required for the Claude channel |
   | `GOOGLE_API_KEY` | Gemini queries | required for the Gemini channel |
   | `SERPAPI_API_KEY` | Google search results | [free trial, no card required](https://serpapi.com/users/sign_up) |
   | `PERPLEXITY_API_KEY` | Perplexity queries | optional — Perplexity is disabled by default in `config.yaml` (`providers.perplexity.enabled: false`); only needed if you flip that to `true` |

   Any provider whose key is missing is simply skipped, not treated as an error — you don't need all four to run the monitor.

4. **Review `config.yaml`** — brand name, tracked competitors, AI-assistant prompts, and Google search queries all live here. Edit to fit what you're tracking.

## Usage

Run from the repo root with the virtualenv's Python:

```bash
# Load .env into the shell
set -a; source .env; set +a

# Query ChatGPT / Claude / Gemini with the configured prompts
.venv/bin/python3 monitor.py

# Query Google search (via SerpApi) with the configured keywords
.venv/bin/python3 serp_monitor.py

# Print the summary report (mention rates, competitor frequency, keyword gaps)
.venv/bin/python3 report.py
```

Each run of `monitor.py` / `serp_monitor.py` appends to that day's file in `results/` (`YYYY-MM-DD.jsonl` and `serp-YYYY-MM-DD.jsonl`), so re-running on the same day adds more data points rather than overwriting.

## Project layout

```
config.yaml       brand, competitors, prompts, search queries, provider toggles
monitor.py        AI-assistant channel (ChatGPT / Claude / Gemini)
serp_monitor.py   Google search channel (via SerpApi)
report.py         summary report across both channels
results/          dated JSONL output (gitignored except this README's directory structure)
recommendations/  point-in-time SEO recommendation writeups
```

## Notes

- `results/*.jsonl` and `.env` are gitignored — raw run data and API keys never get committed.
- AI-assistant mention rates and Google appearance rates in `report.py` exclude prompts/queries that already name "Exadel AI" in their text, since those are echoes of the brand name rather than organic recall.
