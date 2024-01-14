#!/usr/bin/env python3

import lirc

if __name__ == '__main__':
    lirc_client = lirc.Client()
    lirc_client.send_once("HK970", "KEY_POWER")
    
    with open('/proc/asound/E30/pcm0p/sub0/status', 'r') as soundStatusfile:
        status = soundStatusfile.readline().strip("\n")

    print (status)
    print ("Status is " + ("closed" if (status == 'closed') else "not closed"))