# -* coding: utf-8 -*-

import sys
import os
import requests as req
import pcapy
from impacket.ImpactDecoder import *

REPORT_ADDRESS = "http://localhost:5050/api/record/%s"

def report(mac_addr):
    try:
        res = req.get(REPORT_ADDRESS % mac_addr)
    except Exception as e:
        return

def handler(header, data):
    eth = EthDecoder().decode(data)
    host = eth.get_ether_shost()
    mac_addr = ":".join(["%02x" % x for x in host.tolist()]).lower()
    report(mac_addr)

def main(interface_name):
    try:
        devices = pcapy.findalldevs()
    except Exception as e:
        sys.stderr.write("No devices are found.\n")
        sys.exit(-1)

    if (not interface_name in devices):
        sys.stderr.write("Device name %s not found.\n" % interface_name)
        sys.exit(-1)

    p = pcapy.open_live(interface_name, 65536, True, 100)
    # p.setfilter("arp")
    p.loop(-1, handler)

if __name__ == "__main__":
    if (len(sys.argv) != 2):
        sys.stderr.write("python %s [Interface Name]\n")
        sys.exit(-1)

    interface_name = sys.argv[1].strip()
    main(interface_name)

