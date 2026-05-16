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
       libpcre2-dev \
       zlib1g-dev \
       autoconf \
       rsync \
       bash \
       curl \
       sudo \
       golang-go \
       git \
       vim \
       jq \
  && rm -rf /var/lib/apt/lists/*

# When ZSH_VERSION is set, compile that exact release from source.
# Otherwise install the distro-packaged zsh (Debian trixie ships 5.9).
ARG ZSH_VERSION
# hadolint ignore=DL3003
RUN set -ex \
  && if [ -n "${ZSH_VERSION}" ]; then \
       apt-get update \
       && apt-get install -y --no-install-recommends wget xz-utils make \
       && rm -rf /var/lib/apt/lists/* \
       && wget -q "https://www.zsh.org/pub/zsh-${ZSH_VERSION}.tar.xz" \
       && tar xf "zsh-${ZSH_VERSION}.tar.xz" \
       && cd "zsh-${ZSH_VERSION}" \
       && ./configure --prefix=/usr/local --enable-pcre \
       && make -j"$(nproc)" \
       && make install \
       && cd .. && rm -rf "zsh-${ZSH_VERSION}"* ; \
     else \
       apt-get update \
       && apt-get install -y --no-install-recommends zsh \
       && rm -rf /var/lib/apt/lists/* ; \
     fi

# Install zunit and its helpers into /usr/local/bin at build time.
RUN git clone --depth 1 https://github.com/zdharma/zunit.git /tmp/zunit.git
WORKDIR /tmp/zunit.git
RUN set -ex \
  && ./build.zsh \
  && mv /tmp/zunit.git/zunit /usr/local/bin/zunit \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/revolver/v0.2.4/revolver' \
       > /usr/local/bin/revolver \
  && curl -fsSL 'https://raw.githubusercontent.com/zdharma/color/d8f91ab5fcfceb623ae45d3333ad0e543775549c/color.zsh' \
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

# Install zi as $ZUSER at build time — no network calls at test time.
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
COPY tests/        /src/tests/
RUN chown -R ${PUID}:${PGID} /home/${ZUSER}/.zshenv /home/${ZUSER}/.zshrc /src

# VOLUME declared after all COPYs — declaring before COPY silently discards copied files.
VOLUME ["/data"]

USER ${ZUSER}
WORKDIR /home/${ZUSER}

CMD ["zsh", "-il"]
