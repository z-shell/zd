#!/usr/bin/env zunit
#
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#

teardown() {
  color cyan @teardown called

  [[ -n "$DATA_DIR" ]] && {
    color red bold "Deleting $DATA_DIR" >&2
    sudo rm -rf "$DATA_DIR"
  }
}
