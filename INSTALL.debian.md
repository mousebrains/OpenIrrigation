# Installation on a Raspberry Pi with Raspberry Pi OS (Debian Trixie)
---
## I use industrial SLC SD cards which have a TBW rating in excess of 250TBW. A good retail grade SD card will last 1.5-2.5 years running this system. I have not worn an industrial SLC SD card out yet.
---
## My production system is on a Raspberry Pi 3 Model B with a real time clock. I use a RasClock device.
---
## Install Raspberry Pi OS: These instructions are tested on Raspberry Pi OS (Debian Trixie) Lite
- Download and create an SD card image of [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/operating-systems/)
- I run my Raspberry Pi computers headless. To enable sshd on the first boot, touch ssh in the root directory of your SD card.
- Boot your Raspberry Pi with your SD card.
- If logging into your Raspberry Pi via ssh you will need to obtain its IP address.
- Log into your Raspberry Pi. Modern Raspberry Pi OS requires you to set a username and password during image creation (there is no longer a default `pi` user).
- Run "sudo raspi-config"
  - Change the password.
  - Update the tool.
  - Under the "Advanced Options" expand the filesystem to use the entire SD card.
  - Under the "Network Options" set the hostname.
  - Under the "Localisation Options" set your locale information.
  - Under the "Interfacing Options" enable ssh if you have not already and want it.

- Reboot and login.
- Update and upgrade:
  - sudo apt-get update
  - sudo apt-get upgrade
---
## User configuration
- I set up a dedicated user account without login privileges to run the irrigation software:
  - sudo adduser --disabled-login irrigation
  - sudo usermod -aG dialout irrigation # Add to dialout group so it can access the serial ports
---
## Optional VIM installation
I use vim with syntax highlighting:
- sudo apt-get install vim
---
## Mail server installation and setup
I use a smarthost mail relay via a gmail account.
- You will need a gmail app password for your gmail account.
- sudo apt-get install libsasl2-modules postfix
  - "satellite system"
  - FQDN
  - \[smtp.gmail.com\]:587
- To complete the installation follow these [instructions](https://www.linode.com/docs/email/postfix/configure-postfix-to-send-mail-using-gmail-and-google-apps-on-debian-or-ubuntu/)
---
## Optional zeroconf/bonjour installation
I have Apple devices on my network so I install zeroconf/bonjour:
- sudo apt-get install avahi-daemon

---
## Webserver installation
- Install nginx and php-fpm
  - sudo apt-get install nginx
  - sudo apt-get install php-fpm
- Optional: SSL certificates for nginx
  - Obtain an SSL private key and certificate, ideally CA signed.
    * If you want to use a self-signed certificate, DigitalOcean has a nice set of [instructions.](https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04)
    * My scripts for generating self-signed certificates, a local CA, and local CA signed certificates, [mkCertificates](https://github.com/mousebrains/mkCertificates)
  - I install my private key and signed certificate in /etc/nginx/certs.
    - sudo mkdir /etc/nginx/certs
    - cd /etc/nginx/certs
    - sudo chmod 600 *
    - sudo chmod 700 .
- nginx and php-fpm configuration: `sudo make install` (see [INSTALL.md](INSTALL.md)) runs
  [webserver/setup.sh](webserver/setup.sh), which configures both. See
  [webserver/README.md](webserver/README.md) for what it changes.
  - nginx and php-fpm run as their own Unix user, `oiweb` by default, which can read but not
    write the web files. setup.sh creates it; its database role is created by `make freshdb`
    (on an existing install, see webserver/README.md).
  - The Server-Sent Events status streams get their own php-fpm pool, so open browser tabs
    cannot hold up page loads and button presses.
---
## PostgreSQL installation
Install PostgreSQL
- sudo apt-get install postgresql # PostgreSQL installation
- sudo apt-get install php-pgsql # PDO module for php
---
## Python module installation
- sudo apt-get install python3-serial
- sudo apt-get install python3-psycopg
- sudo apt-get install python3-astral

## Git installation
- sudo apt-get install git
---
## I set the following shell environment variables:
- LANGUAGE=$LANG
- LC_ALL=$LANG
- PGDATABASE=irrigation # So you don't have to specify a database on the psql command line
---
## Here are the [OpenIrrigation Instructions](https://github.com/mousebrains/OpenIrrigation/blob/master/INSTALL.md)
