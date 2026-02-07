FROM alpine:3.22

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

RUN apk add --no-cache haproxy bash python3 certbot openssl curl \
    && apk add --no-cache --virtual .build-deps build-base python3-dev musl-dev linux-headers \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

RUN openssl dhparam -out /etc/haproxy/dhparam 2048 \
    && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

WORKDIR /scripts

COPY build/assets /

COPY pyproject.toml uv.lock LICENSE README.md /scripts/
COPY src/ /scripts/
COPY tests/ /scripts/tests/

RUN cd /scripts && uv sync --frozen

RUN apk del .build-deps

RUN cd /scripts && uv run pytest -s -vv tests/ && uv sync --no-dev

CMD ["uv", "run", "python", "-u", "/scripts/main.py"]
