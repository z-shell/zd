# Writing Tests

Tests live in `tests/` as `.zunit` files and are run by [ZUnit](https://github.com/zdharma/zunit). Each file covers a logical group of Zi functionality. The same files run in both the native CI tier and the Docker matrix — no duplication.

## Test file anatomy

Every `.zunit` file follows this structure:

```zsh
#!/usr/bin/env zunit
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

@setup {
  load setup    # resets ZI_DATA between tests
  load helpers  # provides zi_test()
  setup
}

@teardown {
  load teardown
  teardown
}

@test 'descriptive test name' {
  # test body
}
```

`@setup` and `@teardown` run before and after each `@test` block. `load setup` and `load helpers` source `tests/setup.zsh` and `tests/helpers.zsh` respectively.

---

## The `zi_test` helper

`zi_test` is the core of every test. It spawns a fresh, isolated Zsh subprocess, sources Zi, runs the snippet you pass, then captures the exit code in `$state` and all output in `$output`.

**Signature:**

```zsh
zi_test '<zi commands>' ['<pre-source configuration>']
```

Use the optional second argument only when a contract depends on configuration
that Zi reads while being sourced:

```zsh
zi_test 'alias zini 2>/dev/null' 'ZI[INTERNAL_ALIASES]=0'
```

**Minimal example:**

```zsh
@test 'fzf installs as a program' {
  zi_test 'zi lucid as"program" from"gh-r" for junegunn/fzf'

  assert $state equals 0
  assert "$output" contains "Unpacking"
  assert "$output" contains "Successfully"
}
```

**Multi-line commands** — use a single-quoted heredoc style:

```zsh
@test 'sbin ice creates shim' {
  zi_test '
    zi light z-shell/z-a-bin-gem-node
    zi light-mode as"null" from"gh-r" sbin"fzf" for junegunn/fzf
  '

  assert $state equals 0
}
```

**Testing failure** — assert non-zero exit codes explicitly:

```zsh
@test 'bad mv pattern fails with exit 1' {
  zi_test '
    zi as"command" from"gh-r" bpick"*musl*" mv"DOES_NOT_EXIST* -> fd" pick"fd/fd" \
      for @sharkdp/fd
  '

  assert $state equals 1
  assert "$output" contains "DOES_NOT_EXIST"
}
```

---

## Asserting on files

After `zi_test` runs, the installed plugin or snippet lives under `$ZI_DATA`. Use `$ZI_DATA` in assertions — never hardcode a path.

**Plugin path pattern:** `${ZI_DATA}/plugins/<owner>---<name>/<file>`

```zsh
local artifact="${ZI_DATA}/plugins/junegunn---fzf/fzf"
assert "$artifact" is_file
assert "$artifact" is_executable
```

**Snippet path pattern:** `${ZI_DATA}/snippets/<OMZL::name>/<file>`

```zsh
local artifact="${ZI_DATA}/snippets/OMZL::spectrum.zsh/OMZL::spectrum.zsh"
assert "$artifact" is_file
assert "$artifact" is_readable
```

**Polaris (programs installed via `sbin`):** `${ZI_DATA}/polaris/bin/<name>`

```zsh
assert "${ZI_DATA}/polaris/bin/fzf" is_executable
```

Note how `owner/name` becomes `owner---name` in the filesystem path — Zi replaces `/` with `---`.

---

## Variable interpolation

`zi_test` receives a string that is embedded into an inner Zsh process. There are two shells involved: the outer ZUnit shell and the inner Zsh started by `zi_test`.

- **Single quotes** — the string is passed literally; `$VAR` references resolve in the _inner_ shell (after Zi is sourced). This is the default and is what you want for most tests.
- **Double quotes** — the string is interpolated by the _outer_ shell before being passed in. Use this when you want to inject an outer variable's value.

```zsh
# Correct — expands $my_plugin in the outer (ZUnit) shell
zi_test "zi light ${my_plugin}"

# Wrong — $my_plugin is undefined in the inner shell, expands to empty
zi_test 'zi light ${my_plugin}'
```

In practice, test values are almost always literals, so single quotes are correct in the vast majority of cases.

---

## Test isolation

Each `zi_test` call is a completely fresh Zsh process. There is no shared Zi state between individual `@test` blocks — no loaded plugins, no cached data, no side-effects from previous tests.

`tests/setup.zsh` wipes `$ZI_DATA` between every `@test` block:

```zsh
setup() {
  rm -rf "${ZI_DATA:?}"/*
  mkdir -p "${ZI_DATA}"
}
```

This means tests can be run in any order and do not depend on each other.

---

## When regression coverage is required

User-visible Zi behavioral changes require focused regression coverage when they
alter a documented command, option, alias, compatibility helper, or other stable
interface. Add an assertion that would fail if the reported behavior returned,
and prefer deterministic parse, help, or isolated-function seams over live
updates and other user-state mutation. Avoid asserting incidental formatting
when a stable semantic marker is available.

Internal refactors that preserve observable behavior do not require a new test
unless they fix a demonstrated regression or change an existing contract.

---

## Adding a new suite

1. Create `tests/<name>.zunit` following the anatomy above.
2. Add `<name>` to the matrix in `.github/workflows/test-native.yml`:

   ```yaml
   matrix:
     file: [annexes, compat, ice, packages, plugins, snippets, <name>]
   ```

3. Verify locally before pushing:

   ```sh
   make test FILE=<name>
   ```

The new suite will be picked up automatically by the Docker matrix workflow (`test-matrix.yml`) — it iterates over all `*.zunit` files, so no change is needed there.

---

## Common assertion patterns

| Assertion                          | Meaning                                      |
| ---------------------------------- | -------------------------------------------- |
| `assert $state equals 0`           | Command exited successfully                  |
| `assert $state equals 255`         | Command exited with a specific non-zero code |
| `assert $state not_equal_to 0`     | Command failed (any non-zero code)           |
| `assert "$output" contains "text"` | Output includes the substring                |
| `assert "$artifact" is_file`       | Path exists and is a regular file            |
| `assert "$artifact" is_executable` | Path exists and is executable                |
| `assert "$artifact" is_readable`   | Path exists and is readable                  |

Full ZUnit assertion reference: <https://zunit.xyz/docs/writing-tests/assertions/>
