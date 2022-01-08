#!/usr/bin/env zsh

zi::setup() {
  source /src/zi/zi.zsh
}

zi::reload() {
  local zf1 zf2
  for zf1 in /src/zi/*.zsh; do
    source "$zf1"
  done
  for zf2 in /src/zi/lib/zsh/*.zsh; do
    source "$zf2"
  done
}

zi::setup-keys() {
  zi snippet OMZL::key-bindings.zsh
}

zi::setup-annexes() {
  zi light-mode compile'*handler' for \
    z-shell/z-a-meta-plugins \
    @annexes
}

zi::setup-annexes+rec() {
  zi light-mode compile'*handler' for \
    z-shell/z-a-meta-plugins \
    @annexes+rec
}

zi::setup-annexes-extra() {
  # Dependencies
  sudo apk add ruby-dev grep tree
  zi::install-zsdoc

  zi light-mode compile'*handler' for \
    z-shell/z-a-man \
    z-shell/z-a-test
}

zi::install-zsdoc() {
  zi light-mode \
    make"PREFIX=$ZPFX install" \
    for z-shell/zsdoc
}

zi::setup-minimal() {
  zi wait lucid light-mode for \
    atinit"zicompinit; zicdreplay" \
    z-shell/F-Sy-H \
    atload"_zsh_autosuggest_start" \
    zsh-users/zsh-autosuggestions \
    blockf atpull'zi creinstall -q .' \
    zsh-users/zsh-completions
}

zi::pack-zsh() {
  local version="$1"
  zi pack"$version" for zsh
}
