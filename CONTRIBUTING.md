# Contributing to Axiom

Axiom is open source under the Apache License 2.0 and welcomes community contributions. This document covers how to get started as a contributor.

For a deeper technical reference — DB migration conventions, architecture overview, and code structure guidelines — see [docs/developer/contributing.md](https://dev.master-of-puppets.work/docs/developer/contributing/) in the documentation site.

## Contributor License Agreement

By submitting a pull request to this repository, you certify that your contribution is your original work (or that you have the right to submit it) and that you agree to license it under the Apache License 2.0.

## Enterprise Edition Boundary

The `/ee` directory contains proprietary Axiom Enterprise Edition code. Community contributions to `/ee` are **not accepted**. All community contributions must remain outside the `/ee` directory.

If you are unsure whether your change touches EE code, check before opening a PR — contributions that modify `/ee` will be closed without review.

## Code Style

**Python:** Black and Ruff are configured in `pyproject.toml`. Run `ruff check .` and `black .` before committing.

**TypeScript:** ESLint is configured in `puppeteer/dashboard/.eslintrc.*`. Run `npm run lint` before committing.

## Testing

All pull requests must include tests. Both test suites must pass:

```bash
# Backend
cd puppeteer && pytest

# Frontend
cd puppeteer/dashboard && npm run test -- --run
```

## Pull Request Workflow

**Branch naming:** `type/short-description`
Examples: `fix/node-heartbeat`, `feat/job-retry`, `docs/rbac-guide`

**PR title format:** `type(scope): description`
Examples: `fix(jobs): handle null node assignment`, `feat(foundry): add blueprint validation`

One maintainer approval is required before merge. Automated checks must pass.

## Reporting Issues

Use GitHub issue templates for bug reports and feature requests:

- **Bug report:** [.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature request:** [.github/ISSUE_TEMPLATE/feature_request.md](.github/ISSUE_TEMPLATE/feature_request.md)

Please search existing issues before opening a new one.

## Detailed Developer Guide

For DB migration conventions, architecture internals, and full code structure guidelines, see the [Developer Contributing Guide](https://dev.master-of-puppets.work/docs/developer/contributing/) in the documentation site.
