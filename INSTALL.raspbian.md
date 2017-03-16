# Installation on a Raspberry Pi 3 with Raspbian Stretch Lite

 * Raspbian
 1. Download and create SD card image of Raspbian Stretch Lite
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
 2. Insatall SQLite, "sudo apt-get sqlite3"
 2. Insatall Python3, "sudo apt-get python3"
 # 2. Insatall NumPy, "sudo apt-get python3-numpy"
 # 2. Insatall Nose if using NumPy benchmarking, "sudo apt-get python3-nose"
 8. sudo adduser irrigation and set appropriate options
