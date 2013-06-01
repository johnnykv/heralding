Quickstart
==========

Deployment overview
-------------------

.. digraph:: overview

    hive_a -> beekeeper [label="Reporting",color= "blue"];
    feeder_a -> beekeeper [label="Reporting",color= "blue"];
    feeder_b -> beekeeper [label="Reporting",color= "blue"];

    feeder_a -> hive_a [label="Honeytokens",color= "red"];
    feeder_b -> hive_a [label="Honeytokens",color= "red"]

    beekeeper -> nsm [label="Alerts", style="dashed"]
    beekeeper -> beekeeper [label="Analysis of honeytokens"];

    hive_a [label="Hive\n192.168.5.1"];
    beekeeper [label="Beekeeper\n192.168.2.2", fillcolor="palegreen", style="filled"];
    feeder_a [label="Feeder\n192.168.200.222"];
    feeder_b [label="Feeder\n192.168.200.250"];
    nsm [label="NSM", style="dashed"]

Supported protocols
-------------------

==========  ====  =========== ======
 Protocol   Auth  Interaction Notes
==========  ====  =========== ======
ssh         Yes   No          xx
vnc         Yes   No          xx
ftp         Yes   Yes         xx
telnet      Yes   Yes         xx
pop3        Yes   Yes         xx
smtp        Yes   No          xx
==========  ====  =========== ======

Installation
------------