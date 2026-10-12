#!/bin/sh
#
# Configure nginx and php-fpm for OpenIrrigation.
# Patches system defaults in place rather than overwriting whole files.
# Run as root (via sudo make install).
#
# nginx and php-fpm run as WEBUSER, a Unix user of their own that can read
# the webroot but not write it, and that reaches PostgreSQL by peer
# authentication as a role in the parent role. setup.sh creates the Unix
# user; the database role is created by 'make freshdb', or by hand on an
# existing install (see README.md). Until WEBUSER can query the database,
# nginx and php-fpm keep running as USER, as before.
#

set -eu

usage() {
    echo "Usage: $0 --user=USER --webroot=PATH [--webuser=WEBUSER] [--dbname=DBNAME] [--domain=FQDN]" >&2
    exit 1
}

# --- Parse arguments ---
USER=
WEBUSER=
WEBROOT=
DBNAME=irrigation
DOMAIN=
for arg in "$@"; do
    case "$arg" in
        --user=*)   USER="${arg#--user=}" ;;
        --webuser=*) WEBUSER="${arg#--webuser=}" ;;
        --webroot=*) WEBROOT="${arg#--webroot=}" ;;
        --dbname=*) DBNAME="${arg#--dbname=}" ;;
        --domain=*) DOMAIN="${arg#--domain=}" ;;
        *) usage ;;
    esac
done
[ -z "$USER" ] && usage
[ -z "$WEBROOT" ] && usage
[ -z "$WEBUSER" ] && WEBUSER="$USER" # No web user configured: the old layout

# Auto-detect FQDN if not provided
if [ -z "$DOMAIN" ]; then
    DOMAIN=$(hostname -f 2>/dev/null || true)
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Detect PHP version ---
PHP_WWWCONF=$(find /etc/php -path '*/fpm/pool.d/www.conf' -type f -print 2>/dev/null \
    | sort -V | tail -n 1)
if [ -z "$PHP_WWWCONF" ]; then
    echo "Error: cannot find php-fpm www.conf" >&2
    exit 1
fi
# Extract version from path: /etc/php/8.4/fpm/pool.d/www.conf -> 8.4
PHP_VER=$(echo "$PHP_WWWCONF" | sed 's|/etc/php/\([^/]*\)/.*|\1|')
PHPFPM_SOCK="/run/php/php${PHP_VER}-fpm.sock"
# A second pool for the long-lived Server-Sent Events streams
SSE_POOL="$(dirname "$PHP_WWWCONF")/oi-sse.conf"
SSE_SOCK="/run/php/oi-sse.sock"

echo "Detected PHP ${PHP_VER} (${PHP_WWWCONF})"
echo "Using sockets: ${PHPFPM_SOCK} (pages, actions) and ${SSE_SOCK} (SSE streams)"

# --- Web user ---

# Run a command as the web user, from a directory it can enter
as_web() {
    (cd / && runuser -u "$WEBUSER" -- "$@")
}

# Give WEBUSER search (x) access to each directory above WEBROOT that it
# cannot search, e.g. a 0700 home directory: an ACL for WEBUSER alone when
# setfacl exists, else o+x. Search access opens known paths; it does not
# list the directory.
grant_traverse() {
    path=
    for part in $(echo "${WEBROOT%/}" | tr '/' ' '); do
        path="${path}/${part}"
        [ "$path" = "${WEBROOT%/}" ] && break
        as_web test -x "$path" && continue
        if command -v setfacl >/dev/null 2>&1; then
            echo "Granting ${WEBUSER} search access to ${path} (ACL)"
            setfacl -m "u:${WEBUSER}:x" "$path"
        else
            echo "Granting search access to ${path} (chmod o+x)"
            chmod o+x "$path"
        fi
    done
}

if [ "$WEBUSER" != "$USER" ]; then
    if ! id -u "$WEBUSER" >/dev/null 2>&1; then
        echo "Creating system user ${WEBUSER}"
        useradd --system --user-group --no-create-home --home-dir /nonexistent \
            --shell /usr/sbin/nologin "$WEBUSER"
    fi
    grant_traverse

    WEB_OK=yes
    for f in "${WEBROOT}/index.php" "${WEBROOT}/php/config.php"; do
        if ! as_web test -r "$f"; then
            echo "WARNING: ${WEBUSER} cannot read ${f}" >&2
            WEB_OK=no
        fi
    done
    if as_web test -w "$WEBROOT"; then
        echo "WARNING: ${WEBUSER} can write ${WEBROOT}; it should only read it" >&2
    fi
    # The pages connect as the PHP process's Unix user (peer authentication)
    if ! as_web psql -X -q -t -A -d "$DBNAME" -c 'SELECT count(*) FROM tableInfo;' >/dev/null 2>&1; then
        echo "WARNING: ${WEBUSER} cannot query database ${DBNAME}. Create its role with" >&2
        echo "  sudo -u postgres psql -c \"CREATE ROLE ${WEBUSER} IN ROLE irrparent LOGIN INHERIT;\"" >&2
        echo "(using your parent role) and run this again." >&2
        WEB_OK=no
    fi
    if [ "$WEB_OK" != yes ]; then
        echo "WARNING: keeping nginx and php-fpm running as ${USER}" >&2
        WEBUSER="$USER"
    fi
