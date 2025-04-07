FROM postgres:15

# Set the locale
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8

# Copy initialization scripts
COPY ./init/01-create-multiple-databases.sh /docker-entrypoint-initdb.d/
COPY ./init/02-init-amr-schema.sql /docker-entrypoint-initdb.d/
COPY ./init/02a-create-bakta-schema.sql /docker-entrypoint-initdb.d/
COPY ./init/03-init-amr-antibiotic.sql /docker-entrypoint-initdb.d/
COPY ./init/04-import-sql-schema.sh /docker-entrypoint-initdb.d/

# Make initialization scripts executable
RUN chmod +x /docker-entrypoint-initdb.d/01-create-multiple-databases.sh \
    && chmod +x /docker-entrypoint-initdb.d/04-import-sql-schema.sh
