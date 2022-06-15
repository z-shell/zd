#!/usr/bin/env bash

export HOME=/home/${ZUSER}

sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
adduser -D -s /bin/zsh -u "${PUID}" -h "${HOME}" "${ZUSER}"

printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
mkdir -p /src /data && chown -R "${PUID}:${PGID}" /src /data

ln -sfv /src/zshenv "${HOME}"/.zshenv
ln -sfv /src/zshrc "${HOME}"/.zshrc

if [[ -f ${HOME}/init.zsh ]]; then
  chmod u+x "${HOME}"/init.zsh
  "${HOME}"/init.zsh
fi
