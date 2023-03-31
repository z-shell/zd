#!/usr/bin/env sh

export HOME=/home/"${ZUSER}"

command sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
command adduser -D -s /bin/zsh -u "${PUID}" -h "${HOME}" "${ZUSER}"

command printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
command mkdir -p /src /data && chown -R "${PUID}:${PGID}" /src /data

command -sfv /src/zshenv "${HOME}"/.zshenv
command -sfv /src/zshrc "${HOME}"/.zshrc

if [ -f "${HOME}"/init.zsh ]; then
  command chmod u+x "${HOME}"/init.zsh
  # shellcheck source=/dev/null
  . "${HOME}"/init.zsh
fi
