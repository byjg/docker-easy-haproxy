FROM alpine:3.22

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml certbot openssl curl \
    && apk add --no-cache --virtual .build-deps build-base python3-dev musl-dev linux-headers \
    && pip3 install --upgrade pip --break-system-packages \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

RUN openssl dhparam -out /etc/haproxy/dhparam 2048 \
    && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

WORKDIR /scripts

COPY build/assets /

COPY pyproject.toml LICENSE README.md /scripts/
COPY src/ /scripts/
COPY tests/ /scripts/tests/

RUN cd /scripts && uv pip install --python /usr/bin/python3 --break-system-packages ".[dev]"

RUN apk del .build-deps

RUN cd /scripts && pytest -s -vv tests/

CMD ["/usr/bin/python", "-u", "/scripts/main.py" ]
