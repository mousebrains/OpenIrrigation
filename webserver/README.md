# nginx and php-fpm configuration

`sudo make install` runs `setup.sh`, which configures the system's nginx and
php-fpm for the web interface. It patches the packaged defaults in place
rather than replacing whole files:

- **/etc/nginx/nginx.conf** -- the `user` directive is set to the web user.
- **/etc/nginx/sites-available/irrigation** -- generated from
  `nginx/sites-available/default`: HTTP redirects to HTTPS, only private
  networks are allowed, security headers, and PHP via FastCGI. The
  Server-Sent Events streams (`status.php` and `*Status.php`) go to their own
  php-fpm pool. `sites-enabled/default` is removed.
- **/etc/nginx/snippets/ssl.conf** -- the Let's Encrypt certificate for the
  host's FQDN if there is one, else a self-signed certificate.
- **/etc/php/VERSION/fpm/pool.d/www.conf** -- the `www` pool, for pages and
  the POST actions: runs as the web user, `pm = ondemand`, at most 8 workers.
- **/etc/php/VERSION/fpm/pool.d/oi-sse.conf** -- the `oi-sse` pool, written
  by `setup.sh`, for the SSE streams: at most 16 workers.

## Why two pools

Every open page holds two SSE streams (`status.php` and its own
`*Status.php`), each a php-fpm worker for as long as the page is open. In a
single pool a few open tabs used up every worker, and a POST such as "All
Off" then waited in the queue until nginx gave up with a 504. With the
streams in their own pool, open tabs cannot delay pages or actions. When a
tab closes its streams notice within about 5 seconds and free their
workers.

Memory: a worker is roughly 20 MB RSS, much of it shared with the php-fpm
master, plus a PostgreSQL backend each. `ondemand` starts workers only while
pages are open, and they exit 30 s after their last request. To measure on
the Pi with pages open:

    for p in $(pgrep -f 'php-fpm: pool'); do
        printf '%s %s kB PSS\n' "$p" "$(awk '/^Pss:/ {print $2}' /proc/$p/smaps_rollup)"
    done

## The web user

nginx and php-fpm run as a Unix user of their own, `oiweb` by default (set
with `./config --webUser=NAME`), not as the user that owns the installed
files and runs the irrigation services. The web user can read the webroot
and `php/config.php` but not write them, and it reaches PostgreSQL by peer
authentication as a role of the same name in the parent role (`irrParent`).
The web interface has no login: the nginx allow-list of private networks is
what admits clients.

`setup.sh` creates the Unix user if it is missing, and gives it search
(`x`) access to each directory above the webroot that it cannot already
search (an ACL with `setfacl` if installed, else `chmod o+x`). It then checks
that the web user can read the webroot and query the database. If any check
fails it prints why and keeps running nginx and php-fpm as the owning user,
as before, so an install never breaks the site; run it again once fixed.

`make freshdb` creates the database role, since `./config` adds the web user
to `ROLES`. An existing install needs it created once by hand.

### Moving an existing install to the web user

1. Regenerate `Makefile.params` with the options it was made with (they are
   on its third line) so it gains `WEBUSER = oiweb`:

        head -3 Makefile.params
        ./config ...same options...

2. Create the database role, using your parent role and web user names:

        sudo -u postgres psql -c "CREATE ROLE oiweb IN ROLE irrparent LOGIN INHERIT;"

3. Install. This creates the Unix user, sets permissions, rewrites the
   nginx and php-fpm configuration, and restarts nginx and php-fpm:

        make all
        sudo make install

   Read `setup.sh`'s output: it should say
   `nginx and php-fpm will run as oiweb` (before it validates the nginx
   and php-fpm configuration and ends with `Done.`) and have no WARNING
   lines.

4. Optional: remove the PHP session files the old user left. Pages cope
   without this (a browser whose session file is unreadable gets a new
   session):

        sudo find /var/lib/php/sessions -name 'sess_*' -user irrigation -delete  # your USER

### Verifying

    ps -o user=,args= -C nginx                  # workers: oiweb
    ps -o user=,args= -C php-fpm8.4             # pool www and oi-sse: oiweb
    ls -l /run/php/                             # php8.4-fpm.sock and oi-sse.sock, owner oiweb
    sudo -u oiweb test -w "$(sed -n 's/^WEBDIR = //p' Makefile.params)" && echo WRITABLE  # prints nothing
    sudo -u oiweb psql -d irrigation -c 'SELECT count(*) FROM tableInfo;'

Then open the Manual Operations and Monitor pages, check that the status bar
updates, and with a page open:

    sudo -u postgres psql -d irrigation -c \
        "SELECT usename, count(*) FROM pg_stat_activity GROUP BY 1;"   # oiweb rows

`systemctl.php` shows the unit status, but the journal lines under it only
if the web user may read the system journal (`usermod -aG systemd-journal
oiweb` grants that; it is not done by default).

### Rolling back

To run nginx and php-fpm as the owning user again, keeping everything else:

    sudo make -C webserver install WEBUSER=irrigation

(with your `USER`). The `oiweb` user and role can then be removed with
`sudo userdel oiweb` and `sudo -u postgres psql -c "DROP ROLE oiweb;"`.
Installing an older version of the code leaves `pool.d/oi-sse.conf` behind,
unused: `sudo rm /etc/php/8.4/fpm/pool.d/oi-sse.conf` and restart php-fpm.
