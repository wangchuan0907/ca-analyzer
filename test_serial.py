# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import serial
import serial.tools.list_ports

print("serial.tools exists:", hasattr(serial, "tools"))

try:
    ports = list(serial.tools.list_ports.comports())
    print("ports found:", len(ports))
    for p in ports[:3]:
        desc = getattr(p, "description", "MISSING")
        dpn = getattr(p, "descriptive_port_name", "MISSING")
        name = getattr(p, "name", "MISSING")
        print(repr(p.device), "desc=", repr(desc), "dpn=", repr(dpn), "name=", repr(name))
except Exception as e:
    print("Error:", type(e).__name__, str(e))
