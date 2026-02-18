#!/bin/sh
#
# Configure nginx and php-fpm for OpenIrrigation.
# Patches system defaults in place rather than overwriting whole files.
# Run as root (via sudo make install).
#

set -eu

usage() {
    echo "Usage: $0 --user=USER [--domain=FQDN]" >&2
    exit 1
}

# --- Parse arguments ---
USER=
DOMAIN=
for arg in "$@"; do
    case "$arg" in
        --user=*)   USER="${arg#--user=}" ;;
        --domain=*) DOMAIN="${arg#--domain=}" ;;
        *) usage ;;
    esac
done
[ -z "$USER" ] && usage

# Auto-detect FQDN if not provided
if [ -z "$DOMAIN" ]; then
    DOMAIN=$(hostname -f 2>/dev/null || true)
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Detect PHP version ---
PHP_WWWCONF=$(ls /etc/php/*/fpm/pool.d/www.conf 2>/dev/null | head -1)
if [ -z "$PHP_WWWCONF" ]; then
    echo "Error: cannot find php-fpm www.conf" >&2
    exit 1
fi
# Extract version from path: /etc/php/8.4/fpm/pool.d/www.conf -> 8.4
PHP_VER=$(echo "$PHP_WWWCONF" | sed 's|/etc/php/\([^/]*\)/.*|\1|')
PHPFPM_SOCK="/run/php/php${PHP_VER}-fpm.sock"

echo "Detected PHP ${PHP_VER} (${PHP_WWWCONF})"
echo "Using socket: ${PHPFPM_SOCK}"

# --- nginx ---

# Patch user directive in nginx.conf
sed -i 's/^\s*user\s\+.*;/user '"${USER}"';/' /etc/nginx/nginx.conf

# Install site config with socket path substituted
sed "s|__PHPFPM_SOCK__|${PHPFPM_SOCK}|g" \
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
    if [ -n "$DOMAIN" ]; then
        echo "Hint: to use Let's Encrypt, run:"
        echo "  certbot certonly --webroot -w /home/${USER}/public_html -d ${DOMAIN}"
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
patch_fpm "listen.owner" "$USER"
patch_fpm "listen.group" "$USER"
patch_fpm "listen"       "$PHPFPM_SOCK"
patch_fpm "user"         "$USER"
patch_fpm "group"        "$USER"
patch_fpm "pm.max_children" "20"
patch_fpm "pm"           "ondemand"

# --- Restart services ---

echo "Restarting nginx and php${PHP_VER}-fpm..."
systemctl restart nginx "php${PHP_VER}-fpm"

echo "Done."
