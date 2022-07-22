#!/bin/bash

if [ $# -ne 1 ];then
	echo "Error: You must supply a valid Guest-VM hostname"
        exit 1
else
	domain="$1"
fi

if ! virsh list |grep -q "${domain}" ;then
	echo "Info: ${domain} is not found to be running" &>2
	exit 0
fi


vm_ip=$(virsh domifaddr "${domain}" |grep -oP '\d+\.\d+\.\d+\.\d+')

echo "$domain,$vm_ip" |tr -d '\n'
