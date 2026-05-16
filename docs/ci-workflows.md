# CI Workflows

`zd` uses a two-tier CI model. Native tests run on every push and pull request to catch regressions quickly. The Docker matrix runs weekly to verify compatibility across Zsh versions without blocking merges.

## Overview

| Workflow           | File              | Trigger                                       | Purpose                             |
| ------------------ | ----------------- | --------------------------------------------- | ----------------------------------- |
| ZUnit (native)     | `test-native.yml` | push, PR, schedule, dispatch, `workflow_call` | Fast ZUnit suite on ubuntu-latest   |
| ZUnit (Zsh matrix) | `test-matrix.yml` | weekly, dispatch                              | Zsh 5.5.1–5.9 compat via Docker     |
| Zi Docker          | `docker.yml`      | push, tags, schedule                          | Build and publish multi-arch images |
| Zsh -n             | `zsh-n.yml`       | push, PR                                      | Syntax check all `.zsh` files       |
| CodeQL             | `codeql.yml`      | push, PR, schedule                            | Security scanning                   |

---

## test-native.yml

The primary CI workflow. Runs on every push to `main` (when `tests/**` or `utils.zsh` change), on all pull requests, on a weekly Monday schedule, and on manual or `workflow_call` dispatch.

**Matrix:** one parallel job per `.zunit` file — `annexes`, `ice`, `packages`, `plugins`, `snippets`. Jobs run with `fail-fast: false` so a failure in one suite does not cancel the others.

**Steps per job:**

1. Checkout the repository
2. Install `zsh` via `apt-get`
3. Install `zunit`, `revolver`, and `color` into `bin/`
4. Install Zi — either via the default install script or a custom repo/ref when inputs are provided (see [Cross-Repo Integration](cross-repo.md))
5. Run `zunit --tap --verbose tests/<suite>.zunit`

**Environment variables set by the workflow:**

| Variable  | Value                       | Purpose                                      |
| --------- | --------------------------- | -------------------------------------------- |
| `PATH`    | `$PWD/bin:$PATH`            | Makes `zunit`, `revolver`, `color` available |
| `ZI_BIN`  | `$HOME/.local/share/zi/bin` | Points `zi_test` at the installed Zi binary  |
| `ZI_DATA` | `$RUNNER_TEMP/zunit`        | Isolated data dir; wiped between tests       |
| `TERM`    | `xterm`                     | Required for Zi's output formatting          |

**Manual dispatch inputs** (available in the GitHub Actions UI):

| Input     | Default   | Description                                                               |
| --------- | --------- | ------------------------------------------------------------------------- |
| `zi_repo` | _(empty)_ | GitHub repo for Zi (`owner/name`). Empty uses the default install script. |
| `zi_ref`  | `main`    | Branch, tag, or SHA to install.                                           |

---

## test-matrix.yml

Runs weekly (Wednesday 03:00 UTC) and on manual dispatch. Not triggered by push or pull request — Zsh version compatibility is a periodic concern, not a per-commit one.

**Matrix:** six parallel jobs, one per Zsh version:

| Version | Tag suffix  |
| ------- | ----------- |
| 5.5.1   | `zsh-5.5.1` |
| 5.6.2   | `zsh-5.6.2` |
| 5.7.1   | `zsh-5.7.1` |
| 5.8     | `zsh-5.8`   |
| 5.8.1   | `zsh-5.8.1` |
| 5.9     | `zsh-5.9`   |

**Per job:**

1. Build the Docker image for that Zsh version using `docker/setup-buildx-action` and `docker/build-push-action`, passing `ZSH_VERSION` as a build arg — the Dockerfile compiles that exact Zsh release from source on the `debian:trixie-slim` base
2. Layer caching via `type=gha` — only changed layers rebuild on subsequent runs
3. Run all test files in a single container invocation:

```sh
docker run --rm \
  --env TERM=xterm \
  --env ZI_DATA=/data \
  --volume "${RUNNER_TEMP}/zunit:/data" \
  "zd:${{ matrix.zsh_version }}" \
  zsh -c 'for f in /src/tests/*.zunit; do zunit --tap --verbose "$f" || exit $?; done'
```

Running all suites in one container (rather than one container per suite) keeps the job count at 6 instead of 30.

---

## docker.yml

Builds and publishes multi-architecture images (`linux/amd64`, `linux/arm64`) to `ghcr.io/z-shell/zd`.

**Triggers:**

- Push to `main` touching `docker/**`, `scripts/**`, `tests/**`, or `lib/**`
- Tag push matching `v*.*.*`
- Weekly schedule (Wednesday 03:00 UTC)
- Manual dispatch

**Jobs:**

`build-versioned` — builds one image per Zsh version (5.5.1–5.9) with tag `zsh-<version>`. Images are pushed only when the trigger is not a pull request (`github.event.number == 0`).

`build-latest` — builds the `latest` tag. Pushed only on `main` branch pushes.

Layer caching uses `type=gha` for both jobs.

---

## Environment variable reference

All workflows share a common set of variables. The table below covers every variable used across the three main workflows.

| Variable      | Workflow       | Default                     | Description                                  |
| ------------- | -------------- | --------------------------- | -------------------------------------------- |
| `TERM`        | native, matrix | `xterm`                     | Terminal type required by Zi output          |
| `ZI_BIN`      | native         | `$HOME/.local/share/zi/bin` | Path to Zi binary directory                  |
| `ZI_DATA`     | native, matrix | `$RUNNER_TEMP/zunit`        | Plugin/snippet data directory                |
| `ZI_REPO`     | native (input) | `z-shell/zi`                | Zi GitHub repo when using `workflow_call`    |
| `ZI_REF`      | native (input) | `main`                      | Zi branch/tag/SHA when using `workflow_call` |
| `ZSH_VERSION` | matrix, docker | _(empty)_                   | Zsh version to bake into the Docker image    |
