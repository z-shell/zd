#!/usr/bin/env zsh

# Functions to wrap container setup and initialization.

prepare_system() {
  printf '%s\n' "Setting owner of /data to ${PUID}:${PGID}" >&2
  sudo chown -R "${PUID}:${PGID}" /data

  printf '%s\n' "Copying files from /static to /data" >&2
  rsync -raq /static/ /data
}

initiate_system() {
  typeset -gxU path module_path

  path=("${ZPFX:-${HOME}/.zi/polaris}/bin" "${HOME}/go/bin" $path)
  module_path+=( /data/zmodules/zpmod/Src )

  zmodload zi/zpmod &>/dev/null

  source ~/.zi/bin/zi.zsh

  autoload -Uz _zi
  (( ${+_comps} )) && _comps[zi]=_zi
}

reload_system() {
  local zf1 zf2
  for zf1 in ~/.zi/bin/*.zsh; do
    source "$zf1"
  done
  for zf2 in ~/.zi/bin/lib/zsh/*.zsh; do
    source "$zf2"
  done
}

# Functions to wrap Zi commands.

zi::install-zsdoc() {
  zi light-mode \
    make"PREFIX=$ZPFX install" \
    for z-shell/zsdoc
}

zi::setup-keys() {
  zi snippet OMZL::key-bindings.zsh
}

zi::setup-annexes() {
  zi light-mode for \
    z-shell/z-a-meta-plugins @annexes
}

zi::setup-annexes+rec() {
  zi light-mode for \
    z-shell/z-a-meta-plugins @annexes+rec
}

zi::setup-annexes+add() {
  sudo apk add ruby-dev grep tree
  zi::install-zsdoc
  zi light-mode for z-shell/z-a-test
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
  local ZSH_VERSION="$1"
  zi pack"$ZSH_VERSION" for zsh
  zi pack atload=+"zicompinit; zicdreplay" for system-completions
}
