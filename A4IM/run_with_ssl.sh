#!/bin/bash
# Force older TLS versions and disable TLS 1.3
export GIT_SSL_GNUTLS_PRIORITY="NORMAL:-VERS-TLS1.3:+VERS-TLS1.2:+VERS-TLS1.1:+VERS-TLS1.0"
# Configure git to use this SSL version
git config --global http.sslVersion tlsv1.2
# Run the program
./run_gitfilereader.sh