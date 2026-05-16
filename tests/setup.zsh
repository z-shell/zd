#!/usr/bin/env zunit
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

setup() {
  export ZI_DATA="${TMPDIR:-/tmp}/zunit"

  {
    color magenta @setup started
    color magenta "ZI_DATA=${ZI_DATA}"
  } >&2

  # Wipe and recreate between tests. Direct rm avoids glob-no-match errors.
  rm -rf "${ZI_DATA:?}"
  mkdir -p "${ZI_DATA}"
}
