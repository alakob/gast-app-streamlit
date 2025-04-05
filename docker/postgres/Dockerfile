FROM postgres:15

# Set the locale
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8

# Copy initialization scripts
COPY ./init/create-multiple-databases.sh /docker-entrypoint-initdb.d/

# Make initialization scripts executable
RUN chmod +x /docker-entrypoint-initdb.d/create-multiple-databases.sh
