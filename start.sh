#!/bin/sh
tailscaled --tun=userspace-networking &
tailscale up --authkey=${TAILSCALE_AUTHKEY} --hostname=oura_to_db-render
echo Tailscale started
nc -lk -p ${TAILSCALE_FORWARD_PORT} -e tailscale nc ${TAILSCALE_FORWARD_HOST} ${TAILSCALE_FORWARD_PORT} &
gunicorn serve:app -b :8080
