ARG VERSION=edge
FROM alpine:$VERSION
LABEL maintainer="<%= Z-Shell Community %>"
LABEL email="<%= team@zshell.dev =%>"

ARG DIR
ARG PUID
ARG PGID
ARG TERM
ARG ZUSER
ARG ZHOST
# Bump this ARG when a new Go release is available
ARG GO_VERSION=1.26.1

ENV DIR=${DIR:-/static}
ENV PUID=${PUID:-1000}
ENV PGID=${PGID:-1000}
ENV TERM=${TERM:-xterm}
ENV ZUSER=${ZUSER:-user}
ENV HOST=$ZHOST
ENV PATH="/usr/local/go/bin:$PATH"

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
  zsh \
  git \
  vim \
  jq

# Install Go from upstream — avoids the outdated apk package
RUN set -ex \
  && ARCH="$(uname -m)" \
  && case "$ARCH" in \
       x86_64)       GOARCH="amd64" ;; \
       aarch64)      GOARCH="arm64" ;; \
       armv6l|armv7l) GOARCH="armv6l" ;; \
       *)       echo "Unsupported arch: $ARCH" && exit 1 ;; \
     esac \
  && curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH}.tar.gz" \
     | tar -C /usr/local -xz \
  && go version

WORKDIR $DIR
COPY . .
RUN chmod +x entrypoint.sh && ./entrypoint.sh

VOLUME ["/src", "/data"]
COPY --chown=$ZUSER . /src

USER $ZUSER
WORKDIR /home/$ZUSER

RUN /tmp/install.sh -i skip

SHELL ["/bin/zsh", "-lc", "@zi-scheduler burst"]

CMD ["zsh", "-il"]
