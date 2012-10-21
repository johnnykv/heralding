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
* Tries to do login at hive at common intervals
* Logs attempts of MiTM attack. (Only possible with SSH?)
## Problems
* Again, communicating feeder logins to Hive