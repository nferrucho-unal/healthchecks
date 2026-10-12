# Identificación de puntos únicos de falla (SPOFs)

Análisis sobre la arquitectura de despliegue documentada en
[`vista_cc.md`](vista_cc.md) (`docker-compose`: un servicio `web` + un servicio
`db`). 

## Alcance funcional esencial

Para Healthchecks se consideran esenciales:

1. **Recibir pings** (HTTP y, si está habilitado, SMTP).
2. Persistir el estado de checks / pings / flips.
3. Detectar caídas y enviar alertas a los canales configurados.
4. Exponer dashboard/API para operar el sistema.

## Inventario de SPOFs

| ID | Componente | Severidad | Función afectada si falla | ¿Por qué es SPOF? | 
|---|---|---|---|---|
| **S1** | **PostgreSQL (`db`)** | Crítica | Todo: pings, UI, API, alertas | Una sola instancia; sin réplica ni failover en compose | 
| **S2** | **Volumen `db-data`** | Crítica | Pérdida o indisponibilidad del estado | Único almacén persistente del dominio; sin backup/réplica declarados en el compose | 
| **S3** | **Contenedor `web` / uWSGI** | Crítica | Ingesta HTTP, dashboard, API y daemons | Un solo servicio `web`; los workers (4) mitigan fallas de *request*, no la caída del contenedor o del master | 
| **S4** | **`sendalerts` (daemon)** | Crítica (misión) | Detección de caídas y envío de alertas | Una sola instancia `attach-daemon`; si el proceso o el contenedor mueren, no hay otro consumidor de la “cola” basada en tablas | 
| **S5** | **Host / nodo de despliegue** | Crítica (infra) | Disponibilidad global | `web` y `db` suelen vivir en la misma máquina en el compose de laboratorio | 


## Detalle de los SPOFs 

### S1 - PostgreSQL

- **Impacto:** sin BD no hay escritura de pings, ni lectura de dashboard, ni polling de `sendalerts`.
- **Acoplamiento:** apps Django, `sendalerts`, `sendreports` y `smtpd` dependen del mismo almacén.
- **Mitigación:** réplica primaria/standby, HA (Patroni/Cloud managed), backups + PITR, healthchecks con failover.

### S2 - Volumen `db-data`

- **Impacto:** corrupción o pérdida del volumen = pérdida del historial y de la configuración (checks, canales, usuarios).
- **Mitigación:** backups periódicos, snapshots, réplicas geográficas.

### S3 - Contenedor `web` / proceso uWSGI master

- **Impacto:** deja de escucharse `:8000`; caen UI, API y pings HTTP. Además caen los daemons acoplados.
- **No es SPOF a nivel worker:** `processes = 4` permite sobrevivir a la muerte de un worker individual (`harakiri = 10`).
- **Sí es SPOF a nivel instancia:** no hay segundo contenedor ni balanceador en el compose.
- **Mitigación:** varias réplicas detrás de un load balancer; separar daemons del proceso web.

### S4 - `sendalerts`

- **Impacto:** los pings pueden seguir llegando y guardándose, pero **no se detectan timeouts ni se notifican** caídas → falla la promesa central del producto.
- **Por qué es único:** un solo proceso hace poll de `Check`/`Flip`; no hay cola externa con múltiples consumidores.
- **Mitigación parcial ya existente:** uWSGI reinicia el daemon si muere (`attach-daemon`), pero eso no cubre caída del contenedor ni partición prolongada.


### S5 - Host único

- **Impacto:** falla de máquina, disco o red del host tumba `web` + `db` a la vez.
- **Mitigación:** despliegue multi-AZ / multi-nodo.
