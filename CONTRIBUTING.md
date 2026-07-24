# Contributing

This repository is proprietary — see [LICENSE](LICENSE). It isn't open to unsolicited contributions: only people explicitly authorized by the copyright holder should open PRs. If you haven't been given write access and want to propose a change, contact connectwithkatianna@gmail.com first rather than opening a PR.

## PR review process (for authorized contributors)

1. Branch off `main`, make your changes, push, and open a PR against `main`.
2. **CI must pass.** The `check-env-not-committed` workflow runs automatically on every PR and push to `main`, and blocks merge if `.env` (or any `.env.*` variant besides `.env.example`) is committed, or if `.gitignore` stops excluding it.
3. **At least 1 approving review is required.** [CODEOWNERS](.github/CODEOWNERS) names `@connectwithkatianna-ctrl` as owner of the whole repo, so review is requested automatically. Approvals are dismissed if you push new commits to the PR branch — you'll need a fresh approval after changes.
4. The repo owner can merge as admin without waiting on either gate. Every other contributor needs both the CI check and the review to pass before merging.
5. `main` doesn't allow force-pushes or branch deletion.

## Practical notes

- Python 3.9+; dependencies are in `requirements.txt` (`requests`, `pyyaml`).
- Never commit `.env` — copy `.env.example` instead. The CI check exists specifically to catch this.
- Prefer changing `config.yaml` (brand, competitors, prompts, search queries) over hardcoding values in `monitor.py` / `serp_monitor.py` / `report.py`.
