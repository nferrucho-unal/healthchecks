# Terraform

Esta configuración despliega Healthchecks en AWS mediante tres módulos:

- `networking`: VPC en dos zonas de disponibilidad, subredes públicas para ALB/ECS y subredes privadas para RDS.
- `compute`: ECS Fargate, Application Load Balancer, grupos de seguridad, logs de CloudWatch y secretos de Django.
- `database`: PostgreSQL RDS privado, backups automáticos y contraseña aleatoria en AWS Secrets Manager.

Las tareas ECS usan la imagen pública `healthchecks/healthchecks` y la configuración de PostgreSQL que espera la aplicación (`DB`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`). Las migraciones se ejecutan al iniciar el contenedor, según `docker/uwsgi.ini`.

## Despliegue

Requisitos: Terraform 1.5 o superior, una cuenta AWS y credenciales disponibles mediante el mecanismo estándar de AWS (por ejemplo, AWS CLI o variables de entorno). No se requiere configurar recursos desde la consola web.

Desde este directorio, seleccione un tag publicado de versión (`vX.Y`) o un tag `sha-<commit>`; no se aceptan tags móviles como `latest` o `master`:

```sh
terraform init
terraform fmt -recursive
terraform validate
terraform plan -var='image_tag=vX.Y'
terraform apply -var='image_tag=vX.Y'
```

La URL pública queda disponible con `terraform output -raw service_url`. Repetir `plan`/`apply` sin cambiar entradas conserva el estado deseado. La base de datos está protegida contra eliminación mediante `prevent_destroy` y la protección de borrado de RDS; además, si ambas guardas se retiran intencionalmente, Terraform exige crear un snapshot final con identificador único.

`terraform destroy` queda bloqueado mientras la protección de RDS permanezca en la configuración. Para una baja deliberada, primero retire `prevent_destroy` y aplique `deletion_protection = false` manteniendo el recurso declarado. En una segunda operación, elimine el recurso; Terraform creará el snapshot final configurado antes de borrar RDS.

Terraform guarda estado local por defecto. El estado contiene valores sensibles generados, aunque estén marcados como sensibles, por lo que no debe compartirse ni añadirse a Git. Para trabajo en equipo, configure un backend remoto S3 cifrado y con bloqueo antes de aplicar. La contraseña de PostgreSQL y la clave Django se generan automáticamente y se guardan en Secrets Manager; ECS las obtiene al iniciar cada tarea.

## Alcance de red

El ALB publica HTTP en el puerto 80 y las tareas ECS tienen IP pública para descargar la imagen de Docker Hub, pero su puerto 8000 solo acepta tráfico desde el ALB. RDS no es público y solo acepta conexiones desde las tareas. Para una instalación expuesta en producción, añada terminación TLS y un dominio antes de publicar la URL.