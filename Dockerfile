FROM alpine:latest
WORKDIR /app
RUN apk add gcc python3 ca-certificates iptables ip6tables tailscale python3-dev libc-dev libffi-dev ninja g++
RUN rm -rf /var/cache/apk/*
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"


# copy just this first so the installation gets cached
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . ./
#RUN ./venv/bin/pip3 install -r requirements.txt

## https://docs.docker.com/develop/develop-images/multistage-build/#use-multi-stage-builds
#FROM alpine:latest
#RUN apk update && apk add ca-certificates iptables ip6tables && rm -rf /var/cache/apk/*

RUN chmod 755 /app/start.sh /app/serve.py /app/oura_to_db.py
# Run on container startup.
CMD ["/app/start.sh"]
