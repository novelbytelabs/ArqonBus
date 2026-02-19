# Contributing to ArqonBus

Thank you for your interest in contributing to ArqonBus! This document outlines the branch management strategy, workflow, and guidelines for contributing to the project.

## Table of Contents

1. [Branch Strategy](#branch-strategy)
2. [Workflow Steps](#workflow-steps)
3. [Branch Lifecycle](#branch-lifecycle)
4. [Commit Guidelines](#commit-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Code Style](#code-style)
7. [Getting Help](#getting-help)

---

## Branch Strategy

ArqonBus follows a structured branching model to ensure code quality and stable releases.

### Branch Types

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production branch | **Protected** - No direct commits allowed |
| `dev` | Default development branch | Integration point for all features |
| `dev/<feature-name>` | Feature branches | Created from `dev`, merged back to `dev` |

### Key Rules

1. **Never develop directly from `main`** - All development happens on feature branches
2. **`dev` is the integration branch** - All features merge into `dev` first
3. **Use `dev/` prefix for feature branches** - Examples:
   - `dev/vnext-innovation-execution`
   - `dev/add-websocket-reconnect`
   - `dev/fix-memory-leak`

---

## Workflow Steps

### Starting a New Feature

```bash
# 1. Ensure you're on dev and up-to-date
git checkout dev
git pull origin dev

# 2. Create a new feature branch
git checkout -b dev/my-feature-name

# 3. Work on your feature, committing regularly
git add .
git commit -m "feat: add new feature capability"
```

### Keeping Your Branch Updated

```bash
# Sync with upstream dev regularly
git checkout dev
git pull origin dev
git checkout dev/my-feature-name
git merge dev

# Or use rebase for a cleaner history
git rebase dev
```

### Merging Back to Dev

**Option A: Pull Request (Recommended)**

1. Push your branch to origin:
   ```bash
   git push origin dev/my-feature-name
   ```

2. Create a PR targeting `dev` on GitHub

3. Wait for CI to pass and code review

4. Merge the PR

**Option B: Direct Merge (For Small Changes)**

```bash
git checkout dev
git pull origin dev
git merge dev/my-feature-name
git push origin dev
```

### Releasing to Production

When `dev` is ready for release:

1. Create a PR from `dev` to `main`
2. Ensure all CI checks pass
3. Get maintainer approval
4. Merge the PR

---

## Branch Lifecycle

### Best Practices

- **Keep branches short-lived** - Aim for 1-3 days maximum
- **Delete branches after merging** - Prevents clutter and confusion
- **Regularly sync with upstream `dev`** - Minimizes merge conflicts

### Cleaning Up

```bash
# Delete local branch after merge
git branch -d dev/my-feature-name

# Delete remote branch
git push origin --delete dev/my-feature-name

# Prune deleted remote branches
git fetch --prune
```

### Branch Naming Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `dev/` | Feature development | `dev/add-user-auth` |
| `fix/` | Bug fixes | `fix/websocket-timeout` |
| `refactor/` | Code refactoring | `refactor/simplify-router` |
| `docs/` | Documentation changes | `docs/update-api-guide` |

---

## Commit Guidelines

### Conventional Commits

Use the [Conventional Commits](https://www.conventionalcommits.org/) format for all commit messages:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add WebSocket reconnection logic` |
| `fix` | Bug fix | `fix: resolve memory leak in router` |
| `refactor` | Code refactoring | `refactor: simplify message routing` |
| `docs` | Documentation | `docs: update API reference` |
| `test` | Adding/updating tests | `test: add unit tests for envelope parser` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `perf` | Performance improvement | `perf: optimize message serialization` |
| `style` | Code style changes | `style: format with ruff` |

### Writing Good Commit Messages

**Do:**
- Write in imperative mood: "add feature" not "added feature"
- Keep the first line under 72 characters
- Explain *why* the change was made in the body
- Reference issues: `fixes #123` or `relates to #456`

**Example:**
```
feat: add exponential backoff for WebSocket reconnection

Implements configurable exponential backoff with jitter for
WebSocket reconnection attempts. This prevents thundering herd
problems when the server recovers from an outage.

- Configurable initial delay (default: 100ms)
- Configurable max delay (default: 30s)
- Random jitter to prevent synchronization

Relates to #234
```

---

## Pull Request Process

### Before Creating a PR

- [ ] Code compiles without errors
- [ ] All tests pass locally
- [ ] Code follows style guidelines (ruff for Python, rustfmt for Rust)
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional commits format

### Creating a PR

1. **Use the PR Template** - Reference the template at [`docs/ArqonBus/templates/github_pr_template.md`](docs/ArqonBus/templates/github_pr_template.md)

2. **Fill out all required sections**:
   - Overview of changes
   - Linked spec/design docs
   - State machine or protocol changes
   - Testing performed
   - Security considerations

3. **CI Requirements**:
   - All CI checks must pass before merge
   - CI triggers on PRs to `main` and `dev`
   - CI also runs on pushes to `feature/**` branches

### PR Requirements

| Target Branch | Requirements |
|---------------|--------------|
| `dev` | CI passing, at least 1 reviewer approval |
| `main` | CI passing, maintainer approval required |

### Review Process

1. Author submits PR
2. CI automatically runs tests
3. Reviewers provide feedback
4. Author addresses feedback
5. Reviewer approves
6. Maintainer merges (for `main`) or author merges (for `dev`)

---

## Code Style

### Python

- **Follow PEP 8** - Use [ruff](https://docs.astral.sh/ruff/) for linting
- **Type hints** - Use type annotations for function signatures
- **Docstrings** - Document public functions and classes

```bash
# Run linter
ruff check .

# Format code
ruff format .

# Run tests
pytest
```

### Rust

- **Follow standard Rust conventions**
- **Use `cargo fmt`** for formatting
- **Use `clippy`** for linting

```bash
# Format code
cargo fmt

# Run linter
cargo clippy -- -D warnings

# Run tests
cargo test
```

### General Principles

- **Write self-documenting code** - Use descriptive names
- **Keep functions small** - Single responsibility
- **Add comments for "why"** - Not "what"
- **Update documentation** - Keep docs in sync with code

---

## Getting Help

- **Documentation**: See [`docs/developers_guide.md`](docs/developers_guide.md) for detailed development information
- **Issues**: Check existing issues or create a new one
- **PR Template**: [`docs/ArqonBus/templates/github_pr_template.md`](docs/ArqonBus/templates/github_pr_template.md)

---

## Quick Reference

```bash
# Start new feature
git checkout dev && git pull && git checkout -b dev/my-feature

# Run tests
pytest

# Lint code
ruff check .

# Push and create PR
git push origin dev/my-feature

# After merge, cleanup
git branch -d dev/my-feature
git push origin --delete dev/my-feature
```

---

Thank you for contributing to ArqonBus! 🚀
