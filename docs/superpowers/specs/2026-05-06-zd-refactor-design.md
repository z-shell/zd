# zd Container Refactor Design

**Date:** 2026-05-06
**Status:** Approved

## Problem

The `zd` container is the test harness for the zi plugin manager. It has two core problems:

1. **Flaky CI** — each ZUnit test spawns a fresh Docker container and runs live network downloads (GitHub releases, git clones). Any transient network failure fails the test.
2. **Hard to author tests** — zi commands are passed as shell-escaped strings to `run.sh --wrap`, creating an escaping nightmare. There is no fast local iteration path; every tweak requires a full container round-trip.

## Approach: Native CI tier + Docker only for Zsh version matrix

Tests run natively on GitHub runners for regular CI. Docker is reserved for the Zsh version compatibility matrix (5.5.1–5.9), run on a weekly schedule.

## Repository Structure

```
zd/
  tests/                  # all .zunit files — shared between native and Docker tiers
    helpers.zsh           # zi_test() helper and shared utilities
    setup.zsh             # per-test data dir reset
    teardown.zsh          # per-test cleanup
    annexes.zunit
    ice.zunit
    packages.zunit
    plugins.zunit
    snippets.zunit
  docker/
    Dockerfile            # two-stage build; zi pre-installed during build
    entrypoint.sh         # user creation only — no runtime downloads
    zshenv
    zshrc
  scripts/
    build.sh              # image build helper
    run.sh                # interactive container launcher (dev use)
  utils.zsh               # zi wrapper functions (prepare_system, initiate_system, etc.)
  .github/
    workflows/
      test-native.yml     # tier 1: native zsh on ubuntu-latest
      test-matrix.yml     # tier 2: Docker, Zsh version matrix
      docker.yml          # image publish (unchanged)
```

Key moves from current layout:
- `docker/tests/` → `tests/` (tests are no longer Docker-specific)
- `docker/build.sh`, `docker/run.sh` → `scripts/`
- Docker build context contains only what `docker build` needs

## Test Authoring Model

### The problem with the current model

Tests pass zi commands as shell-escaped strings to `run.sh --wrap`, which runs `zsh -ilsc "<escaped-string>"` inside a container. Example of current escaping:

```zsh
local z=$'zi id-as'\''atpull-fail'\'' null \
atpull'\''echo "intentional failure"; return 255'\'' run-atpull \
for z-shell/null; zi update atpull-fail'
run ./docker/run.sh --wrap --debug --zunit $z
```

### The fix: `zi_test` helper

`tests/helpers.zsh` provides a `zi_test` function that runs a fresh isolated zsh process per test. Commands are written as normal zsh in the test file — no escaping:

```zsh
# tests/helpers.zsh
ZI_BIN="${ZI_BIN:-${HOME}/.zi/bin}"
ZI_DATA="${ZI_DATA:-${TMPDIR:-/tmp}/zunit}"

zi_test() {
  local script=$1
  run zsh -lc "
    typeset -gA ZI
    ZI[HOME_DIR]=${ZI_DATA}
    source ${ZI_BIN}/zi.zsh
    autoload -Uz _zi
    ${script}
  "
}
```

Same test rewritten:

```zsh
@test 'failing atpull ice' {
  zi_test '
    zi id-as"atpull-fail" null \
      atpull"echo intentional failure; return 255" run-atpull \
      for z-shell/null
    zi update atpull-fail
  '
  assert $state equals 255
  assert "$output" contains "intentional failure"
}
```

Each test gets a fresh isolated zsh process. No shared state between tests. `zi_test` works identically in both the native tier and inside the Docker container — only `ZI_BIN` and `ZI_DATA` env vars differ.

File-level assertions reference `ZI_DATA` directly:

```zsh
assert "${ZI_DATA}/plugins/junegunn---fzf/fzf" is_executable
```

## Native CI Tier

**Workflow:** `.github/workflows/test-native.yml`

