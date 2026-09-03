# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# A plug-in that immediately autoloads a function it does not own. `_main_complete'
# ships with Zsh, so resolving it requires the caller's $fpath to survive the
# autoload substitution. See z-shell/zi#488.
#
# The assertions live here rather than in the zi_test argument because a sourced
# file is parsed only by the inner shell, so no zunit build's command quoting can
# change what is measured. See z-shell/zunit#25.

autoload +X -Uz _main_complete

if [[ ${functions[_main_complete]} == *_comp_setup* ]]; then
  print -r -- foreign-autoload-ok
else
  print -r -- "foreign-autoload-broken: [${functions[_main_complete]}]"
fi