fi
echo "nginx and php-fpm will run as ${WEBUSER}"

# --- nginx ---

# Patch user directive in nginx.conf
sed -i 's/^\s*user\s\+.*;/user '"${WEBUSER}"';/' /etc/nginx/nginx.conf

# Install site config with socket paths substituted
sed -e "s|__PHPFPM_SOCK__|${PHPFPM_SOCK}|g" \
    -e "s|__SSE_SOCK__|${SSE_SOCK}|g" \
    -e "s|__WEBROOT__|${WEBROOT}|g" \
    "${SCRIPT_DIR}/nginx/sites-available/default" \
    > /etc/nginx/sites-available/irrigation

# --- SSL certificate paths ---
if [ -n "$DOMAIN" ] && [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo "Using Let's Encrypt certificate for ${DOMAIN}"
    SSL_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    SSL_KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
else
    echo "Using self-signed certificate"
    install -d -m 700 /etc/nginx/certs
    SSL_CERT="/etc/nginx/certs/irrigation.cert"
    SSL_KEY="/etc/nginx/certs/irrigation.key"
    if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
        openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
            -keyout "$SSL_KEY" -out "$SSL_CERT" \
            -subj "/CN=${DOMAIN:-localhost}"
    fi
    if [ -n "$DOMAIN" ]; then
        echo "Hint: to use Let's Encrypt, run:"
        echo "  certbot certonly --webroot -w ${WEBROOT} -d ${DOMAIN}"
    fi
fi

# Generate SSL snippet
cat > /etc/nginx/snippets/ssl.conf <<SSLEOF
ssl_certificate     ${SSL_CERT};
ssl_certificate_key ${SSL_KEY};
SSLEOF

# Enable irrigation site, disable default
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/irrigation /etc/nginx/sites-enabled/irrigation

echo "Validating nginx configuration..."
nginx -t

# --- php-fpm ---

echo "Patching ${PHP_WWWCONF}..."

# Helper: set a key = value in www.conf, handling commented-out lines too
patch_fpm() {
    key="$1"
    val="$2"
    # Uncomment if commented, then set value
    sed -i \
        -e "s|^;\?\s*${key}\s*=.*|${key} = ${val}|" \
        "$PHP_WWWCONF"
}

# Order matters: patch listen.owner/listen.group before listen,
# so the broader "listen" pattern doesn't clobber them.
# The regex anchors key matching with \s*= to avoid partial matches,
# but process dotted keys first to be safe.
patch_fpm "listen.owner" "$WEBUSER"
patch_fpm "listen.group" "$WEBUSER"
patch_fpm "listen.mode"  "0660"
patch_fpm "listen"       "$PHPFPM_SOCK"
patch_fpm "user"         "$WEBUSER"
patch_fpm "group"        "$WEBUSER"
patch_fpm "pm"           "ondemand"
# Pages and the POST actions only: requests that finish in well under a
# second, since the SSE streams have their own pool below
patch_fpm "pm.max_children" "8"
patch_fpm "pm.process_idle_timeout" "30s"
patch_fpm "pm.max_requests" "250"

echo "Writing ${SSE_POOL}..."
cat > "$SSE_POOL" <<POOLEOF
; Generated by OpenIrrigation's webserver/setup.sh; rerun it instead of editing.
;
; Each open page holds two Server-Sent Events streams (status.php and its
; own *Status.php), each a php-fpm worker for as long as the page is open.
; nginx sends them to this pool so that open tabs can never use up the
; www pool, which serves the pages and the POST actions such as All Off.
[oi-sse]
user = ${WEBUSER}
group = ${WEBUSER}
listen = ${SSE_SOCK}
listen.owner = ${WEBUSER}
listen.group = ${WEBUSER}
listen.mode = 0660
pm = ondemand
; 16 streams is 8 open pages. Each worker is roughly 20 MB RSS, much of it
; shared with the master, plus a PostgreSQL backend; ondemand starts them
; only while pages are open.
pm.max_children = 16
pm.process_idle_timeout = 30s
pm.max_requests = 250
POOLEOF

echo "Validating php-fpm configuration..."
"php-fpm${PHP_VER}" -t

# --- Restart services ---

echo "Restarting nginx and php${PHP_VER}-fpm..."
systemctl restart nginx "php${PHP_VER}-fpm"

echo "Done."
