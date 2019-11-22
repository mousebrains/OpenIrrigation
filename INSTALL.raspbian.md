# Installation on a Raspberry Pi 3 with Raspbian Buster Lite

## Install Raspbian: These instructions are tested on Raspbian Buster
- Download and create an SD card image of [Raspbian Buster Lite](https://www.raspberrypi.org/downloads/raspbian/)
- I run my Raspberry Pi computers headless. To enable sshd on the first boot, touch ssh in the root directory of your SD card.
- Boot your Raspberry Pi with your SD card.
- Log into your Raspberry Pi. The default username is pi and the default password is raspberry
- Run "sudo raspi-config" 
  - Change the password.
  - Under the "Advanced Options" expand the filesystem to use the entire SD card.
  - Under the "Network Options" set the hostname.
  - Under the "Localisation Options" set your locale information.
  - Under the "Interfacing Options" enable ssh if you have not already and want it.
 
- Reboot and login as user pi.
- Update and upgrade:
  - sudo apt-get update
  - sudo apt-get upgrade

## User configuration
- I set up a different user account to login from pi and delete the pi account
  - sudo adduser foo
  - sudo usermod -aG sudo foo # Add to sudoers
  - sudo usermod -aG dialout foo # Add to dialout so it can access serial ports
  - logout and log back in as user foo
  - check that sudo works via "sudo ls"
  - sudo deluser --remove-home pi # Remove the pi login
  - sudo delgroup pi

- I set up a dedicated user account without login privledges to run the irrigaiton software:
  - sudo adduser --disabled-login irrigation 
  - sudo usermod -aG dialout irrigation # Add to dialout group so it can access the serial ports


# Installation on a Raspberry Pi 3 with Raspbian Buster Lite

 * Raspbian
 1. Download and create SD card image of Raspbian Stretch Lite
 2. On the SD card's boot partition "touch ssh" to enable ssh at boot time for a headless system
 2. Install SD and boot up Raspberry Pi connected to the network
 3. Get network address, xxx.xxx.xxx.xxx, of the Raspberry Pi
 4. ssh pi@xxx.xxx.xxx.xxx
 5. The default password is raspberry
 6. Run "sudo raspi-config" and do the following:
  ** raspi-config options
  1. expand the filesystem 
  2. change the password
  3. got to "Internationalisation Options" and set the locale, time zone, ...
  4. go to advanced options and change the hostname
  5. finish and reboot the Raspberry Pi.
 7. ssh pi@xxx.xxx.xxx.xxx
 8. Update repository database, "sudo apt-get update"
 9. Upgrade packages, "sudo apt-get upgrade"
 1. Install VIM if you use it for syntax highlighting. "sudo apt-get install vim"
 1. Install git. "sudo apt-get install git"
 2. Insatall PostgreSQL, "sudo apt-get install postgresql"
 3. Install pyserial, "sudo apt-get install python3-serial"
 # 2. Insatall NumPy, "sudo apt-get install python3-numpy"
 # 2. Insatall Nose if using NumPy benchmarking, "sudo apt-get install python3-nose"
 8. sudo adduser irrigation and set appropriate options
 9. Install the webserver:
   9. Install NGINX, "sudo apt-get install nginx"
   9. Install PHP7.x-FPM, "sudo apt-get install php-fpm"
   9. Follow instructions at "https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04" for setting up NGINX for SSL. Please note the perfect forwarding key generating can take a long time on a Pi. I used a faster computer. I also changed all my key lengths to 4096.
   9. Uncomment lines in /etc/nginx/sites-enabled/default for php-fpm setup
   9. setup of http to redirect to https
   9. Add signed ssl certificates
   10. change root to /home/irrigation/public_html
   9. Add index.php to index line in https
   9. in nginx.conf change user to irrigation
   9. change user/group in /etc/php/.../www.conf to irrigation from www-data, there are four spots
   9. Change php-fpm from dynamic to ondemand, max workers->20


nginx:
	1. enable http2 by adding to listen line in site config

*******************

Install latest raspbian operating system. I do everything headless over a wired connection, so I enable sshd on the SD card by creatingn an empty file, ssh, in the root directory of the SD card.

Login as user pi, default password raspberry.

Run raspi_config 
sudo raspi_config
	Update to the latest raspi-config tool under the "Update" entry,
	change the default password,
	under "Network Options" set the hostname,
	under "Localisation Options" set your locale information,
	under "Interfacing Options" enable ssh, and
	under "Advanced Options" expand the file partition to fill the SD card.

Reboot and login as user pi.

Update and upgrade:
sudo apt-get update
sudo apt-get upgrade

I set up a different user account to login from pi and delete the pi account
sudo adduser foo
sudo usermod -aG sudo foo # Add to sudoers
sudo usermod -aG dialout foo # Add to dialout so it can access serial ports
logout and log back in as user foo
check that sudo works via "sudo ls"
sudo deluser --remove-home pi # Remove the pi login
sudo delgroup pi

I set up a dedicated user account without login privledges to run the irrigaiton software:
sudo adduser --disabled-login irrigation 
sudo usermod -aG dialout irrigation # Add to dialout group so it can access the serial ports

I use vim with syntax highlighting:
sudo apt-get install vim

Setup mail. I use a smarthost mail relay via a gmail account.
You will need an gmail app password for your gmail account.
See: https://www.linode.com/docs/email/postfix/configure-postfix-to-send-mail-using-gmail-and-google-apps-on-debian-or-ubuntu/
sudo apt-get libsasl2-modules postfix
	"satellite system"
	FQDN
	[smtp.gmail.com]:587

Then follow linnode's instructions

I have Mac's on my network so I install zeroconf/bonjour:
sudo apt-get install avahi-daemon

Install the webserver
 9. Install the webserver:
   9. Install NGINX, "sudo apt-get install nginx"
   9. Install PHP-FPM, "sudo apt-get install php-fpm"
   9. sudo apt-get install php-pgsql
   9. Obtain an SSL private key and certificate, ideally CA signed. If you want to use a self-signed certificate, instructions are available at: "https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04"
   9. I install my private key and certificate in /etc/nginx/certs and set the directory and file permissions to no group nor world access.
   9. Please note the perfect forwarding key generating can take a long time on a Pi. I used a faster computer. I also changed all my key lengths to 4096.
   9. Uncomment lines in /etc/nginx/sites-enabled/default for php-fpm setup
   9. setup of http to redirect to https
   9. Add signed ssl certificates
   10. change root to /home/irrigation/public_html
   9. Add index.php to index line in https
   9. in nginx.conf change user to irrigation
   9. Check nginx configuration syntax using "sudo nginx -t"
   9. change user/group in /etc/php/.../www.conf to irrigation from www-data, there are four spots
   9. Change php-fpm from dynamic to ondemand, max_childer->20


nginx:
	1. enable http2 by adding to listen line in site config
Install PostgreSQL:
sudo apt-get install postgresql

Install python modules:
sudo apt-get install python3-serial
sudo apt-get install python3-psycopg2
sudo apt-get install python3-astral

Install git
sudo apt-get install git

Clone or download the OpenIrrigation package from github.com: https://github.com/mousebrains/OpenIrrigation
git clone git@github.com:mousebrains/OpenIrrigation.git

cd to the OpenIrrigation directory and run config. Use "./config --help" for a full list of options.
Here is my config command, taking advantage of the defaults:
# For a productions system, or
./config --prefix=~irrigation --user=irrigation --roles=irrigation --roles=foo 
# for a simulated system
./config --prefix=~irrigation --user=irrigation --roles=irrigation --roles=foo  --simulate

Examine Makefile.params to make sure the configuration is what you want

Run make to build a fresh database:

make all

Install everything:

sudo make install

Enable and start the services:

sudo make enable start

To see the service status run

make status
