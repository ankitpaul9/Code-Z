#!/usr/bin/env bash

#------------------------------------------------------------------
# Utility to install the crts and keys for rest-server.
#------------------------------------------------------------------

if [ $# -eq 1 ]; then
   if [[ $1 -eq "-h" ]]; then
     echo "Usage: $0 [Certificates Name]"
     exit 1
   fi
else
   echo "Invalid Number of arguments"
   echo "Usage: $0 [Certificates Name]"
   exit 1
fi

current_ID_LIKE=$(command grep 'ID_LIKE=' /etc/os-release | awk -F '=' '{print $2}')
INSTALL_DIR="/opt/certs"
CRT_NAME=$1
CRTS_DIR=${INSTALL_DIR}

if [ "$current_ID_LIKE" = "debian" ]; then
    SSL_CRTS_DIR="/usr/local/share/ca-certificates/"
    UPDATE_CRTS="update-ca-certificates --fresh"
else
    SSL_CRTS_DIR="/etc/pki/ca-trust/source/anchors/"
    UPDATE_CRTS="update-ca-trust"
fi

mkdir -p ${CRTS_DIR} >/dev/null 2>&1 || { echo >&2 "CRTS folder already exists."; }
pushd ${CRTS_DIR} >/dev/null
if [ ${PWD} != $CRTS_DIR ]; then
    echo >&2 "Failed to push to crts directory."; exit 1;
fi

if [ -s ${CRT_NAME}_CA.crt -a -s ${CRT_NAME}.crt -a -s ${CRT_NAME}.key];
then
    echo "Certificates already present"
    cp ./${CRT_NAME}_CA.crt $SSL_CRTS_DIR
    ${UPDATE_CRTS}
else
    # Generating CA certificate
    openssl genrsa -out ${CRT_NAME}_CA.key 4096
    openssl req -new -x509 -days 1000 -key ${CRT_NAME}_CA.key -out ${CRT_NAME}_CA.crt -subj /C=US/ST=CALIFORNIA/L=SANJOSE/O=CODEZ/OU=IT/CN=0.0.0.0

    # Generating serveri SSL key and crt
    openssl genrsa -out ${CRT_NAME}.key
    openssl req -new -key ${CRT_NAME}.key -out ${CRT_NAME}.csr -subj /C=US/ST=CALIFORNIA/L=SANJOSE/O=CODEZ/OU=IT/CN=0.0.0.0
    openssl x509 -req -days 1000 -in ${CRT_NAME}.csr -CA ${CRT_NAME}_CA.crt -CAkey ${CRT_NAME}_CA.key -set_serial 01 -out ${CRT_NAME}.crt

    cp ./${CRT_NAME}_CA.crt $SSL_CRTS_DIR
    ${UPDATE_CRTS}
fi
popd >/dev/null
