FROM debian:bookworm-slim
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt install -y nginx-light
RUN rm /etc/nginx/sites-enabled/default
RUN apt-get install -y  wget
RUN mkdir /conf
RUN mkdir /conf/tar1090
RUN wget -nv -O /conf/tar1090/tar1090.conf https://github.com/wiedehopf/tar1090/raw/master/nginx.conf
RUN printf "server{\n listen 80 default_server;\n listen [::]:80 default_server; \n root /var/www/html;\n  include /usr/local/share/tar1090/nginx-tar1090-webroot.conf;\n location /re-api/ {\n gzip on; proxy_http_version 1.1; \n proxy_max_temp_file_size 0;\n proxy_pass http://readsb:30152;\n } \n} \n server{ \n listen 89; \n  root /coverage/ ; location /graphs1090/graphs/ { gzip on; alias /run/graphs1090/; } location /graphs1090 { alias /usr/share/graphs1090/html/;  gzip on; } rewrite ^/perf$ /graphs1090/ permanent;} " >>  /etc/nginx/sites-enabled/default




RUN chown -R www-data:www-data /var/lib/nginx
RUN chown -R www-data:www-data /var/log/nginx
RUN chown -R www-data:www-data /run
RUN chown -R www-data:www-data /etc/nginx
RUN chown -R www-data:www-data /var/www/html/

USER www-data

EXPOSE 89/tcp
EXPOSE 80/tcp
CMD cat /etc/nginx/sites-enabled/default  && \
    ls -lah /coverage && \
    nginx -g 'daemon off;' 
   

