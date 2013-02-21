# Beeswarm [![Build Status](https://travis-ci.org/johnnykv/beeswarm.png?branch=master)](https://travis-ci.org/johnnykv/beeswarm)
A honeypot project which will try to estimate how, where and when credentials are intercepted and reused.
The project consists of two independent parts:
* Hive
 * Multiprotocol honeypot, comes default with ssh, pop3, pop3s, ssh, ftp and telnet capability.
 * Extendable, both in terms of new protocols but can also be extended to provide shell like feature like Kippo.
 * Distributes all login attempts using hpfeeds. (beeswarn.hive)
* Feeder (currently under initial development)
 * Simulates a normal end-user system by regulary interacting with Hive.
 * Distributes all login attempts using hpfeeds. (beeswarn.feeder)


## Hive
### Installation
``` shell
$>pip install -r requirements.txt
$>openssl req -new -newkey rsa:1024 -days 365 -nodes -x509 -keyout server.key -out server.crt
$>openssl rsa -in server.key -text -out server.key
```

### Sample usage

```
$>sudo python run_hive.py
2013-02-21 10:36:05,975 (root) Consumer created.
2013-02-21 10:36:05,976 (root) Started pop3 capability listening on port 110
2013-02-21 10:36:05,976 (root) Started pop3s capability listening on port 995
2013-02-21 10:36:05,976 (root) Started telnet capability listening on port 23
2013-02-21 10:36:05,976 (root) Started ssh capability listening on port 2222
2013-02-21 10:36:05,976 (root) Started ftp capability listening on port 21
2013-02-21 10:36:05,980 (root) Privileges dropped, running as nobody/nobody.
2013-02-21 10:36:05,982 (hive.consumer.loggers.hpfeeds) Connecting to feed broker at hpfeeds.honeycloud.net:10000
2013-02-21 10:36:06,012 (hive.consumer.loggers.hpfeeds) Connected to hpfeed broker.
2013-02-21 10:37:01,444 (hive.models.session) telnet authentication attempt from 192.168.1.123. [james/bond] (7cee7b1c-2b1b-42ac-a963-156ecb58f2f1)
2013-02-21 10:37:49,787 (hive.models.session) ssh authentication attempt from 192.168.1.123. [root/toor] (6cda8971-aefd-41a6-9a96-caf4c7407028)
2013-02-21 10:37:50,113 (hive.models.session) ssh authentication attempt from 192.168.1.123. [root/qwerty] (6cda8971-aefd-41a6-9a96-caf4c7407028)
```

## Feeder
Still under development.

# Concept for deployment

## General
* One Hive operating with static ip.
 * Transmits login attempts on HPFeed channel beeswarm.hive
* Several feeders interacting with Hive services.
 * Some connect directly, other using various proxies (TOR, VPN providers, etc)
 * Transmits activity on HPFeed channel beeswarm.feeder
* [Mnemosyne](https://github.com/johnnykv/mnemosyne) correlates data on beeswarm.hive and beeswarm.feeder to identify malicious usage.

## Deployment diagram
                                  (honeybees)
    +-----------+                   Traffic
    |   Feeder  |+--------------------------------------------------+
    +-----------+           ^                                       |
    (Static IP)             |                                       |
                            |Intercept creds.                       |
                            |                                       |
                            |                                       v
                    +-------+------+     Reuse credentials    +------------+
                    |  Evil dudes  |+------------------------>|    Hive    |+---------> HPFeeds
                    +-------+------+                          +------------+
                            |                                  (Static ip)
                            |Operates exit node                     ^
                            |(and intercepting creds)               |
                            |                                       |
                            v                                       |
    +-----------+    +-------------+                                |
    |   Feeder  |+-->|TOR Exit Node|+-------------------------------+
    +-----------+    +-------------+               Traffic
     (Using TOR)                                 (honeybees)
