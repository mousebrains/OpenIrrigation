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
- nginx configuration
  - If using SSL create a file in /etc/nginx/snippets, I use [ssl.conf.](https://github.com/mousebrains/OpenIrrigation/blob/master/webserver/nginx/snippets/ssl.conf)
  - Modify /etc/nginx/sites-enabled/default to suite your needs. Here is my [example.](https://github.com/mousebrains/OpenIrrigation/blob/master/webserver/nginx/sites-available/default). I redirect all http traffic to https, enable php-fpm, load the SSL key and certificate, enable http2, and point the root at /home/irrigation/public_html.
  - Change the username that nginx runs as in /etc/nginx/nginx.conf. www-data will need to be changed to your user. I use a username of irrigation. Here is my [example.](https://github.com/mousebrains/OpenIrrigation/blob/master/webserver/nginx/nginx.conf)
  - Check for typos using the command
    - sudo nginx -t
- php-fpm configuration involves modifying the /etc/php/8.4/fpm/pool.d/www.conf file. Here is my [example](https://github.com/mousebrains/OpenIrrigation/blob/master/webserver/php-fpm/www.conf)
    - Change user and group to the same user nginx is running as. There are four locations, (user|group) and listen.(owner|group). I use irrigation for both.
    - Change "pm =" line to "pm = ondemand"
    - Change the pm.max_children line to 20"
- Restart the webserver and php-fpm.
  - sudo systemctl restart nginx php8.4-fpm
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
