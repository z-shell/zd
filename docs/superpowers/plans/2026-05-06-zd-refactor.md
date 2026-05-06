# zd Container Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-test Docker container spawning with a `zi_test` helper (fresh zsh subprocess per test), and move Docker to a scheduled Zsh-version matrix only.

**Architecture:** Native ZUnit tests source zi via a `zi_test()` helper that launches `zsh -c` per test — no Docker, no shell-escaping nightmares. Docker is retained for a 6-job weekly matrix (Zsh 5.5.1–5.9) where the image has zi pre-baked at build time. Both tiers share the same `.zunit` files in `tests/`.

**Tech Stack:** Zsh, ZUnit (zdharma/zunit), Docker/Alpine, GitHub Actions

---

## File Map

**Create:**
- `tests/helpers.zsh` — `zi_test()` helper + shared env vars
- `tests/setup.zsh` — per-test data dir reset (no sudo)
- `tests/teardown.zsh` — per-test cleanup (no sudo)
- `tests/annexes.zunit` — migrated from `docker/tests/annexes.zunit`
- `tests/ice.zunit` — migrated from `docker/tests/ice.zunit`
- `tests/plugins.zunit` — migrated from `docker/tests/plugins.zunit`
- `tests/snippets.zunit` — migrated from `docker/tests/snippets.zunit`
- `tests/packages.zunit` — migrated from `docker/tests/packages.zunit`
- `scripts/build.sh` — `docker/build.sh` with updated context path
- `scripts/run.sh` — copy of `docker/run.sh` (unchanged)
- `.github/workflows/test-native.yml` — tier-1: native zsh on ubuntu-latest
- `.github/workflows/test-matrix.yml` — tier-2: Docker Zsh version matrix

**Modify:**
- `docker/Dockerfile` — two-stage; zi + zunit pre-baked; `ZSH_VERSION` used; `VOLUME` after `COPY`
- `docker/entrypoint.sh` — user creation only; drop wget, symlinks, init.zsh
- `docker/zshrc` — source zi directly; drop `prepare_system`/`initiate_system`
- `docker/docker-compose.yml` — context updated to repo root
- `.github/workflows/zunit.yml` — replaced by `test-native.yml` (deleted)

**Delete (Task 15):**
- `docker/tests/` (entire directory)
- `docker/build.sh`, `docker/run.sh` (moved to `scripts/`)
- `docker/zunit.sh`, `docker/init.zsh`
- `.github/workflows/zunit.yml`

---

## Task 1: Scaffold directories and move scripts

**Files:**
- Create: `scripts/build.sh`
- Create: `scripts/run.sh`

- [ ] **Step 1: Create the `tests/` and `scripts/` directories**

```bash
mkdir -p tests scripts
```

- [ ] **Step 2: Write `scripts/build.sh`**

Differences from `docker/build.sh`: `dockerfile` is now `docker/Dockerfile` (relative to repo root), and the build context is `realpath ..` (repo root, not `docker/`).

```bash
cat > scripts/build.sh << 'EOF'
#!/usr/bin/env bash
# -*- mode: bash; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=bash sw=2 ts=2 et

col_error="[31m"
col_info="[32m"
col_rst="[0m"

say() {
  printf '%s\n' "${col_info}${1}${col_rst}" >&2
}

err() {
  say "${col_error}${1}${col_rst}" >&2
  exit 1
}

build() {
  command cd -P -- "$(dirname -- "$(command -v -- "$0" || true)")" && pwd -P || exit 9

  local image_name="${1:-zd}"
  local tag="${2:-latest}"
  local zsh_version="${3}"
  local container_hostname="z-shell"
  shift 3

  local dockerfile="docker/Dockerfile"

  if [[ -n ${zsh_version} ]]; then
    tag="zsh${zsh_version}-${tag}"
  fi

  say "Building image: ${image_name}"

  local -a args
  [[ -n ${NO_CACHE} ]] && args+=(--no-cache "$@")

  if docker build \
    --build-arg "ZUSER=${USER:-$(id -u -n)}" \
    --build-arg "ZHOST=${container_hostname}" \
    --build-arg "PUID=${UID:-$(id -u)}" \
    --build-arg "PGID=${GID:-$(id -g)}" \
    --build-arg "TERM=${TERM:-xterm-256color}" \
    --build-arg "ZSH_VERSION=${zsh_version}" \
    --file "${dockerfile}" \
    --tag "${image_name}:${tag}" \
    "${args[@]}" "$(realpath .. || true)"; then
    {
      say "To use this image for ZUnit tests run: "
      say "export CONTAINER_IMAGE=\"${image_name}\" CONTAINER_TAG=\"${tag}\""
      say "ZUnit run --verbose"
    } >&2
  else
    err "Container failed to build."
  fi
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  CONTAINER_IMAGE="${CONTAINER_IMAGE:-ghcr.io/z-shell/zd}"
  BUILD_ZSH_VERSION="${BUILD_ZSH_VERSION-}"
  CONTAINER_TAG="${CONTAINER_TAG:-latest}"
  NO_CACHE="${NO_CACHE-}"

  while [[ -n $* ]]; do
    case "$1" in
    --image | -i)
      CONTAINER_IMAGE="$2"
      shift 2
      ;;
    --no-cache | -N)
      NO_CACHE=1
      shift
      ;;
    --zsh-version | -zv | --zv)
      BUILD_ZSH_VERSION="${2}"
      shift 2
      ;;
    *)
      break
      ;;
    esac
  done

  build "${CONTAINER_IMAGE}" "${CONTAINER_TAG}" "${BUILD_ZSH_VERSION}" "$@"
fi
EOF
chmod +x scripts/build.sh
```

