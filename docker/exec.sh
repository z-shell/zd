#!/usr/bin/env bash

sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
adduser -D -s /bin/zsh -u "${PUID}" -h "/home/${ZUSER}" "${ZUSER}"

printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
mkdir -p /src /data /static && chown -R "${PUID}:${PGID}" /src /data /static

ln -sfv /src/docker/zshenv /home/"${ZUSER}"/.zshenv
ln -sfv /src/docker/zshrc /home/"${ZUSER}"/.zshrc

if [[ -f /home/"${ZUSER}"/init.zsh ]]; then
  chmod u+x /home/"${ZUSER}"/init.zsh
  /home/"${ZUSER}"/init.zsh
fi
