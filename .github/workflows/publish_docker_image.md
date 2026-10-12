# Publicación de imágenes Docker

Este documento describe [`publish_docker_image.yml`](./publish_docker_image.yml).
El workflow valida el proyecto antes de publicar la imagen en los registros de
contenedores.

## Cuándo se ejecuta

- En cada push a `master`.
- Cuando se publica un release de GitHub.
- Cuando se inicia manualmente desde la pestaña **Actions** de GitHub.

## Jobs y orden de ejecución

Los jobs `tests`, `typecheck` y `lint` se ejecutan en paralelo:

- **Pruebas:** ejecuta los tests de `hc.api`, `hc.front`, `hc.accounts`, `hc.lib`
  y `hc.logs` con Python 3.14 y PostgreSQL 16.
- **Mypy:** ejecuta `mypy --strict hc`.
- **Lint:** revisa el Dockerfile con Hadolint, valida los manifiestos Docker Compose
  y analiza los workflows con Actionlint.
- **Imagen en GHCR:** espera a que pasen `lint`, `tests` y `typecheck`. Construye la
  imagen desde `docker/Dockerfile` y la publica en `ghcr.io/<propietario>/<repositorio>`.
- **Docker Hub:** espera a que terminen correctamente los tres chequeos y la
  publicación en GHCR. Construye y publica en Docker Hub la imagen
  `<DOCKERHUB_USERNAME>/healthchecks` para `linux/amd64`, `linux/arm/v7` y
  `linux/arm64/v8`, con SBOM.

Si falla cualquiera de los chequeos o la publicación en GHCR, Docker Hub no recibe
la imagen.

## Etiquetas

La acción de metadata genera etiquetas a partir de la rama o tag de Git y del
commit (`sha-<commit>`). En los pushes a `master`, la imagen incluye la etiqueta
`master`; para releases se usa la etiqueta correspondiente al tag del release.

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
