ARG ALPINE_VERSION=edge
FROM alpine:${ALPINE_VERSION} AS base

LABEL maintainer="Z-Shell Community"
LABEL email="team@zshell.dev"

ARG TERM=xterm
ENV TERM=${TERM}

RUN set -ex && apk --no-cache add \
  alpine-zsh-config \
  ncurses-dev \
  build-base \
  coreutils \
  pcre-dev \
  zlib-dev \
  autoconf \
  libuser \
  rsync \
  bash \
  curl \
  sudo \
  go \
  zsh \
  git \
  vim \
  jq

# Install zunit and its helpers into /usr/local/bin at build time.
RUN set -ex \
  && git clone --depth 1 https://github.com/zdharma/zunit.git /tmp/zunit.git \
  && cd /tmp/zunit.git && ./build.zsh \
  && mv /tmp/zunit.git/zunit /usr/local/bin/zunit \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/revolver/v0.2.4/revolver' \
       > /usr/local/bin/revolver \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/color/d8f91ab5fcfceb623ae45d3333ad0e543775549c/color.zsh' \
       > /usr/local/bin/color \
  && chmod u+x /usr/local/bin/{color,revolver,zunit} \
  && rm -rf /tmp/zunit.git

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

# Install zi as $ZUSER at build time — no network calls at test time.
USER ${ZUSER}
ARG ZI_BRANCH=main
RUN zsh -c "$(curl -fsSL https://install.zshell.dev)" -- -i skip

# Optionally install a specific Zsh version via zi pack at build time.
# Leave ZSH_VERSION empty for the :latest image (uses Alpine's zsh).
ARG ZSH_VERSION=
RUN [ -z "${ZSH_VERSION}" ] || \
    zsh -c "source \${HOME}/.zi/bin/zi.zsh && zi pack\"${ZSH_VERSION}\" for zsh"

# Switch back to root for COPY operations.
USER root
COPY docker/zshenv /home/${ZUSER}/.zshenv
COPY docker/zshrc  /home/${ZUSER}/.zshrc
COPY utils.zsh     /src/utils.zsh
COPY tests/        /src/tests/
RUN chown -R ${PUID}:${PGID} /home/${ZUSER}/.zshenv /home/${ZUSER}/.zshrc /src

# VOLUME declared after all COPYs — declaring before COPY silently discards copied files.
VOLUME ["/data"]

USER ${ZUSER}
WORKDIR /home/${ZUSER}

CMD ["zsh", "-il"]
