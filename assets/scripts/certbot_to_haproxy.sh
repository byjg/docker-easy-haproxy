#!/bin/bash

source /scripts/functions.sh

# Loop through all Let's Encrypt certificates
for CERTIFICATE in `find /etc/letsencrypt/live/* -type d`; do
  CERTIFICATE=`basename $CERTIFICATE`

  # Combine certificate and private key to single file
  cat /etc/letsencrypt/live/$CERTIFICATE/fullchain.pem /etc/letsencrypt/live/$CERTIFICATE/privkey.pem > /certs/letsencrypt/$CERTIFICATE.pem
done

# It will be checked on haproxy-reload.sh
touch /tmp/force-reload