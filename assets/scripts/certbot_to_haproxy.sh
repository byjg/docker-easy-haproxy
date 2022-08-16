#!/bin/bash

# Loop through all Let's Encrypt certificates
for CERTIFICATE in `find /etc/letsencrypt/live/* -type d`; do
  CERTIFICATE=`basename $CERTIFICATE`

  # Combine certificate and private key to single file
  cat /etc/letsencrypt/live/$CERTIFICATE/fullchain.pem /etc/letsencrypt/live/$CERTIFICATE/privkey.pem > /etc/haproxy/certs/$CERTIFICATE.pem
done

# It will be checked on haproxy-reload.sh
touch /tmp/force-reload