- [ ] **Step 3: Write `scripts/run.sh` (--zunit branch stripped)**

The `--zunit` branch in `docker/run.sh` mounts `${ROOT_DIR}/zshenv` and `${ROOT_DIR}/zshrc`, which would point to `scripts/zshenv` after the move — files that don't exist. Since tests no longer run through Docker per-test, strip that branch entirely.

```bash
cat > scripts/run.sh << 'EOF'
#!/usr/bin/env bash
# -*- mode: bash; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=bash sw=2 ts=2 et

col_error="[31m"
col_info="[32m"
col_rst="[0m"

say() {
  printf '%s\n' "${col_info}${1}${col_rst}" >&2
}

err() {
  say "${col_error}${1}${col_rst}" >&2
  exit 1
}

parent_process() {
  local ppid pcmd
  ppid="$(ps -o ppid= -p "$$" | awk '{ print $1 }' || true)"

  if [[ -z ${ppid} ]]; then
    say "Failed to determine parent process"
    return 1
  fi

  if pcmd="$(ps -o cmd= -p "${ppid}")"; then
    say "${pcmd}"
    return
  fi

  return 1
}

running_interactively() {
  if [[ -n ${CI} ]]; then
    return 1
  fi

  if ! [[ -t 1 ]]; then
    parent_process | grep -q zunit || true
  fi
}

create_init_config_file() {
  local tempfile

  if [[ -z $* ]]; then
    return 1
  fi

  tempfile="$(mktemp)"
  printf '%s\n' "$*" >"${tempfile}"
  printf '%s\n' "${tempfile}"
}

run() {
  local image="${CONTAINER_IMAGE:-ghcr.io/z-shell/zd}"
  local tag="${CONTAINER_TAG:-latest}"
  local init_config="$1"
  shift

  local -a args=(--rm)

  if running_interactively; then
    args+=(--tty=true --interactive=true)
  fi

  if [[ -n ${init_config} ]]; then
    if [[ -r ${init_config} ]]; then
      args+=(--volume "${init_config}:/init.zsh")
    else
      say "Init config file is not readable"
      return 1
    fi
  fi

  if [[ -n ${TERM} ]]; then
    args+=(--env "TERM=${TERM}")
  fi

  if [[ -n ${CONTAINER_ENV[*]} ]]; then
    local e
    for e in "${CONTAINER_ENV[@]}"; do
      args+=(--env "${e}")
    done
  fi

  if [[ -n ${CONTAINER_VOLUMES[*]} ]]; then
    local vol
    for vol in "${CONTAINER_VOLUMES[@]}"; do
      args+=(--volume "${vol}")
    done
  fi

  local -a cmd=("$@")

  if [[ -n ${WRAP_CMD} ]]; then
    local zsh_opts="ilsc"
    [[ -n ${ZSH_DEBUG} ]] && zsh_opts="x${zsh_opts}"
    cmd=(zsh "-${zsh_opts}" "${cmd[*]}")
  fi

  if [[ -n ${DEBUG} ]]; then
    {
      say "\$ docker run ${args[*]} ${image}:${tag} ${cmd[*]@Q}"
    } >&2
  fi

  docker run "${args[@]}" "${image}:${tag}" "${cmd[@]}"
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  CONTAINER_IMAGE=${CONTAINER_IMAGE:-ghcr.io/z-shell/zd}
  CONTAINER_TAG="${CONTAINER_TAG:-latest}"
  CONTAINER_ENV=()
  CONTAINER_VOLUMES=()
  DEBUG="${DEBUG-}"
  ZSH_DEBUG="${ZSH_DEBUG-}"
  INIT_CONFIG_VAL="${INIT_CONFIG_VAL-}"
  WRAP_CMD="${WRAP_CMD-}"

  while [[ -n $* ]]; do
    case "$1" in
    --xsel | -b)
      INIT_CONFIG_VAL="$(xsel -b)"
      shift
      ;;
    -c | --config | --init-config | --init)
      INIT_CONFIG_VAL="$2"
      shift 2
      ;;
    -f | --config-file | --init-config-file | --file)
      if ! [[ -r $2 ]]; then
        say "Unable to read from file: $2"
        exit 2
      fi
      INIT_CONFIG_VAL="$(cat "$2")"
      shift 2
      ;;
    -d | --debug)
      DEBUG=1
      shift
      ;;
    -D | --dev | --devel)
      DEVEL=1
      shift
      ;;
    -i | --image)
      CONTAINER_IMAGE="$2"
      shift 2
      ;;
    -t | --tag)
      CONTAINER_TAG="$2"
      shift 2
      ;;
    -e | --env | --environment)
      CONTAINER_ENV+=("$2")
      shift 2
      ;;
    -v | --volume)
      CONTAINER_VOLUMES+=("$2")
      shift 2
      ;;
    -w | --wrap)
      WRAP_CMD=1
      shift
      ;;
    --zsh-debug | -x | -Z)
      ZSH_DEBUG=1
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if INIT_CONFIG="$(create_init_config_file "${INIT_CONFIG_VAL}")"; then
    trap 'rm -vf $INIT_CONFIG' EXIT INT
  fi
  CONTAINER_ROOT="$(
    cd -P -- "$(dirname "$0")"
    pwd -P
  )" || exit 9
  if [[ -n ${DEVEL} ]]; then
    CONTAINER_VOLUMES+=(
      "${CONTAINER_ROOT}:/src"
    )
  fi

  run "${INIT_CONFIG}" "$@"
fi
EOF
chmod +x scripts/run.sh
```

