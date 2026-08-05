# CI setup

Operational notes for the workflows in this directory. Contributor-facing
guidance lives in [CONTRIBUTING.md](../CONTRIBUTING.md); this file is for
whoever maintains the automation.

## Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `nightly.yml` | `17 6,18 * * *` UTC + dispatch | Refreshes `src/_data/github_meta.json`, summarizes new releases into `src/_data/planet_feeds.json`, regenerates `README.md`, opens a PR |
| `planet-feeds.yml` | `43 6,18 * * *` UTC + dispatch | Pulls YouTube / arXiv / Reddit / community / connpass items into `src/_data/planet_feeds.json`, opens a PR |
| `validate.yml` | PR | `scripts/validate.py` over every entry |
| `build-check.yml` | PR | Eleventy build |
| `entry-from-issue.yml` | `approved` label on an issue | Converts an entry-submission issue into a PR |

`nightly.yml` accepts a `dry_run` input: summaries are printed, nothing is
written, and no PR is opened. Use it to exercise the summarization path safely.

## Summarization backend

Release summaries and the bilingual connpass blurbs both run through
`scripts/llm_client.py`. The provider is chosen by the `SUMMARY_PROVIDER`
repository **Variable** — no code change needed to switch.

| `SUMMARY_PROVIDER` | Backend | Credential |
|---|---|---|
| unset / `foundry` | Claude on Microsoft Foundry (default) | `FOUNDRY_API_KEY` secret |
| `anthropic` | Anthropic Messages API direct | `ANTHROPIC_API_KEY` secret |
| `github` | GitHub Models — **retired, does not work** | — |

### Required configuration

**Secret `FOUNDRY_API_KEY`** — the API key for the Foundry resource. That is the
only thing the default path needs.

**Variable `FOUNDRY_ENDPOINT`** *(optional)* — overrides the deployment URL when
the resource changes. Defaults to the URL in `scripts/llm_client.py`:

```
https://tsingletary-8246-resource.services.ai.azure.com/anthropic/v1/messages
```

**Variable `SUMMARY_MODEL`** *(optional)* — overrides the model id. The Foundry
default is `claude-haiku-4-5`. Note the id differs from the Anthropic-direct
default (`claude-haiku-4-5-20251001`): Foundry catalogs Claude without the date
suffix.

Foundry serves Claude behind an Anthropic-compatible surface at
`/anthropic/v1/messages`, so both providers share one request path in
`llm_client._call_anthropic_api()` — same payload, same `x-api-key` auth, same
`content[0].text` response. Only the host and the billing account differ.

### Budget

The Foundry resource is capped at **$20/month**. Haiku plus the sparse-body gate
below keeps normal usage far under that: a typical night summarizes 0–5
releases at roughly 1–2k tokens each. If summaries stop appearing, check the
Azure spend cap before debugging code.

## Why not GitHub Models or Copilot

**GitHub Models was retired on 2026-07-30.** `models.github.ai` answers every
request — inference, catalog, even unauthenticated — with HTTP 410
`github_models_retirement_brownout`. The `github` provider is kept only so that
an unconverted `SUMMARY_PROVIDER=github` fails with an explanatory message.
Note the error text still says "temporarily unavailable… brownout", which is
misleading: the brownouts were the July 16 and 23 rehearsals, and the string is
now served post-retirement.

**GitHub Copilot inference was evaluated and rejected.** `api.githubcopilot.com`
accepts only interactive OAuth (`gho_`) tokens. Measured from inside Actions it
rejects both credentials available there:

```
PAT:            "Personal Access Tokens are not supported for this endpoint"
Actions token:  "GitHub App Server-To-Server Tokens are not supported for this endpoint"
```

The Copilot **CLI** does work in Actions with a fine-grained, user-owned PAT
carrying the `Copilot Requests` permission (`npm install -g @github/copilot`,
then `copilot -p <prompt> --no-ask-user`), but it needs a node install and a
subprocess per release, and its model catalog is narrower than the API's.
Foundry is the simpler dependency.

## Failure modes

**The summarize step exits non-zero when every summarization call fails.** This
is deliberate. Before it existed, a dead backend was indistinguishable from a
quiet news day: each release logged `SKIP: summarization failed`, the job exited
0, and the nightly PR arrived with no summaries in it. If the step goes red,
read the `WARN llm_client <provider>` lines — they carry the HTTP status and the
provider's own error message.

Common causes:

| Symptom | Cause |
|---|---|
| `HTTP 401` | Key belongs to a different resource, or is unset/rotated |
| `HTTP 404 … Deployment not found` | `SUMMARY_MODEL` names a model not deployed on this resource |
| `HTTP 429` | Rate or budget cap hit — check the Azure spend cap |
| `HTTP 410 … retirement` | `SUMMARY_PROVIDER` is still set to `github`; unset it |

**"No new release items" is usually correct, not a bug.** Candidates are
filtered before the model is ever called:

- already present in `planet_feeds.json` (deduplicated by URL)
- pre-release tags — `dev`, `rc`, `alpha`, `beta`, `qa`, CI experiment tags
- bodies under `SPARSE_LIMIT` (120 chars) in `scripts/summarize_releases.py`

A repo whose releases carry empty bodies will never produce feed items. That is
intended: summarizing "Bug fixes." yields nothing worth publishing.

**Metadata gaps are logged but do not fail the run.** `fetch_github_meta.py`
prints `WARN <repo>: HTTP 404` for repos it cannot read — private, renamed, or
deleted — and moves on. Those entries silently keep stale stars and releases
forever, so it is worth grepping a nightly log for `WARN` occasionally.

## Bot PRs

Both scheduled workflows open PRs via `peter-evans/create-pull-request` rather
than pushing to `main`:

- `chore/nightly-github-metadata` → "chore: update GitHub metadata"
- `chore/nightly-planet-feeds` → "chore: update planet feeds"

Deliberately **no** `[skip ci]` in the commit message: single-commit PRs
squash-merge with that message as the commit title, and it must not suppress
the Pages deploy on `main`.

`data.json` is **not** regenerated by CI — only `README.md` is. Run
`npm run generate` by hand after changing entries, or `data.json` drifts. (It
had drifted a month and 12 entries before 2026-08-05.)
