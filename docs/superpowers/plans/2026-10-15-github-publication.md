# GitHub Publication Implementation Plan

> **For agentic workers:** Execute this plan inline and verify every external state change.

**Goal:** Publish a clean, English-only version of the project to a private GitHub repository.

**Architecture:** Curate the local tree with a deny-by-default data policy, translate tracked documentation, initialize Git on `main`, verify the staged tree, then create and push the GitHub repository.

**Tech Stack:** Git, GitHub CLI, PowerShell, Python, pytest

**Spec:** `docs/superpowers/specs/2026-10-15-github-publication-design.md`

## Global Constraints

- Never upload `data/`, `.venv/`, credentials, ledgers, or large parquet artifacts.
- Keep all tracked human-readable content in English.
- Create the remote as private unless the user requests otherwise.
- Run the complete test suite before pushing.

### Task 1: Curate and translate the repository

- [x] Replace Chinese documentation with accurate English versions.
- [x] Harden `.gitignore` around datasets, generated ledgers, and large artifacts.
- [x] Scan the candidate tree for non-English text, secrets, and oversized files.

### Task 2: Initialize and verify Git

- [x] Initialize the repository with branch `main`.
- [x] Stage the curated tree and inspect the complete staged file list.
- [x] Run the full test suite and create the initial commit.

### Task 3: Create and verify GitHub

- [x] Create `Cloooooney/us-stock-ai-quant` as a private repository.
- [x] Push `main` and set the upstream.
- [x] Verify remote visibility, default branch, and commit identity.
