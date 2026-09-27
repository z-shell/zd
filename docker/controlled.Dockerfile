# Controlled profiles are separate from the interactive Zi image.
FROM debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a AS tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential ca-certificates cmake curl git libncurses-dev libpcre2-dev \
       autoconf automake patch python3 xz-utils \
    && rm -rf /var/lib/apt/lists/*

FROM tools AS builder
ARG ZSH_VERSION=5.9.2
ARG ZSH_PATCH_SET=none
COPY docker/build-runtime.py /opt/zd/build-runtime.py
RUN ZSH_VERSION=${ZSH_VERSION} ZSH_PATCH_SET=${ZSH_PATCH_SET} python3 /opt/zd/build-runtime.py

FROM debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates python3 libncursesw6 libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/zsh /opt/zsh
COPY --from=builder /opt/zd/runtime.json /opt/zd/runtime.json
COPY --from=builder /tmp/zsh-build/zsh-*/LICENCE /usr/share/doc/zd-zsh/copyright
COPY scripts/zd.py /opt/zd/zd.py
RUN ln -s /opt/zsh/bin/zsh /usr/local/bin/zsh && dpkg-query -W > /opt/zd/packages.tsv
LABEL dev.zshell.zd.profile=runtime
ENV PATH=/opt/zsh/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /work
USER 1000:1000
CMD ["/opt/zsh/bin/zsh", "-f"]

FROM tools AS module-build
COPY --from=builder /opt/zsh /opt/zsh
COPY --from=builder /opt/zd/runtime.json /opt/zd/runtime.json
COPY --from=builder /tmp/zsh-build/zsh-*/LICENCE /usr/share/doc/zd-zsh/copyright
COPY scripts/zd.py /opt/zd/zd.py
RUN ln -s /opt/zsh/bin/zsh /usr/local/bin/zsh && dpkg-query -W > /opt/zd/packages.tsv
LABEL dev.zshell.zd.profile=module-build
ENV PATH=/opt/zsh/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /work
USER 1000:1000
CMD ["/opt/zsh/bin/zsh", "-f"]
