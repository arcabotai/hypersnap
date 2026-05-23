# Hypersnap Toolkit Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build an open-source `hypersnap` command and `hypersnap.org` website for installing, diagnosing, and supporting Hypersnap / Snapchain nodes.

**Architecture:** A stdlib-only Python CLI performs local checks and writes sanitized reports. A tiny static website explains the commands and routes users to GitHub. A bash installer clones the repo and symlinks the `hypersnap` executable.

**Tech Stack:** Python 3.10+, Bash, static HTML/CSS, pytest, Vercel-compatible static hosting.

---

## v0.1 Tasks

1. Scaffold CLI package and command entrypoint.
2. Implement read-only diagnostics: host, resources, Docker, Compose, containers, ports, info endpoint, logs.
3. Implement `status`, `logs`, `share`, and guarded `install` commands.
4. Build static `hypersnap.org` landing page.
5. Add tests and local validation.
6. Ask before creating GitHub repo, committing, pushing, or deploying.

## v0.2 Tasks

1. Add Graphite/Grafana metric probes for shard lag and peer counts.
2. Add `repair` subcommands for explicitly approved safe operations.
3. Add `share --upload` only after privacy review.
4. Add optional `doctor --explain` LLM mode with bring-your-own-key support.
