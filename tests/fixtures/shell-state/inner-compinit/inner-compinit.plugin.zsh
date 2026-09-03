# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Runs compinit from inside a plug-in body. This is the z-shell/zi#471
# arrangement: the bulk `autoload -Uz' that compinit replays happens while the
# substitution is installed, so every function compinit declares is offered to
# the loading plug-in's ownership logic. Functions the plug-in does not own must
# keep normal lazy $fpath resolution.

autoload -Uz compinit
compinit -u -d "${ZI[HOME_DIR]}/zcompdump-inner"

autoload +X -Uz _main_complete 2>/dev/null

if [[ ${functions[_main_complete]} == *_comp_setup* ]]; then
  print -r -- inner-compinit-ok
else
  print -r -- "inner-compinit-broken: [${functions[_main_complete]}]"
fi
