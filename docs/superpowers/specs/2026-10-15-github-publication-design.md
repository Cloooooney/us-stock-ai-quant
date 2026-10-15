# GitHub Publication Design

## Intent

Publish the US equity quantitative research project to the authenticated GitHub account as an English-only, private repository that can be cloned and reviewed without exposing local datasets, credentials, or machine-specific artifacts.

## Repository

- Owner: `Cloooooney`
- Name: `us-stock-ai-quant`
- Visibility: private by default
- Default branch: `main`

## Included

- Python source code and tests.
- English project documentation, model cards, research conclusions, small CSV summaries, and charts.
- Dependency and configuration files.

## Excluded

- The virtual environment, caches, and local execution scratch files.
- All raw and derived market/SEC datasets under `data/`.
- Large prediction parquet files and local paper-rehearsal output.
- Formal paper-trading ledgers and signal snapshots if they are generated later.
- Credentials, API keys, tokens, and machine-specific secrets.

## Acceptance Criteria

- No Chinese text remains in tracked text files.
- No tracked file exceeds GitHub's 100 MB limit.
- The full automated test suite passes before publication.
- Secret scanning finds no credential material.
- The repository is created privately and `main` is pushed successfully.
- The remote repository and latest commit are verified after the push.
