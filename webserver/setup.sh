#!/bin/sh
#
# Configure nginx and php-fpm for OpenIrrigation.
# Patches system defaults in place rather than overwriting whole files.
# Run as root (via sudo make install).
#

set -eu

usage() {
    echo "Usage: $0 --user=USER" >&2
    exit 1
}

# --- Parse arguments ---
USER=
for arg in "$@"; do
    case "$arg" in
        --user=*) USER="${arg#--user=}" ;;
        *) usage ;;
    esac
done
[ -z "$USER" ] && usage

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

# Install SSL snippet
cp "${SCRIPT_DIR}/nginx/snippets/ssl.conf" /etc/nginx/snippets/ssl.conf

# Create certs directory
install -d -m 700 /etc/nginx/certs

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
