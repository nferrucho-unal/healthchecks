# Publicación de imágenes Docker

Este documento describe [`publish_docker_image.yml`](./publish_docker_image.yml).
El workflow valida el proyecto, publica la imagen en GHCR y, después de un escaneo
de seguridad, la publica también en Docker Hub.

## Cuándo se ejecuta

- En cada push a `master`.
- Cuando se publica un release de GitHub.
- Cuando se inicia manualmente desde la pestaña **Actions** de GitHub.

## Jobs y orden de ejecución

Los jobs `tests`, `typecheck` y `lint` se ejecutan en paralelo:

- **Pruebas:** instala Python 3.14 y las dependencias del proyecto, y ejecuta toda
  la suite con `python manage.py test --verbosity 2` contra PostgreSQL 16.
- **Mypy:** crea `hc/local_settings.py` y ejecuta `mypy --strict hc`.
- **Lint:** revisa el Dockerfile con Hadolint, valida los manifiestos Docker Compose
  y analiza los workflows con Actionlint.
- **Imagen en GHCR:** espera a que pasen `lint`, `tests` y `typecheck`. Construye la
  imagen desde `docker/Dockerfile` y la publica en
  `ghcr.io/<propietario>/<repositorio>`.
- **Docker Hub:** espera a que terminen correctamente los tres chequeos y la
  publicación en GHCR. Primero construye una imagen local y la escanea con Trivy;
  falla si encuentra vulnerabilidades corregibles `CRITICAL` o `HIGH`, e ignora las
  que aún no tienen corrección. Si pasa el escaneo, construye y publica
  `<DOCKERHUB_USERNAME>/healthchecks` para `linux/amd64`, `linux/arm/v7` y
  `linux/arm64/v8`, con SBOM.

Si falla un chequeo, la publicación en GHCR o el escaneo Trivy, Docker Hub no recibe
la imagen. Como GHCR se publica antes del job de Docker Hub, un fallo de Trivy no
revierte la imagen que ya se haya publicado en GHCR.

## Etiquetas

Para GHCR, las etiquetas incluyen la referencia de rama o pull request, el commit
y `latest` en la rama predeterminada. Para Docker Hub, se generan etiquetas para la
rama o tag y para el commit con el prefijo `sha-`. Así, los pushes a `master` usan
la etiqueta `master`; los releases usan su tag en Docker Hub y la etiqueta del
commit en GHCR.

## Configuración de Docker Hub

Configura estos secretos del repositorio en **Settings → Secrets and variables →
Actions**:

- `DOCKERHUB_USERNAME`: usuario de Docker Hub.
- `DOCKERHUB_TOKEN`: access token de Docker Hub con permisos para publicar en el
  repositorio `healthchecks` de ese usuario. Crea el repositorio en Docker Hub si
  todavía no existe.

El workflow también necesita permiso de escritura de paquetes para publicar en
GHCR. Usa `GITHUB_TOKEN`, que GitHub Actions proporciona, y concede al workflow el
permiso `packages: write`.

## Claves de la aplicación

Los jobs de pruebas y tipado usan `SECRET_KEY=dummy-key` como valor de prueba. La
construcción de la imagen usa `build-key` únicamente durante la preparación de
archivos estáticos. Ninguna de esas claves configura la instancia desplegada: la
clave de ejecución debe definirse por separado en la configuración del entorno de
despliegue, por ejemplo en `docker/.env`.
