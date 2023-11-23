#!/usr/bin/env sh

HOME="/home/${ZUSER}"

export HOME

command sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
command adduser -D -s /bin/zsh -u "${PUID}" -h "${HOME}" "${ZUSER}"

command printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
command mkdir -p /src /data
command chown -R "${PUID}:${PGID}" /src /data

command wget 'https://raw.githubusercontent.com/z-shell/zi-src/main/lib/sh/install.sh' -qO /tmp/install.sh
command chown "${PUID}:${PGID}" /tmp/install.sh
command chmod u+x /tmp/install.sh

command ln -sfv /src/zshenv "${HOME}/.zshenv"
command ln -sfv /src/zshrc "${HOME}/.zshrc"

if [ -f "${HOME}"/init.zsh ]; then
  command chmod u+x "${HOME}"/init.zsh
  # shellcheck source=/dev/null
  . "${HOME}"/init.zsh
fi
