# Installing Heralding in five to seven steps.

* [Step 1: Install dependencies](#step-1-install-dependencies)
* [Step 2: Checkout the code](#step-2-checkout-the-code)
* [Step 3: Setup Virtual Environment](#step-3-setup-virtual-environment)
* [Step 4: Install Heralding](#step-4-install-heralding)
* [Step 5: Customize the configuration (optional)](#step-5-customize-the-configuration-optional)
* [Step 6: Start the honeypot](#step-6-start-the-honeypot)
* [Step 7: Run Heralding as a service (optional)](#step-7-run-heralding-as-a-service-optional)

This guide is a more comprehensive version of the [README](https://github.com/johnnykv/heralding/blob/master/README.rst) geared towards installing Heralding on Ubuntu 16.04 in a Python virtual environment.

## Step 1: Install dependencies
First, we install support for Python virtual environments and other dependencies. The actual Python packages are installed later.
```
$ sudo apt-get install python3-pip python3-dev python3-venv build-essential libssl-dev libffi-dev
```

## Step 2: Checkout the code
This example puts things in the `user`'s home directory:
```
$ cd ~
$ git clone https://github.com/johnnykv/heralding.git
Cloning into 'heralding'...
remote: Counting objects: 10199, done.
remote: Total 10199 (delta 0), reused 0 (delta 0), pack-reused 10199
Receiving objects: 100% (10199/10199), 5.62 MiB | 0 bytes/s, done.
Resolving deltas: 100% (7532/7532), done.
Checking connectivity... done.
$ cd heralding
```

## Step 3: Setup Virtual Environment
Next, you need to create your virtual environment:
```
$ pwd
/home/user/heralding
$ python3 -m venv heralding-env
```

Activate the virtual environment:
```
$ source heralding-env/bin/activate
```

## Step 4: Install Heralding
Install the required packages and Heralding itself into your new virtual environment:
```
(heralding-env) $ pip install -r requirements.txt 
[...]
(heralding-env) $ pip install heralding
Collecting heralding
Requirement already satisfied: aiosmtpd in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: pyzmq in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: pyaml in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: pycrypto>=2.6.0 in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: nose in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: pyOpenSSL in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: Enum34 in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: asyncssh in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: ipify in ./heralding-env/lib/python3.5/site-packages (from heralding)
Requirement already satisfied: atpublic in ./heralding-env/lib/python3.5/site-packages (from aiosmtpd->heralding)
Requirement already satisfied: PyYAML in ./heralding-env/lib/python3.5/site-packages (from pyaml->heralding)
Requirement already satisfied: six>=1.5.2 in ./heralding-env/lib/python3.5/site-packages (from pyOpenSSL->heralding)
Requirement already satisfied: cryptography>=1.9 in ./heralding-env/lib/python3.5/site-packages (from pyOpenSSL->heralding)
Requirement already satisfied: backoff>=1.0.7 in ./heralding-env/lib/python3.5/site-packages (from ipify->heralding)
Requirement already satisfied: requests>=2.7.0 in ./heralding-env/lib/python3.5/site-packages (from ipify->heralding)
Requirement already satisfied: idna>=2.1 in ./heralding-env/lib/python3.5/site-packages (from cryptography>=1.9->pyOpenSSL->heralding)
Requirement already satisfied: cffi>=1.7 in ./heralding-env/lib/python3.5/site-packages (from cryptography>=1.9->pyOpenSSL->heralding)
Requirement already satisfied: asn1crypto>=0.21.0 in ./heralding-env/lib/python3.5/site-packages (from cryptography>=1.9->pyOpenSSL->heralding)
Requirement already satisfied: certifi>=2017.4.17 in ./heralding-env/lib/python3.5/site-packages (from requests>=2.7.0->ipify->heralding)
Requirement already satisfied: urllib3<1.23,>=1.21.1 in ./heralding-env/lib/python3.5/site-packages (from requests>=2.7.0->ipify->heralding)
Requirement already satisfied: chardet<3.1.0,>=3.0.2 in ./heralding-env/lib/python3.5/site-packages (from requests>=2.7.0->ipify->heralding)
Requirement already satisfied: pycparser in ./heralding-env/lib/python3.5/site-packages (from cffi>=1.7->cryptography>=1.9->pyOpenSSL->heralding)
Installing collected packages: heralding
Successfully installed heralding-0.2.1
```

## Step 5: Customize the configuration (optional)
You can customize the default configuration file `heralding.yml` located in the github repo's folder by first making a copy:
```
(heralding-env) $ cp heralding/heralding.yml .
```
Then make your changes & save:
```
(heralding-env) $ nano heralding.yml
```

## Step 6: Start the honeypot
Start the honeypot using the command below. We run it in the background by appending `&` to the command `sudo ./heralding-env/bin/heralding`:
```
(heralding-env) $ sudo ./heralding-env/bin/heralding &
2017-09-18 22:30:08,707 (root) Initializing Heralding version 0.2.1
2017-09-18 22:30:08,724 (heralding.reporting.file_logger) File logger started, using file: heralding_activity.log
2017-09-18 22:30:08,749 (heralding.honeypot) Found public ip: x.x.x.x
2017-09-18 22:30:08,750 (heralding.honeypot) Started Pop3S capability listening on port 995
2017-09-18 22:30:08,751 (heralding.honeypot) Started Imaps capability listening on port 993
2017-09-18 22:30:08,752 (heralding.honeypot) Started Imap capability listening on port 143
2017-09-18 22:30:08,753 (heralding.honeypot) Started https capability listening on port 443
2017-09-18 22:30:08,753 (heralding.honeypot) Started smtp capability listening on port 25
2017-09-18 22:30:08,754 (heralding.honeypot) Started Pop3 capability listening on port 110
2017-09-18 22:30:08,754 (heralding.honeypot) Started Telnet capability listening on port 23
2017-09-18 22:30:08,755 (heralding.honeypot) Started Http capability listening on port 80
2017-09-18 22:30:08,756 (heralding.honeypot) Started SSH capability listening on port 22
2017-09-18 22:30:08,757 (heralding.honeypot) Started ftp capability listening on port 21
2017-09-18 22:30:08,757 (root) Privileges dropped, running as nobody/nogroup.
```

## Step 7: Run Heralding as a service (optional)
If heralding is already running, you might want to stop it before proceeding.

Instead of running heralding interactively or in the background, you can run it as a service using `systemd` in Ubuntu 16.04. Below is an example service file you can use. It should work fine if you followed all of the previous steps above.

```
[Unit]
Description=heralding
Documentation=https://github.com/johnnykv/heralding
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/user/heralding/
Environment=VIRTUAL_ENV="/home/user/heralding/heralding-env/"
Environment=PATH="$VIRTUAL_ENV/bin:$PATH"
ExecStart=/home/user/heralding/heralding-env/bin/heralding
ExecReload=/bin/kill -s TERM $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Create the unit file for our heralding service, copy/pasting the example above and changing your `user` name if applicable:
```
$ sudo nano /etc/systemd/system/heralding.service
```

Reload `systemd`:
```
$ sudo systemctl daemon-reload
```

Then, activate the launch of the service at boot:
```
$ sudo systemctl enable heralding
```

Finally, start heralding:
```
$ sudo service heralding start
```

You can also check the status to see if its running and some log messages:
```
$ sudo service heralding status
```

That's it!
