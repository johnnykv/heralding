from smtplib import SMTP


s = SMTP('localhost', 8025)
s.sendmail('anne@example.com', ['bart@example.com'], """\
From: anne@example.com
To: bart@example.com
Subject: A test

testing
""")
s.quit()