- [ ] **Step 4: Verify both scripts are executable**

```bash
ls -la scripts/
```

Expected: `build.sh` and `run.sh` both show `-rwxr-xr-x`.

- [ ] **Step 5: Commit**

```bash
git add scripts/
git commit -m "feat: add scripts/ directory with build.sh and run.sh"
```

---

## Task 2: Write tests/helpers.zsh

**Files:**
- Create: `tests/helpers.zsh`

- [ ] **Step 1: Write `tests/helpers.zsh`**

```bash
cat > tests/helpers.zsh << 'EOF'
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

# Run a zi snippet in a fresh isolated zsh subprocess.
# $1 — zsh code to execute (unescaped; single-quote at call site to prevent
#       expansion before the function receives it).
#
# Variable interpolation note: ${_zi_bin} and ${_zi_data} are expanded by the
# outer shell when the inner command string is assembled. References to $VAR
# inside the script argument resolve in the *inner* shell after zi is sourced.
# To pass an outer variable's value into the script, let it expand in the
# caller: zi_test "zi light ${my_plugin}"
zi_test() {
  local script=$1
  local _zi_bin="${ZI_BIN:-${HOME}/.zi/bin}"
  local _zi_data="${ZI_DATA:-${TMPDIR:-/tmp}/zunit}"
  run zsh -c "
    typeset -gxU path
    path=( \${HOME}/go/bin \$path )
    typeset -gA ZI
    ZI[HOME_DIR]=${_zi_data}
    source ${_zi_bin}/zi.zsh
    autoload -Uz _zi
    ${script}
  "
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/helpers.zsh
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/helpers.zsh
git commit -m "feat: add tests/helpers.zsh with zi_test helper"
```

---

## Task 3: Migrate setup.zsh and teardown.zsh

**Files:**
- Create: `tests/setup.zsh`
- Create: `tests/teardown.zsh`

Key changes from `docker/tests/`:
- `DATA_DIR` → `ZI_DATA` (matches the env var `zi_test` uses)
- `PLUGINS_DIR`, `SNIPPETS_DIR`, `ZPFX` dropped — tests now use `${ZI_DATA}/plugins`, `${ZI_DATA}/snippets`, `${ZI_DATA}/polaris` inline
- `sudo rm -rf` → `rm -rf` (native runner owns the temp dir)

- [ ] **Step 1: Write `tests/setup.zsh`**

