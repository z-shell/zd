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
       x86_64)        GOARCH="amd64" ;; \
       aarch64)       GOARCH="arm64" ;; \
       armv6l|armv7l) GOARCH="armv6l" ;; \
       *)             echo "Unsupported arch: $ARCH" && exit 1 ;; \
     esac \
  && GO_TARBALL="go${GO_VERSION}.linux-${GOARCH}.tar.gz" \
  && rm -rf /usr/local/go \
  && curl -fsSL "https://go.dev/dl/${GO_TARBALL}" -o "/tmp/${GO_TARBALL}" \
  && EXPECTED_SHA256="$(curl -fsSL 'https://go.dev/dl/?mode=json&include=all' \
       | jq -r --arg f "${GO_TARBALL}" '.[].files[] | select(.filename==$f) | .sha256')" \
  && [ -n "${EXPECTED_SHA256}" ] || { echo "Failed to retrieve SHA256 for ${GO_TARBALL}" && exit 1; } \
  && echo "${EXPECTED_SHA256}  /tmp/${GO_TARBALL}" | sha256sum -c - \
  && tar -C /usr/local -xzf "/tmp/${GO_TARBALL}" \
  && rm -f "/tmp/${GO_TARBALL}" \
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
