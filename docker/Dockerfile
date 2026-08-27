FROM debian:trixie-slim AS base

LABEL maintainer="Z-Shell Community"
LABEL email="team@zshell.dev"

ARG TERM=xterm
ENV TERM=${TERM}
ENV DEBIAN_FRONTEND=noninteractive

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
       ca-certificates \
       libncurses-dev \
       build-essential \
       coreutils \
       file \
       libpcre2-dev \
       zlib1g-dev \
       autoconf \
       automake \
       rsync \
       bash \
       curl \
       sudo \
       golang-go \
       git \
       vim \
       jq \
  && rm -rf /var/lib/apt/lists/*

# When ZSH_VERSION is set, compile that exact release from the GitHub mirror.
# Tags are formatted as zsh-X.Y.Z (e.g. zsh-5.9).
# Otherwise install the distro-packaged zsh (Debian trixie ships 5.9).
ARG ZSH_VERSION
# hadolint ignore=DL3003
RUN set -ex \
  && if [ -n "${ZSH_VERSION}" ]; then \
       git clone --depth 1 --branch "zsh-${ZSH_VERSION}" \
         https://github.com/zsh-users/zsh.git /tmp/zsh-src \
       && cd /tmp/zsh-src \
       && ./Util/preconfig \
       && install -m 0755 /usr/share/misc/config.sub Config/config.sub \
       && sed -i -E 's/\b(bool|num|str)(codes|names|fnames)\b/zsh_\1\2/g' Src/Modules/termcap.c \
       && export CFLAGS="${CFLAGS:--O2} -Wno-error=implicit-int -Wno-error=implicit-function-declaration" \
       && build_platform="$(dpkg --print-architecture)" \
       && case "${build_platform}" in \
            amd64) build_platform=x86_64 ;; \
            arm64) build_platform=aarch64 ;; \
          esac \
       && ./configure \
            --build="${build_platform}-unknown-linux-gnu" \
            --prefix=/usr/local \
            --with-tcsetpgrp \
            --enable-pcre \
       && make -j"$(nproc)" \
       && make install.bin install.fns install.modules \
       && rm -rf /tmp/zsh-src ; \
     else \
       apt-get update \
       && apt-get install -y --no-install-recommends zsh \
       && rm -rf /var/lib/apt/lists/* ; \
     fi

RUN zsh -fc 'reply=$(print -r -- command-substitution-ok); [[ ${reply} = command-substitution-ok ]]'

ENV LANG=C.UTF-8

# Install zunit and its helpers into /usr/local/bin at build time.
RUN git clone --depth 1 --branch v0.8.2 https://github.com/zdharma/zunit.git /tmp/zunit.git
WORKDIR /tmp/zunit.git
RUN set -ex \
  && ./build.zsh \
  && mv /tmp/zunit.git/zunit /usr/local/bin/zunit \
  && curl -fsSL 'https://raw.githubusercontent.com/z-shell/src/9335c8c14e0aaa845277f882969c146755e1241e/lib/zsh/snippets/revolver' \
       > /usr/local/bin/revolver \
  && curl -fsSL 'https://raw.githubusercontent.com/z-shell/src/9335c8c14e0aaa845277f882969c146755e1241e/lib/zsh/snippets/color.zsh' \
       > /usr/local/bin/color \
  && chmod a+x /usr/local/bin/color /usr/local/bin/revolver /usr/local/bin/zunit \
  && rm -rf /tmp/zunit.git

WORKDIR /

FROM base AS test

ARG ZUSER=user
ARG PUID=1000
ARG PGID=1000
ARG ZHOST=zi-docker

ENV PUID=${PUID}
ENV PGID=${PGID}
ENV ZUSER=${ZUSER}
ENV HOST=${ZHOST}

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && /entrypoint.sh

# Install Zi as $ZUSER at build time so the core checkout is fixed per image.
USER ${ZUSER}
ARG ZI_BRANCH=main
RUN git clone --depth 1 --branch "${ZI_BRANCH}" \
  https://github.com/z-shell/zi.git \
  "${XDG_DATA_HOME:-${HOME}/.local/share}/zi/bin" \
  && mkdir -p \
  "${XDG_DATA_HOME:-${HOME}/.local/share}/zi/cache" \
  "${XDG_DATA_HOME:-${HOME}/.local/share}/zi/completions" \
  "${XDG_DATA_HOME:-${HOME}/.local/share}/zi/plugins" \
  "${XDG_DATA_HOME:-${HOME}/.local/share}/zi/snippets"

# Switch back to root for COPY operations.
USER root
COPY docker/zshenv /home/${ZUSER}/.zshenv
COPY docker/zshrc  /home/${ZUSER}/.zshrc
COPY docker/utils.zsh /src/utils.zsh
COPY docker/utils.zsh /src/docker/utils.zsh
COPY tests/        /src/tests/
RUN chown -R ${PUID}:${PGID} /home/${ZUSER}/.zshenv /home/${ZUSER}/.zshrc /src

# VOLUME declared after all COPYs — declaring before COPY silently discards copied files.
VOLUME ["/data"]

USER ${ZUSER}
WORKDIR /home/${ZUSER}

CMD ["zsh", "-il"]
