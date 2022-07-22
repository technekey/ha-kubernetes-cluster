#!/bin/bash
if [ $# -ne 1 ];then
	echo "Error: No vm_name is supplied to the script."
	exit 1
else
	domain="$1"
fi

paste  <(virsh domifaddr ${domain}) <(virsh list |grep -iE "${domain}|^-| Id") |column -s $'\t' -t 

#virsh  list --name |grep . |while read domain; do paste  <(virsh domifaddr ${domain}) <(virsh list |grep -iE "${domain}|^-| Id") |column -s $'\t' -t ;done |awk '!a[$0]++'
