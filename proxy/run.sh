#!/bin/sh

# Fail the whole script if any single command fails
set -e
# Copy in the default.comf.tpl template, then output a default.conf
# but substituting and of the curly brackets with environment variable values
# at runtime
envsubst < /etc/nginx/default.conf.tpl > /etc/nginx/conf.d/default.conf
# Starts nginx with the default.conf config, daemon off will run
# nginx will run in the foreground
nginx -g 'daemon off;'