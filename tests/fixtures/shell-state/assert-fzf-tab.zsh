# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Sourced after `zi load Aloxaf/fzf-tab'. fzf-tab copies $functions[_main_complete]
# into _ftb__main_complete at load time, so the source function has to be genuinely
# resolved. If it was left autoloadable, the copy names a definition file that
# cannot exist and every completion fails at the first Tab.

if (( ! ${+functions[_ftb__main_complete]} )); then
  print -r -- "fzf-tab-broken: wrapper was never defined"
elif [[ ${functions[_ftb__main_complete]} == *"builtin autoload"* ]]; then
  print -r -- "fzf-tab-broken: wrapper is a stub [${functions[_ftb__main_complete]}]"
else
  print -r -- fzf-tab-wrapper-ok
fi
