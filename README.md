# pix-api

# 2. Subir só o banco e redis
docker-compose up -d db redis

# 3. Criar projeto Django dentro de src/
docker-compose run --rm api django-admin startproject config .

# 4. Criar app pix
docker-compose run --rm api python manage.py startapp pix

# 5. Subir tudo
docker-compose up