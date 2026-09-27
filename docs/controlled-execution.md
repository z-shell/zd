# Controlled repository execution

`bin/zd run` is the local and CI interface for repository-owned commands in
controlled Linux images. It requires Python 3.10+, Git and a Docker engine.
Tests, correctness assertions and benchmark sampling stay in the consumer.

## Profiles

| Profile        | Purpose                                           | Included tools                                                   |
| -------------- | ------------------------------------------------- | ---------------------------------------------------------------- |
| `runtime`      | Clean shell validation and fixture-driven scripts | Exact Zsh, Python, runtime libraries                             |
| `module-build` | Build and test compiled modules                   | Runtime plus GCC, CMake, Git, Autoconf and development libraries |

Neither profile loads Zi or personal configuration. The existing interactive
image remains available for Zi integration. Do not infer that a clean profile
exercises plugin-manager loading, prompt rendering or deferred work.

Build with `make controlled-build PROFILE=module-build ZSH_VERSION=5.9.2
ZSH_PATCH_SET=trap-bounds-a3547fd4`. The explicit patch profile reuses the
reviewed org trap-bounds patch and runs upstream A05/B11 checks during build.
`none` selects the upstream runtime without that fix. Unpatched 5.9.2 is not
qualified by patched-runtime evidence. Supported source releases are 5.8.1,
5.9 and 5.9.2; older releases select GNU89 compiler mode, recorded in runtime
provenance. Profile qualification is separate from source-version support.

Resolve the built image ID with `docker image inspect --format '{{.Id}}'
IMAGE:TAG`. Pass that immutable ID locally, or a registry image digest in CI.
Mutable tags are refused by the runner. Pull registry digests before running;
the runner requires the selected image to be available locally.

```sh
python3 /checkouts/zd/bin/zd run \
  --image "sha256:YOUR_LOCALLY_INSPECTED_IMAGE_ID" \
  --profile module-build --source /checkouts/project \
  --output /scratch/project-check-1 --timeout 900 \
  -- zsh -f scripts/container-check.zsh
```

The example image ID must be replaced with the inspected 64-digit digest.

## Execution and evidence

The checkout is mounted read-only, then copied without Git metadata into a
writable container workspace. Commands run as the invoking user's UID/GID.
`HOME`, `ZDOTDIR` and `TMPDIR` are temporary, and host environment variables
are not inherited. `ZD_OUTPUT_DIR` identifies the evidence mount;
`ZD_SOURCE_REVISION` identifies the original checkout's HEAD. Use these
variables when source archives need a version string or an output location.

The source identity includes a content hash of copied working-tree inputs,
including nonignored untracked files and permissions. Git owns the inventory;
ignored tooling caches are omitted and submodules must be initialized.
Escaping symlinks and overlapping
source/output mounts are refused. Supply a fresh, empty output directory.
Do not run another writer in the source checkout during validation; concurrent
source changes invalidate evidence. Runtime metadata and exact image package
versions are retained alongside execution status and logs, including failures.

Supply prepared fixture checkouts with `--input zi=/checkouts/zi`. Each named
checkout is hashed, mounted read-only and copied without Git metadata under
`ZD_INPUT_DIR`. The checkout path must be its Git root. Provision these inputs
before execution; the runner does not clone or update them. `ZD_RUNNER_IMAGE`
contains the selected immutable image ID for repository benchmark metadata.

`--env NAME=value` explicitly supplies a needed variable; isolation variables
cannot be overridden. Values are not included in provenance, but a workload
can print them. Keep commands, logs and uploaded artifacts free of secrets.
`--dry-run` checks inputs and shows identities without launching a container.

Networking defaults to `none`. Integration tests can explicitly select
`--network bridge`; benchmark mode always requires `none`. Provision required
fixtures and initialized submodules before execution. No dependencies are
installed during the measured workload. `--cpuset` selects CPU affinity;
it does not reserve a core or remove host interference.

## Benchmark use

Use `--mode benchmark` and run the consumer's complete benchmark command.
Its timer belongs inside the container and excludes Docker startup. Specify
cache states explicitly; missing `.zwc` files do not imply cold disk caches.
Use balanced same-run baseline/candidate sampling and an A/A control for
regression comparisons. Image architecture must match the Docker host;
emulated performance measurements are refused.

Retain raw samples and source, image, runtime, compiler, CPU and patch identity.
Container provenance establishes inputs, not exclusive hardware access.
Native macOS, terminal, filesystem and host-integration checks remain separate.
Timing changes request review; functional failures invalidate results.

The org `actions/benchmark-report` consumes ADR-0024 comparisons after the
repository producer runs. zd execution metadata is supplementary provenance,
not a substitute for that comparison schema.

## Qualification

Run `python3 -m unittest discover -s tests -p 'test_zd.py' -v` for argument,
identity, failure and cleanup contracts. Controlled-image CI builds both
profiles, verifies exact versions and selected patches, tests configuration
isolation and failure propagation, and retains evidence. A successful image
build alone does not qualify a consumer or prove live CI behavior.
