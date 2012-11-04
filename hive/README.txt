-- Session Dictionary --
'id' 				: 	new uuid4 for each session (uuid)
'timestamp' 		:   connection time in UTC (datetime)
'last_activity' 	: 	last recorded activity from in UTC (datetime)
'attacker_ip' 		: 	attacke IP address (string)
'attacker_src_port' : 	attacker TCP source ports (integer)
'connected' 		:	set to False when client disconnects (bool)
'protocol_port' 	: 	server portnumber (integer)
'protocol' 			:	protocol (string, eg. 'pop3')
'login_tries' : []	:	contains a login_try dict for each login attemt in this session (list of dicts)

-- Session Dictionary --
'id' 				: 	new uuid4 for each login try (uuid)
'timestamp' 		: 	utc timestamp (datetime)
'login' 			: 	(string)
'password' 			: 	(string)



   +-----------------+
   |     Session     |
   |-----------------|             +--------------+
   |id               |             |   login_try  |
   |timestamp        |             |--------------|
   |last_activity    |1        0..*|id            |
   |attacker_src_port|-------------|timestamp     |
   |attacker_ip      |             |login         |
   |connected        |             |password      |
   |protocol_port    |             +--------------+
   |protocol         |
   +-----------------+