```bash
cat > tests/setup.zsh << 'EOF'
#!/usr/bin/env zunit
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

setup() {
  export ZI_DATA="${TMPDIR:-/tmp}/zunit"

  {
    color magenta @setup started
    color magenta "ZI_DATA=${ZI_DATA}"
  } >&2

  # Wipe plugin/snippet state between tests; keep the dir itself.
  rm -rf "${ZI_DATA:?}"/*
  mkdir -p "${ZI_DATA}"
}

# vim: set ft=zsh et ts=2 sw=2 :
EOF
```

- [ ] **Step 2: Write `tests/teardown.zsh`**

```bash
cat > tests/teardown.zsh << 'EOF'
#!/usr/bin/env zunit
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

teardown() {
  color cyan @teardown called >&2
  [[ -n "${ZI_DATA}" ]] && rm -rf "${ZI_DATA:?}"/*
}

# vim: set ft=zsh et ts=2 sw=2 :
EOF
```

- [ ] **Step 3: Verify syntax**

```bash
zsh -n tests/setup.zsh tests/teardown.zsh
```

Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add tests/setup.zsh tests/teardown.zsh
git commit -m "feat: add tests/setup.zsh and teardown.zsh (no-sudo, ZI_DATA based)"
```

---

## Task 4: Migrate annexes.zunit

**Files:**
- Create: `tests/annexes.zunit`

Changes: `run ./docker/run.sh --wrap --debug --zunit <escaped>` → `zi_test '<unescaped>'`; `${PLUGINS_DIR}` → `${ZI_DATA}/plugins`; add `load helpers`.

Note: `z-a-eval` and `z-a-default-ice` tests assert `$state equals 1` — these are known expected failures (the annexes exit non-zero on load). Keep those assertions as-is.

- [ ] **Step 1: Write `tests/annexes.zunit`**

```bash
cat > tests/annexes.zunit << 'EOF'
#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

