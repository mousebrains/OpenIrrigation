# Nginx and PHP-FPM configuration files

Example configuration files for running the web interface. These are installed to the appropriate system directories during setup.

## Nginx
- **nginx/nginx.conf** -- Main nginx configuration. Sets the worker user to the irrigation user (not the default www-data), enables gzip compression, and includes site configs.
- **nginx/sites-available/default** -- Virtual host configuration. Redirects HTTP to HTTPS, enables PHP-FPM via FastCGI, loads SSL certificates, and points the document root at the irrigation user's public_html directory.
- **nginx/snippets/ssl.conf** -- SSL/TLS certificate and key paths for HTTPS.

## PHP-FPM
- **php-fpm/www.conf** -- PHP-FPM pool configuration. Sets the pool user/group to the irrigation user and configures the Unix socket.
