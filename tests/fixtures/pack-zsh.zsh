#!/usr/bin/env zsh
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

expected_zsh_version=$ZSH_VERSION

zi() {
  [[ $ZSH_VERSION == $expected_zsh_version ]] || return 91
  print -r -- "$*"
}

source "$1"
zi::pack-zsh 5.9
