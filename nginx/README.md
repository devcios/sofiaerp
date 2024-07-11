# NGINX

Configurar certificados de seguridad SSL para Odoo 15 en Ubuntu 20.04 utilizando Certbot y Nginx.

1. Instalar Certbot

Primero, actualiza la lista de paquetes e instala Certbot y el plugin de Nginx:

sudo apt update
sudo apt install certbot python3-certbot-nginx -y

2. Configurar Nginx para Odoo

Crea o edita el archivo de configuración de Nginx para tu dominio. Suponiendo que tu dominio es your_domain.com, crea el archivo /etc/nginx/sites-available/odoo:

sudo nano /etc/nginx/sites-available/odoo

Añade la siguiente configuración básica de Nginx para Odoo:

server {
    listen 80;
    server_name your_domain.com www.your_domain.com;
    
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    # Add Headers for odoo proxy mode
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    # log files
    access_log /var/log/nginx/odoo-access.log;
    error_log /var/log/nginx/odoo-error.log;

    # Redirect requests to odoo backend server
    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_redirect off;
    }

    # common gzip
    gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;
    gzip on;
}

Guarda el archivo y sal del editor.

Habilita el sitio de Nginx:

sudo ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/

Prueba la configuración de Nginx para asegurarte de que no hay errores:

sudo nginx -t

Reinicia Nginx para aplicar los cambios:

sudo systemctl restart nginx

3. Obtener el certificado SSL con Certbot

Ejecuta Certbot con el plugin de Nginx para obtener el certificado SSL:

sudo certbot --nginx -d your_domain.com -d www.your_domain.com

Sigue las instrucciones en pantalla. Certbot editará automáticamente tu configuración de Nginx para usar los nuevos certificados SSL.

4. Verificar la configuración de Nginx

Certbot debería haber modificado tu archivo de configuración para manejar SSL. Verifica que el archivo de configuración se vea algo así:

server {
    listen 80;
    server_name your_domain.com www.your_domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your_domain.com www.your_domain.com;

    ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    access_log /var/log/nginx/odoo-access.log;
    error_log /var/log/nginx/odoo-error.log;

    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_redirect off;
    }

    gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;
    gzip on;
}

5. Reiniciar Nginx

Reinicia Nginx para aplicar los cambios:

sudo systemctl restart nginx

6. Configuración de renovación automática

Certbot configura automáticamente una tarea cron para renovar los certificados. Puedes verificar esta configuración en /etc/cron.d/certbot.

Para asegurarte de que la renovación funciona correctamente, puedes simular una renovación:

sudo certbot renew --dry-run

Resumen

Con estos pasos, has configurado Odoo 15 en Ubuntu 20.04 con un certificado SSL de Let’s Encrypt utilizando Certbot y Nginx. Ahora tu sitio debería estar accesible de forma segura a través de HTTPS.












