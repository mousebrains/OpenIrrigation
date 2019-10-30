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
