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

**Matrix:** ordinary ZD runs execute `annexes`, `ice`, `packages`, `plugins`,
and `snippets`. Reusable calls that provide `zi_repo` also execute `compat`
against the caller's explicit Zi ref. Jobs run with `fail-fast: false` so a
failure in one suite does not cancel the others.

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
2. Layer caching via `type=gha`, scoped per Zsh version (`scope=test-matrix-<version>`) — only changed layers rebuild on subsequent runs. The scope is required: the GHA cache backend has no built-in isolation between concurrent builds, so a shared scope across the six-way matrix would let one leg's cache overwrite another's, leaving only one version genuinely cached per run. `test-matrix.yml` and `docker.yml` run on the identical weekly cron, so their scopes are also prefixed distinctly (`test-matrix-*` vs `docker-*`) to avoid colliding with each other.
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

Each architecture builds natively rather than through QEMU emulation:
`linux/amd64` legs run on `ubuntu-latest`, `linux/arm64` legs run on the
GitHub-hosted `ubuntu-24.04-arm` runner. There is no `docker/setup-qemu-action`
step anywhere in this workflow.

`build-versioned`: matrix of Zsh version (5.5.1–5.9) times architecture
(`amd64`, `arm64`), 12 legs on `push`/`schedule`/`workflow_dispatch`. Each
leg builds and pushes a single-arch, arch-suffixed tag
(`zsh-<version>-amd64`, `zsh-<version>-arm64`). On `pull_request`, only the
`amd64` leg runs (skipped via a job-level `if`) and nothing is pushed: PRs
never publish, so an arm64 leg would validate nothing the amd64 leg does not
already cover.

`publish-versioned`: depends on `build-versioned`, one job per Zsh version.
Runs `docker buildx imagetools create` to join that version's `-amd64` and
`-arm64` tags into the published multi-arch `zsh-<version>` tag. `imagetools`
operates on images already in the registry, so this job (like
`build-latest`'s arm64 leg pushing) only runs off `pull_request`.

`build-latest`/`publish-latest`: the same per-arch-build-then-join split,
for the `latest` tag. Gated at the job level on `github.ref ==
'refs/heads/main'`, so pull requests and non-`main` triggers skip checkout,
Buildx setup, and login entirely rather than running them only to skip the
build step.

The per-arch `-amd64`/`-arm64` tags remain in the registry alongside the
joined manifest tags; they are not deleted after `imagetools create` runs.
This is a deliberate simplicity tradeoff, not an oversight; cleaning them up
would need a further step calling the GitHub Packages API.

Layer caching uses `type=gha` for every build job, scoped per Zsh version
**and architecture** (`scope=docker-<version>-<arch>`, `scope=docker-latest-<arch>`)
for the same reason as `test-matrix.yml` above: an unscoped or
under-scoped cache lets concurrent legs overwrite each other's cache, so
only one leg would ever get a real hit.

On `pull_request` runs, `build-versioned`'s single `amd64` leg also skips
the `mode=max` cache export, since GitHub Actions cache is branch-isolated:
a cache a PR run writes can never be restored by `main` or another PR, so
exporting it there is pure cost. `push`/`schedule`/`workflow_dispatch` runs
still cache normally, since those are the runs that publish.

All four jobs set an explicit `timeout-minutes` (job-level, in addition to
the existing 60-minute step-level timeout on the build step in
`build-versioned`/`build-latest`) so a stuck build fails within a bounded
window instead of falling back to GitHub's 360-minute default.

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
