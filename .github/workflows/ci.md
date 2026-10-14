# CI por servicio

Este documento describe [`ci.yml`](./ci.yml), el workflow de integración continua
del proyecto.

## Cuándo se ejecuta

- Cuando se crea o actualiza un pull request dirigido a `master`.
- Cuando se inicia manualmente desde la pestaña **Actions** de GitHub.

Los pushes a `master` no activan este workflow; la validación y publicación de esa
rama están a cargo de [`publish_docker_image.yml`](./publish_docker_image.yml).

## Tareas

Los jobs de pruebas, tipado y lint se ejecutan en paralelo:

- **Pruebas:** instala Python 3.14 y las dependencias del proyecto, y ejecuta toda
  la suite con `python manage.py test --verbosity 2` contra un servicio PostgreSQL
  16.
- **Mypy:** instala las dependencias, crea `hc/local_settings.py` y ejecuta
  `mypy --strict hc`.
- **Lint:** verifica el Dockerfile con Hadolint, valida las dos configuraciones de
  Docker Compose con `docker compose config -q` y analiza los workflows con
  Actionlint.
- **Imagen:** espera a que terminen correctamente `lint` y todas las pruebas.
  Construye la imagen desde `docker/Dockerfile` y la escanea con Trivy. El escaneo
  falla si encuentra vulnerabilidades corregibles de gravedad `CRITICAL` o `HIGH`;
  las que aún no tienen corrección se ignoran.
  En pull requests solo construye y escanea la imagen; al iniciarse manualmente,
  también la publica en GHCR (`ghcr.io`) con etiquetas de referencia, commit y
  `latest` para la rama predeterminada.

Las pruebas y el chequeo de tipos usan `SECRET_KEY=dummy-key` solo para estas tareas
de CI. No son credenciales de una instancia desplegada.

## Concurrencia

Las ejecuciones con la misma referencia de Git comparten un grupo de concurrencia.
Si llega una nueva ejecución para esa referencia, la anterior puede cancelarse.
