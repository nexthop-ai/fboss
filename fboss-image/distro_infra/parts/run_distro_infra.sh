#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <interface>"
    exit 1
fi

intf=$1
subnet=$(ip -4 addr show dev $intf | awk -F '[[:space:]/]+' '/inet/{print $3}')
echo "Listening on $intf - $subnet"

mkdir -p -m 777 /distro_infra/persistent/cache
cp /distro_infra/ipxe.efi /distro_infra/persistent/cache
cp /distro_infra/autoexec.ipxe /distro_infra/persistent/cache

nginx -c /distro_infra/nginx.conf  -p /distro_infra/persistent

dnsmasq -i $intf --no-daemon \
    --log-debug --log-dhcp \
    --port=0 \
    --enable-tftp \
    --tftp-root=/distro_infra/persistent \
    --tftp-unique-root=mac \
    --tftp-secure \
    --dhcp-script=/distro_infra/post_tftp.sh \
    --dhcp-hostsdir=/distro_infra/dnsmasq_conf.d \
    --dhcp-range=tag:fbossdut,${subnet},proxy \
    --pxe-service=tag:fbossdut,x86-64_EFI,ipxe,ipxe.efi \
    --dhcp-boot=ipxe.efi &

sleep 2 # Wait for dnsmasq log spew

# Loop asking the user for a MAC address, then creating the appropriate configuration files. Exiting the loop on an
# empty MAC
while read -rp "Enter MAC address (blank to exit): " mac; do
    if [[ "${#mac}" -eq 0 ]]; then
        break
    elif [[ "${#mac}" -ne 17 ]]; then
        echo "Invalid MAC address"
        continue
    fi

    dashmac=$(echo $mac | tr '[:upper:]:' '[:lower:]-')
    colonmac=$(echo $dashmac | tr '-' ':')

    mkdir -p -m 777 /distro_infra/persistent/${dashmac}
    ln -f /distro_infra/persistent/cache/ipxe.efi /distro_infra/persistent/${dashmac}/ipxe.efi
    ln -f /distro_infra/persistent/cache/autoexec.ipxe /distro_infra/persistent/${dashmac}/autoexec.ipxe

    echo "${colonmac},id:*,set:fbossdut" > /distro_infra/dnsmasq_conf.d/${dashmac}

    sleep 1 # Wait for dnsmasq log spew
done