- Trigger: push to `main` (paths: `tests/**`), pull requests, weekly schedule, `workflow_dispatch`
- Runner: `ubuntu-latest`
- Matrix: one job per `.zunit` file (parallel, `fail-fast: false`)

**Setup steps:**
1. Install `zsh` via apt
2. Install `zunit`, `revolver`, `color` into `bin/`
3. Install zi via `zsh -c "$(curl -fsSL https://install.zshell.dev)" -- -i skip`
4. Cache `~/.zi/bin` keyed to zi's commit SHA — network hit only when zi changes

**Run:**
```sh
export PATH="$PWD/bin:$PATH"
export ZI_BIN="${HOME}/.zi/bin"
export ZI_DATA="${RUNNER_TEMP}/zunit"
zunit --tap --verbose "tests/${{ matrix.file }}.zunit"
```

This is 10–20× faster than the current per-test container spawn and removes all network flakiness from non-zi sources.

## Docker Tier

### Dockerfile (two-stage)

```dockerfile
ARG ALPINE_VERSION=edge

FROM alpine:${ALPINE_VERSION} AS base

RUN apk --no-cache add \
  build-base ncurses-dev pcre-dev zlib-dev autoconf \
  bash curl git jq rsync sudo zsh vim

# Install zi at build time — not at test time
ARG ZI_BRANCH=main
RUN zsh -c "$(curl -fsSL https://install.zshell.dev)" -- -i skip

FROM base AS test
ARG ZUSER=user
ARG PUID=1000
ARG PGID=1000

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && /entrypoint.sh

COPY docker/zshenv /home/${ZUSER}/.zshenv
COPY docker/zshrc  /home/${ZUSER}/.zshrc
COPY utils.zsh     /src/utils.zsh
COPY tests/        /src/tests/

# VOLUME declared after all COPYs — fixes silent copy invalidation bug
VOLUME ["/data"]

USER ${ZUSER}
WORKDIR /home/${ZUSER}
CMD ["zsh", "-il"]
```

Key fixes vs. current:
- zi is baked in during `docker build` — no network calls at test time
- `VOLUME` declared after `COPY` (current ordering silently discards the copy)
- `entrypoint.sh` only handles user creation — no `wget install.sh` download
- Go removed (not needed for test execution)

### Matrix Workflow

**Workflow:** `.github/workflows/test-matrix.yml`

- Trigger: weekly schedule (`0 3 * * 3`), `workflow_dispatch` only — not on every push
- Matrix: 6 Zsh versions × 5 test files = 30 jobs (`fail-fast: false`)
- Buildx layer caching via `type=gha` — repeat runs rebuild only changed layers

**Run per matrix cell:**
```sh
docker run --rm \
  -e ZI_DATA=/data \
  -v "${RUNNER_TEMP}/zunit:/data" \
  zd:${{ matrix.zsh_version }} \
  zsh -c "zunit --tap --verbose /src/tests/${{ matrix.file }}.zunit"
```

The native workflow catches regressions on every PR. The matrix workflow verifies Zsh version compatibility on a cadence, not blocking every merge.

## Migration of Existing Tests

All five existing `.zunit` files are migrated by:

1. Replacing `run ./docker/run.sh --wrap --debug --zunit <escaped>` with `zi_test '<unescaped>'`
2. Adding `load helpers` to each `@setup` block
3. Replacing hardcoded `${PLUGINS_DIR}` / `${ZPFX}` path assertions with `${ZI_DATA}/plugins/...` and `${ZI_DATA}/polaris/...`
4. Moving files from `docker/tests/` to `tests/`

No test logic changes — only the invocation wrapper and path references.

## What Is Not Changed

- `utils.zsh` functions (`prepare_system`, `initiate_system`, `reload_system`, `zi::*`) — kept as-is for interactive use
- `scripts/run.sh` — kept for interactive `docker run` sessions
- `docker.yml` publish workflow — unchanged
- `.zunit` test assertions and test cases — logic unchanged, only wrapper replaced
- Trunk / linting configuration
