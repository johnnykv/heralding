# Hive
## Functionality
* Accepting common login protocols
 * POP3, IMAP, SSH, Telnet, SMTP, IRC?
* Logs all login attempts
* Marks login attempts with creds. intercepted from Feeder.

## Problems
* How do we distinct normal bruteforce attempte from login tries from intercepted credentials


# Feeder
## Functionality
* Tries to do login at hive with semi-random intervals
* Logs attempts of MiTM attack. (Only possible with SSH?)

## Problems
* Again, communicating feeder logins to Hive

## Deployment
* One feeder operating with static ip
* One feeder using the TOR network to connect to Hive
 * Making detection much harder
 * Would be interesting to see how much intercepted TOR exit traffic are actually used for Malicious purposes

#Deployment concept






	+-----------+             Unencrypted traffic
	|   Feeder  |+--------------------------------------------------+
	+-----------+         ^                                         |
   	(Static IP)           |                                         |
	                      |Intercept creds.                         v
	                      |             Reuse credentials     +------------+
	                +-----+--------++------------------------>|    Hive    |+---------> HPFeeds
	                |  Evil dudes  |                          +------------+
	                +--------------+                           (Static ip)
	                      ++------------+Intercept creds.           ^
	                                    |                           |
	+-----------+    +-------------+    v                           |
	|   Feeder  |+-->|TOR Exit Node|+-------------------------------+
	+-----------+    +-------------+         Unencrypted traffic
	 (Using TOR)