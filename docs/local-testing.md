# Local Testing

The Makefile provides four targets that cover the full local workflow: running the test suite natively, executing ad-hoc Zi commands in Docker, opening an interactive shell, and building the image locally.

## Prerequisites

**For native tests (`make test`):**
- Zsh installed (`zsh --version`)
- Zi installed — default location `~/.zi/bin`. Override with `ZI_BIN=` if installed elsewhere.
- Internet access on first run (downloads `zunit` into `bin/`)

**For Docker targets (`make run`, `make shell`, `make build`):**
- Docker running locally
- The prebuilt image pulled (`docker pull ghcr.io/z-shell/zd:latest`) — or build it with `make build`

---

## Running the test suite — `make test`

```sh
make test
```

On the first run, `make test` automatically installs `zunit`, `revolver`, and `color` into `bin/`. This mirrors exactly what the CI workflow does. Subsequent runs skip the install step (the `bin/zunit` file already exists).

```
Installing zunit into bin/ ...
Done.
==> tests/annexes.zunit
TAP version 13
ok 1 - z-a-bin-gem-node installation
ok 2 - z-a-meta-plugins installation
...
==> tests/ice.zunit
...
```

**Run a single suite:**

```sh
make test FILE=annexes
make test FILE=ice
make test FILE=packages
make test FILE=plugins
make test FILE=snippets
```

**Override where Zi is installed:**

```sh
make test ZI_BIN=/path/to/zi/bin
```

**Use a different data directory:**

```sh
make test ZI_DATA=/tmp/my-zunit-run
```

Each test suite wipes `ZI_DATA` between individual tests (via `tests/setup.zsh`), so isolation is guaranteed regardless of what you set here.

---

## Running an ad-hoc Zi command — `make run`

```sh
make run CMD="<zi snippet>"
```

This starts a fresh container from `ghcr.io/z-shell/zd:latest`, sources Zi via `zsh -il`, and runs your command. The container is removed when it exits.

**Examples:**

```sh
# Install a plugin
make run CMD="zi light z-shell/z-a-bin-gem-node"

# Load a snippet
make run CMD="zi snippet OMZL::spectrum.zsh"

# Install a program from GitHub releases
make run CMD="zi lucid as\"program\" from\"gh-r\" for junegunn/fzf"

# Use a specific image tag
make run CMD="zi light z-shell/z-a-rust" TAG=zsh-5.9
```

`CMD` is required. Running `make run` without it prints a usage error.

---

## Interactive shell — `make shell`

```sh
make shell
```

Opens an interactive Zsh session inside the container with Zi already sourced. Use this to explore the environment, debug a failing test manually, or prototype a new Zi command before writing a test for it.

```sh
$ make shell
user@zi-docker ~ $ zi light junegunn/fzf
...
user@zi-docker ~ $ which fzf
~/.zi/polaris/bin/fzf
user@zi-docker ~ $ exit
```

The container is removed on exit. State does not persist between sessions.

---

## Building the image locally — `make build`

```sh
# Build with Alpine's default Zsh (same as :latest)
make build

# Build with a specific Zsh version baked in
make build ZSH_VERSION=5.9
make build ZSH_VERSION=5.8.1

# Build with a custom image name and tag
make build IMAGE=my-zd TAG=dev
```

After building, use the image in other targets:

```sh
make run CMD="zi light fzf" IMAGE=my-zd TAG=dev
make shell IMAGE=my-zd TAG=dev
```

---

## Variable reference

| Variable | Default | Purpose |
|---|---|---|
| `ZI_BIN` | `~/.zi/bin` | Path to the Zi binary directory (native tests) |
| `ZI_DATA` | `/tmp/zunit-local` | Data directory for plugins/snippets during tests |
| `IMAGE` | `ghcr.io/z-shell/zd` | Docker image name |
| `TAG` | `latest` | Docker image tag |
| `FILE` | _(all suites)_ | Single `.zunit` suite name to run (without extension) |
| `ZSH_VERSION` | _(empty)_ | Zsh version to bake into a local Docker build |