@setup {
  load setup
  load helpers
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'z-a-bin-gem-node installation' {
  zi_test 'zi light z-shell/z-a-bin-gem-node'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-bin-gem-node/z-a-bin-gem-node.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-meta-plugins installation' {
  zi_test 'zi light z-shell/z-a-meta-plugins'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-meta-plugins/z-a-meta-plugins.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-readurl installation' {
  zi_test 'zi light z-shell/z-a-readurl'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-readurl/z-a-readurl.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-rust installation' {
  zi_test 'zi light z-shell/z-a-rust'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-rust/z-a-rust.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-eval installation' {
  zi_test 'zi light z-shell/z-a-eval'

  assert $state equals 1
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-eval/z-a-eval.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-linkbin installation' {
  zi_test 'zi light z-shell/z-a-linkbin'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-linkbin/z-a-linkbin.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-default-ice installation' {
  zi_test 'zi light z-shell/z-a-default-ice'

  assert $state equals 1
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-default-ice/z-a-default-ice.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'z-a-test installation' {
  zi_test 'zi light z-shell/z-a-test'

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Compiling"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-test/z-a-test.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/annexes.zunit
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/annexes.zunit
git commit -m "feat: migrate annexes.zunit to zi_test helper"
```

---

## Task 5: Migrate ice.zunit

**Files:**
- Create: `tests/ice.zunit`

Changes: multi-line `$'...'` escaped strings → clean zsh in single-quoted `zi_test` argument; `${PLUGINS_DIR}` → `${ZI_DATA}/plugins`; `${ZPFX}` → `${ZI_DATA}/polaris`.

- [ ] **Step 1: Write `tests/ice.zunit`**

```bash
cat > tests/ice.zunit << 'EOF'
#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

@setup {
  load setup
  load helpers
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'sbin ice' {
  zi_test '
    zi light z-shell/z-a-bin-gem-node
    zi light-mode as"null" from"gh-r" sbin"fzf" for junegunn/fzf
  '

  assert $state equals 0
  assert "$output" contains "Downloading"

  local artifact="${ZI_DATA}/plugins/z-shell---z-a-bin-gem-node/z-a-bin-gem-node.plugin.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable

  artifact="${ZI_DATA}/polaris/bin/fzf"
  assert "$artifact" is_file
  assert "$artifact" is_executable
}

@test 'failing atclone ice' {
  zi_test 'zi null atclone"echo intentional failure; return 255" for z-shell/null'

  assert $state not_equal_to 0
  assert $state equals 255
  assert "$output" contains "intentional failure"
}

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

@test 'failing mv ice' {
  zi_test '
    zi as"command" from"gh-r" bpick"*musl*" mv"DOES_NOT_EXIST* -> fd" pick"fd/fd" \
      for @sharkdp/fd
  '

  assert $state equals 1
  assert "$output" contains "DOES_NOT_EXIST"
  assert "$output" contains "didn'\''t match any file"
}

@test 'mv ice' {
  zi_test '
    zi as"command" from"gh-r" bpick"*musl*" mv"fd* -> fd" pick"fd/fd" \
      for @sharkdp/fd
  '

  assert $state equals 0

  local artifact="${ZI_DATA}/plugins/sharkdp---fd/fd/fd"
  assert "$artifact" is_file
  assert "$artifact" is_readable
  assert "$artifact" is_executable
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/ice.zunit
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/ice.zunit
git commit -m "feat: migrate ice.zunit to zi_test helper"
```

---

## Task 6: Migrate plugins.zunit

**Files:**
- Create: `tests/plugins.zunit`

- [ ] **Step 1: Write `tests/plugins.zunit`**

```bash
cat > tests/plugins.zunit << 'EOF'
#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

@setup {
  load setup
  load helpers
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'zi fzf installation' {
  zi_test 'zi lucid as"program" from"gh-r" for junegunn/fzf'

  assert $state equals 0
  assert "$output" contains "Unpacking"
  assert "$output" contains "Successfully"

  local artifact="${ZI_DATA}/plugins/junegunn---fzf/fzf"
  assert "$artifact" is_file
  assert "$artifact" is_executable
}

@test 'zi direnv installation' {
  zi_test '
    zi light-mode as"program" \
      atclone"go install github.com/cpuguy83/go-md2man/v2@latest" \
      make for @direnv/direnv
  '

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "go: downloading github.com"

  local artifact="${ZI_DATA}/plugins/direnv---direnv/direnv"
  assert "$artifact" is_file
  assert "$artifact" is_executable
}

@test 'zi diff-so-fancy installation' {
  zi_test '
    zi light-mode for \
      as"program" pick"bin/git-dsf" \
        z-shell/zsh-diff-so-fancy
  '

  assert $state equals 0
  assert "$output" contains "Downloading"
  assert "$output" contains "Cloning into"

  local artifact="${ZI_DATA}/plugins/z-shell---zsh-diff-so-fancy/bin/git-dsf"
  assert "$artifact" is_file
  assert "$artifact" is_executable

  artifact="${ZI_DATA}/plugins/z-shell---zsh-diff-so-fancy/bin/diff-so-fancy"
  assert "$artifact" is_file
  assert "$artifact" is_executable
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/plugins.zunit
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/plugins.zunit
git commit -m "feat: migrate plugins.zunit to zi_test helper"
```

---

## Task 7: Migrate snippets.zunit

**Files:**
- Create: `tests/snippets.zunit`

Changes: `${SNIPPETS_DIR}` → `${ZI_DATA}/snippets`.

- [ ] **Step 1: Write `tests/snippets.zunit`**

```bash
cat > tests/snippets.zunit << 'EOF'
#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

@setup {
  load setup
  load helpers
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'zi OMZL::spectrum.zsh installation' {
  zi_test 'zi snippet OMZL::spectrum.zsh'

  assert $state equals 0
  assert "$output" contains "Downloading"

  local artifact="${ZI_DATA}/snippets/OMZL::spectrum.zsh/OMZL::spectrum.zsh"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'zi OMZP::git installation' {
  zi_test 'zi snippet OMZP::git'

  assert $state equals 0
  assert "$output" contains "Downloading"

  local artifact="${ZI_DATA}/snippets/OMZP::git/OMZP::git"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}

@test 'zi PZTM::environment installation' {
  zi_test 'zi snippet PZTM::environment'

  assert $state equals 0
  assert "$output" contains "Downloading"

  local artifact="${ZI_DATA}/snippets/PZTM::environment/PZTM::environment"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/snippets.zunit
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/snippets.zunit
git commit -m "feat: migrate snippets.zunit to zi_test helper"
```

---

## Task 8: Migrate packages.zunit

**Files:**
- Create: `tests/packages.zunit`

- [ ] **Step 1: Write `tests/packages.zunit`**

```bash
cat > tests/packages.zunit << 'EOF'
#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

@setup {
  load setup
  load helpers
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'zi package ls_colors' {
  zi_test 'zi pack for ls_colors'

  assert $state equals 0
  assert "$output" contains "Package"

  local artifact="${ZI_DATA}/plugins/ls_colors/LS_COLORS"
  assert "$artifact" is_file
  assert "$artifact" is_readable
}
EOF
```

- [ ] **Step 2: Verify syntax**

```bash
zsh -n tests/packages.zunit
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add tests/packages.zunit
git commit -m "feat: migrate packages.zunit to zi_test helper"
```

---

## Task 9: Refactor docker/entrypoint.sh

**Files:**
- Modify: `docker/entrypoint.sh`

Strip to user creation, sudo setup, and directory creation only. Remove: `wget install.sh`, symlinks to `/src/zshenv` and `/src/zshrc`, `init.zsh` sourcing.

- [ ] **Step 1: Overwrite `docker/entrypoint.sh`**

```bash
cat > docker/entrypoint.sh << 'EOF'
#!/usr/bin/env sh

HOME="/home/${ZUSER}"
export HOME

command sed -i -r 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
command adduser -D -s /bin/zsh -u "${PUID}" -h "${HOME}" "${ZUSER}"

command printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
command mkdir -p /src /data
command chown -R "${PUID}:${PGID}" /src /data
EOF
```

- [ ] **Step 2: Verify the file is syntactically valid sh**

```bash
sh -n docker/entrypoint.sh
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add docker/entrypoint.sh
git commit -m "refactor: entrypoint.sh — user creation only, drop runtime downloads"
```

---

## Task 10: Refactor docker/Dockerfile

**Files:**
- Modify: `docker/Dockerfile`

Key changes:
- Add `go` to `apk add` (needed for `go install` in direnv test and for `zunit` build)
- Install `zunit`, `revolver`, and `color` into `/usr/local/bin` at build time
- Install zi as `$ZUSER` at build time (not via `install.sh` at runtime)
- Use `ARG ZSH_VERSION` to optionally install a specific Zsh version via `zi pack` at build time
- Move `VOLUME` after all `COPY` instructions
- Remove Go from-upstream download (use `apk add go` instead)

- [ ] **Step 1: Overwrite `docker/Dockerfile`**

```bash
cat > docker/Dockerfile << 'EOF'
ARG ALPINE_VERSION=edge
FROM alpine:${ALPINE_VERSION} AS base

LABEL maintainer="Z-Shell Community"
LABEL email="team@zshell.dev"

ARG TERM=xterm
ENV TERM=${TERM}

RUN set -ex && apk --no-cache add \
  alpine-zsh-config \
  ncurses-dev \
  build-base \
  coreutils \
  pcre-dev \
  zlib-dev \
  autoconf \
  libuser \
  rsync \
  bash \
  curl \
  sudo \
  go \
  zsh \
  git \
  vim \
  jq

# Install zunit and its helpers into /usr/local/bin at build time.
# go is required to compile zunit from source.
RUN set -ex \
  && git clone --depth 1 https://github.com/zdharma/zunit.git /tmp/zunit.git \
  && cd /tmp/zunit.git && ./build.zsh \
  && mv /tmp/zunit.git/zunit /usr/local/bin/zunit \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/revolver/v0.2.4/revolver' \
       > /usr/local/bin/revolver \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/color/d8f91ab5fcfceb623ae45d3333ad0e543775549c/color.zsh' \
       > /usr/local/bin/color \
  && chmod u+x /usr/local/bin/{color,revolver,zunit} \
  && rm -rf /tmp/zunit.git

FROM base AS test

ARG ZUSER=user
ARG PUID=1000
ARG PGID=1000
ARG ZHOST=zi-docker

ENV PUID=${PUID}
ENV PGID=${PGID}
ENV ZUSER=${ZUSER}
ENV HOST=${ZHOST}

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && /entrypoint.sh

# Install zi as $ZUSER at build time — no network calls at test time.
USER ${ZUSER}
ARG ZI_BRANCH=main
RUN zsh -c "$(curl -fsSL https://install.zshell.dev)" -- -i skip

# Optionally install a specific Zsh version via zi pack at build time.
# Leave ZSH_VERSION empty for the :latest image (uses Alpine's zsh).
ARG ZSH_VERSION=
RUN [ -z "${ZSH_VERSION}" ] || \
    zsh -c "source \${HOME}/.zi/bin/zi.zsh && zi pack\"${ZSH_VERSION}\" for zsh"

# Switch back to root for COPY operations.
USER root
COPY docker/zshenv /home/${ZUSER}/.zshenv
COPY docker/zshrc  /home/${ZUSER}/.zshrc
COPY utils.zsh     /src/utils.zsh
COPY tests/        /src/tests/
RUN chown -R ${PUID}:${PGID} /home/${ZUSER}/.zshenv /home/${ZUSER}/.zshrc /src

# VOLUME declared after all COPYs — declaring before COPY silently discards copied files.
VOLUME ["/data"]

USER ${ZUSER}
WORKDIR /home/${ZUSER}

CMD ["zsh", "-il"]
EOF
```

- [ ] **Step 2: Verify the Dockerfile passes hadolint (if available locally)**

```bash
hadolint docker/Dockerfile || echo "hadolint not installed — skip"
```

- [ ] **Step 3: Commit**

```bash
git add docker/Dockerfile
git commit -m "refactor: Dockerfile — two-stage, zi pre-baked, ZSH_VERSION via zi pack, VOLUME after COPY"
```

---

## Task 11: Update docker/zshrc and docker/zshenv

**Files:**
- Modify: `docker/zshrc`
- Modify: `docker/zshenv`

Remove `prepare_system; initiate_system` from `zshrc` — these relied on `/static/` which no longer exists in the image. Source zi directly. Keep `utils.zsh` sourced for interactive convenience functions.

- [ ] **Step 1: Overwrite `docker/zshrc`**

```bash
cat > docker/zshrc << 'EOF'
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

# Source zi (pre-installed during docker build).
typeset -gA ZI
ZI[HOME_DIR]="${ZI_DATA:-/data}"
source "${HOME}/.zi/bin/zi.zsh"
autoload -Uz _zi
(( ${+_comps} )) && _comps[zi]=_zi

# Load interactive convenience wrappers.
[[ -f /src/utils.zsh ]] && source /src/utils.zsh
EOF
```

- [ ] **Step 2: Overwrite `docker/zshenv`**

```bash
cat > docker/zshenv << 'EOF'
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

export TERM=${TERM:-xterm-256color}
export SHELL=${SHELL:-${commands[zsh]}}
export ZI_DATA=${ZI_DATA:-/data}
EOF
```

- [ ] **Step 3: Verify syntax**

```bash
zsh -n docker/zshrc docker/zshenv
```

Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add docker/zshrc docker/zshenv
git commit -m "refactor: zshrc sources zi directly; drop prepare_system/initiate_system"
```

---

## Task 12: Update docker/docker-compose.yml

**Files:**
- Modify: `docker/docker-compose.yml`

The build context must be the repo root (parent of `docker/`) so that `COPY tests/` and `COPY utils.zsh` resolve correctly in the Dockerfile.

- [ ] **Step 1: Overwrite `docker/docker-compose.yml`**

```bash
cat > docker/docker-compose.yml << 'EOF'
version: "3.9"

services:
  zd:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    stdin_open: true
    tty: true
    container_name: zd
    environment:
      - TERM=xterm-256color
    volumes:
      - $PWD/..:/src
    hostname: zi@docker
EOF
```

- [ ] **Step 2: Verify the file is valid YAML**

```bash
python3 -c "import yaml, sys; yaml.safe_load(open('docker/docker-compose.yml'))" && echo "OK"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docker/docker-compose.yml
git commit -m "fix: docker-compose context updated to repo root for COPY tests/ to work"
```

---

## Task 13: Write .github/workflows/test-native.yml

**Files:**
- Create: `.github/workflows/test-native.yml`

This replaces the functionality of `zunit.yml` for day-to-day CI. Matrix is one job per `.zunit` file. Triggers on push/PR to `main` and weekly schedule.

- [ ] **Step 1: Write `.github/workflows/test-native.yml`**

```bash
cat > .github/workflows/test-native.yml << 'EOF'
name: "ZUnit (native)"

on:
  push:
    branches: [main]
    paths:
      - "tests/**"
      - "utils.zsh"
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 12 * * 1"
  workflow_dispatch:

jobs:
  zunit:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        file: [annexes, ice, packages, plugins, snippets]
    steps:
      - uses: actions/checkout@v4

      - name: Install zsh
        run: sudo apt-get update && sudo apt-get install -yq zsh

      - name: Install zunit
        run: |
          mkdir -p bin
          curl -fsSL 'https://raw.githubusercontent.com/zdharma/revolver/v0.2.4/revolver' > bin/revolver
          curl -fsSL 'https://raw.githubusercontent.com/zdharma/color/d8f91ab5fcfceb623ae45d3333ad0e543775549c/color.zsh' > bin/color
          git clone --depth 1 https://github.com/zdharma/zunit.git zunit.git
          cd zunit.git && ./build.zsh && cd ..
          mv zunit.git/zunit bin/
          chmod u+x bin/{color,revolver,zunit}

      - name: Install zi
        run: zsh -c "$(curl -fsSL https://install.zshell.dev)" -- -i skip

      - name: "ZUnit: ${{ matrix.file }}"
        run: |
          export PATH="$PWD/bin:$PATH"
          export TERM=xterm
          export ZI_BIN="${HOME}/.zi/bin"
          export ZI_DATA="${RUNNER_TEMP}/zunit"
          zunit --tap --verbose "tests/${{ matrix.file }}.zunit"
EOF
```

- [ ] **Step 2: Verify the file is valid YAML**

```bash
python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/test-native.yml'))" && echo "OK"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/test-native.yml
git commit -m "feat: add test-native.yml — native ZUnit CI without Docker"
```

---

## Task 14: Write .github/workflows/test-matrix.yml

**Files:**
- Create: `.github/workflows/test-matrix.yml`

6 jobs, one per Zsh version. Each builds its Docker image once (with `ZSH_VERSION` baked in) then runs all test files in a single container invocation. Runs on schedule and `workflow_dispatch` only — not on every push.

- [ ] **Step 1: Write `.github/workflows/test-matrix.yml`**

```bash
cat > .github/workflows/test-matrix.yml << 'EOF'
name: "ZUnit (Zsh matrix)"

on:
  schedule:
    - cron: "0 3 * * 3"
  workflow_dispatch:

jobs:
  zunit-matrix:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        zsh_version: ["5.5.1", "5.6.2", "5.7.1", "5.8", "5.8.1", "5.9"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: "Build image for Zsh ${{ matrix.zsh_version }}"
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile
          load: true
          build-args: ZSH_VERSION=${{ matrix.zsh_version }}
          tags: zd:${{ matrix.zsh_version }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: "Run all tests in Zsh ${{ matrix.zsh_version }} container"
        run: |
          mkdir -p "${RUNNER_TEMP}/zunit"
          docker run --rm \
            --env TERM=xterm \
            --env ZI_DATA=/data \
            --volume "${RUNNER_TEMP}/zunit:/data" \
            "zd:${{ matrix.zsh_version }}" \
            zsh -c 'for f in /src/tests/*.zunit; do zunit --tap --verbose "$f" || exit $?; done'
EOF
```

- [ ] **Step 2: Verify the file is valid YAML**

```bash
python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/test-matrix.yml'))" && echo "OK"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/test-matrix.yml
git commit -m "feat: add test-matrix.yml — Docker Zsh version matrix (scheduled)"
```

---

## Task 15: Clean up old files

**Files:**
- Delete: `docker/tests/` (entire directory)
- Delete: `docker/build.sh`, `docker/run.sh` (moved to `scripts/`)
- Delete: `docker/zunit.sh`, `docker/init.zsh`
- Delete: `.github/workflows/zunit.yml` (superseded by `test-native.yml`)

- [ ] **Step 1: Remove old test directory and superseded scripts**

```bash
git rm -r docker/tests/
git rm docker/build.sh docker/run.sh docker/zunit.sh docker/init.zsh
```

- [ ] **Step 2: Remove old zunit workflow**

```bash
git rm .github/workflows/zunit.yml
```

- [ ] **Step 3: Verify nothing in the repo still references the deleted paths**

```bash
grep -r 'docker/tests' . --include='*.yml' --include='*.sh' --include='*.zsh' --include='*.md' \
  --exclude-dir=.git --exclude-dir=docs 2>/dev/null || echo "No references found"

grep -r 'docker/build\.sh\|docker/run\.sh\|docker/zunit\.sh\|docker/init\.zsh' . \
  --include='*.yml' --include='*.sh' --include='*.zsh' --include='*.md' \
  --exclude-dir=.git --exclude-dir=docs 2>/dev/null || echo "No references found"
```

Expected: `No references found` for both.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove docker/tests/, old scripts, and superseded zunit.yml workflow"
```

---

## Local Test Verification (reference)

After Task 8, run the full native test suite locally (requires zi and zunit installed):

```bash
# Install zunit if not present
mkdir -p bin
git clone --depth 1 https://github.com/zdharma/zunit.git /tmp/zunit.git
cd /tmp/zunit.git && ./build.zsh && cp zunit ~/bin/ && cd -

# Run all test files
export PATH="$HOME/bin:$PATH"
export ZI_BIN="${HOME}/.zi/bin"
export ZI_DATA="/tmp/zunit-local"
for f in tests/*.zunit; do
  echo "=== $f ==="
  zunit --verbose "$f"
done
```

To run a single file during development:

```bash
ZI_BIN="${HOME}/.zi/bin" ZI_DATA="/tmp/zunit-local" zunit --verbose tests/ice.zunit
```
