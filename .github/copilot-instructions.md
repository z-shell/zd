# Copilot Instructions — z-shell/zd

## Project overview

`zd` is a **Zi Docker environment** — an Alpine Linux–based Docker image that provides a ready-to-use Zsh + [Zi](https://github.com/z-shell/zi) plugin-manager environment. The repository contains:

- The `Dockerfile` and supporting shell scripts that build the image.
- ZUnit integration tests that exercise Zi plugin/snippet/package installation inside a running container.
- A `run.sh` helper that launches the container with sensible defaults.

## Repository layout

```
docker/
  Dockerfile          # Alpine-based image definition
  entrypoint.sh       # POSIX sh setup script run at image-build time (root)
  init.zsh            # Optional user-supplied init script sourced on startup
  utils.zsh           # Zsh helper functions (prepare_system, initiate_system, zi::*)
  zshenv              # Zsh env bootstrap (ZI config, PATH additions)
  zshrc               # Zsh startup config — sources utils.zsh and calls prepare_system/initiate_system
  build.sh            # Bash helper to docker-build the image with appropriate ARGs
  run.sh              # Bash helper to docker-run the image
  zunit.sh            # Bash wrapper that invokes `zunit run --verbose`
  docker-compose.yml  # Compose file for interactive use
  tests/
    setup.zsh         # ZUnit @setup: exports DATA_DIR, PLUGINS_DIR, SNIPPETS_DIR, ZPFX
    teardown.zsh      # ZUnit @teardown: removes DATA_DIR
    plugins.zunit     # ZUnit tests: fzf, direnv, diff-so-fancy plugin installs
    annexes.zunit     # ZUnit tests: Zi annex loading
    ice.zunit         # ZUnit tests: Zi ice-modifier syntax
    packages.zunit    # ZUnit tests: Zi pack installs
    snippets.zunit    # ZUnit tests: Zi snippet loading
.github/
  workflows/
    docker.yml        # CI: multi-arch Docker build matrix (versioned Zsh + latest)
    zunit.yml         # CI: ZUnit test matrix (one job per *.zunit file)
    codeql.yml        # CodeQL security scanning
    labeler.yml       # Auto-labelling PRs
    pr-labels.yml     # PR label sync
    stale.yml         # Stale issue/PR management
    lock.yml          # Lock closed issues/PRs
    rebase.yml        # Auto-rebase
    sync-labels.yml   # Sync labels from config
    zsh-n.yml         # Zsh -n (syntax check) workflow
  ISSUE_TEMPLATE/     # GitHub issue templates
  PULL_REQUEST_TEMPLATE.md
  CODEOWNERS          # @ss-o owns all files
```

## Key conventions

### Shell scripts
- **`entrypoint.sh`** is POSIX `sh` (shebang `#!/usr/bin/env sh`). It runs as root inside the Alpine build context.
  - Use `sed -i -r` (BusyBox `sed` extended-regex flag) — **not** `-E`, which is unsupported by BusyBox.
  - Never use Bashisms (`[[ ]]`, arrays, `local` with assignment, etc.) in this file.
- **`run.sh`**, **`build.sh`**, **`zunit.sh`** are Bash (shebang `#!/usr/bin/env bash`). 2-space indentation, `# vim: ft=bash sw=2 ts=2 et` modeline.
- **Zsh files** (`utils.zsh`, `zshrc`, `zshenv`, `*.zunit`) use 2-space indentation and the modeline `# vim: ft=zsh sw=2 ts=2 et`.
- All text files: UTF-8, LF line endings, 2-space indent (except Makefiles/Go/Java → 4-space/tab).
- Trailing whitespace is trimmed; files end with a newline (enforced by `.editorconfig`).

### Dockerfile
- Base image: `alpine:$VERSION` (defaults to `edge`). No GNU coreutils unless explicitly `apk add`ed.
- `SHELL` instructions in a Dockerfile only configure the default shell for subsequent `RUN`/`CMD`/`ENTRYPOINT` — they **do not execute** their arguments. Never use a `SHELL` instruction expecting it to run a command.
- Do **not** invoke interactive shell functions (e.g., Zi's `@zi-scheduler`) in `RUN` steps — they only exist inside a live Zsh session loaded via `.zshrc`.
- Go is installed from `https://go.dev/dl/` (not from `apk`) to get a current release. Bump `ARG GO_VERSION` when a new Go release is available; SHA256 is verified via the `https://go.dev/dl/?mode=json&include=all` API.
- `LABEL` values must be plain strings — no template syntax like `<%= ... =>`.

### ZUnit tests
- Each `*.zunit` file begins with `@setup { load setup; setup }` and `@teardown { load teardown; teardown }`.
- Every assertion for a binary artifact must include both `assert "$artifact" is_file` **and** `assert "$artifact" is_executable`.
- Use `local artifact=...` for the first artifact in a test; reassign with `artifact=...` (no `local`) for subsequent ones in the same test body.
- Tests run against the published container image via `run.sh --wrap --debug --zunit`.

### `run.sh` helper
- Use `printf '%s\n' "$*"` (not a custom `say` function) when writing content to a temp file or printing a file path.
- `create_init_config_file` writes `$*` to a `mktemp` file and prints the path on stdout.

## CI / workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `docker.yml` | push/PR to `main` touching `docker/**`, scheduled Wed 03:00 UTC | Builds multi-arch image (`linux/amd64`, `linux/arm64`) for Zsh 5.5.1–5.9 matrix + `latest` tag |
| `zunit.yml` | push to `main` touching `*.zunit`, scheduled Mon/Wed 12:00 UTC, `workflow_dispatch` | Runs each `*.zunit` file as a separate matrix job |
| `zsh-n.yml` | Zsh `-n` syntax check | Checks all Zsh files for syntax errors |

### Common build failure causes
1. **`exit 127` in `RUN`**: A command not found — check that it exists in Alpine at build time.
2. **`sed: unrecognized option '-E'`**: Use `-r` instead (BusyBox `sed`).
3. **Zi/Zsh functions not found**: Functions like `@zi-scheduler`, `zi`, `autoload` only exist in a live interactive Zsh session, never at Docker build time.
4. **Go SHA256 mismatch**: The `GO_VERSION` ARG may need updating to a version that exists on `go.dev/dl/`.

## Development workflow

1. Edit files in `docker/`.
2. Build locally: `cd docker && ./build.sh` (or `docker compose build`).
3. Run ZUnit tests: `./docker/zunit.sh` (requires a built image).
4. Submit a PR — CI will run both `docker.yml` and `zunit.yml`.

## Security notes

- Never commit secrets or credentials.
- The Go tarball SHA256 is verified against the official `go.dev` JSON API before extraction.
- `sudoers` for the container user is scoped to `NOPASSWD: ALL` intentionally for the dev environment.
