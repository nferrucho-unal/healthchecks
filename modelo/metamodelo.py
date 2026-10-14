"""Metamodelo de arquitectura del proyecto Healthchecks.

Este script es el resultado de revisar la arquitectura REAL del repositorio
(no un ejemplo ficticio) y de aplicar sobre ella el mismo enfoque de
metamodelado usado en ``references/metamodelo.ipynb``:

1. Un **DSL de arquitectura** basado en textX (``Model -> Layer/Component/
   Connector``) que describe las capas, los componentes y los conectores de
   Healthchecks, y que se puede graficar con Graphviz.
2. Un **metamodelo de calidad** (``Element -> Component/Connector/Pattern/
   Tactic/QualityAttribute/QualityScenario``) implementado con
   ``dataclasses``, que conecta tácticas y patrones reales del código con los
   atributos de calidad que atienden.

Fuentes revisadas para construir el modelo:
    - ``docker-compose.yml``                        (topología de servicios)
    - ``docker/Dockerfile`` y ``docker/uwsgi.ini``   (proceso uWSGI + daemons)
    - ``hc/settings.py``                             (INSTALLED_APPS, DATABASES,
                                                       CACHES, S3_*, EMAIL_*)
    - ``hc/api/models.py``                           (Check, Ping, Flip, Channel,
                                                       Notification, TokenBucket,
                                                       TRANSPORTS)
    - ``hc/api/management/commands/*.py``            (sendalerts, sendreports,
                                                       smtpd, pruneobjects,
                                                       prunetokenbucket, ...)
    - ``hc/integrations/*``                          (29 canales de notificación)
    - ``hc/accounts/models.py``                      (Profile, Project, Member,
                                                       Credential/WebAuthn)

Requisitos del laboratorio cubiertos por este archivo:
    * Revisión de la arquitectura del proyecto               -> ver docstrings
      y el modelo ``ARCHITECTURE_MODEL`` más abajo.
    * Identificación de los componentes arquitectónicos       -> función
      ``clasificar_componentes()`` / sección "Componentes arquitectónicos".
    * Identificación de los componentes de servicio           -> función
      ``clasificar_componentes()`` / sección "Componentes de servicio".

Ejecución:
    python arquitectura/metamodelo.py

Dependencias opcionales (el script funciona en modo degradado si faltan):
    pip install textX graphviz
    # además, para renderizar el PNG se necesita el binario "dot" de Graphviz
    # (apt install graphviz / choco install graphviz / brew install graphviz)

Si ``textX`` no está instalado, el script no puede construir el modelo de
arquitectura (es su base). Si ``graphviz`` (el binario ``dot``) no está
instalado, el script igual genera el archivo fuente ``.gv`` en
``arquitectura/salida/`` para que se pueda renderizar en otro entorno
(por ejemplo https://dreampuf.github.io/GraphvizOnline/).
"""

from __future__ import annotations

import re
import sys
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

try:
    from textx import metamodel_from_str
except ImportError:  # pragma: no cover - entorno sin textX instalado
    metamodel_from_str = None

try:
    from graphviz import Digraph
except ImportError:  # pragma: no cover - entorno sin graphviz instalado
    Digraph = None

BASE_DIR = Path(__file__).resolve().parent
SALIDA_DIR = BASE_DIR / "salida"

# En Windows la consola suele usar cp1252, que no soporta caracteres como
# "■" o tildes en todos los casos. Forzamos UTF-8 en stdout/stderr para que
# el script no falle con UnicodeEncodeError al imprimir el reporte.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


# ===========================================================================
# PARTE 1 — METAMODELO DE ARQUITECTURA (DSL textX)
# ===========================================================================
#
# Se reutiliza la misma gramática del notebook de referencia, extendida con
# dos tipos de componente y dos tipos de conector que no existían porque no
# los necesitaba el ejemplo original ("Urban Alert"), pero que sí hacen
# falta para describir con fidelidad la arquitectura de Healthchecks:
#   - component type "external_service": agrupa servicios de terceros
#     (Slack, Telegram, PagerDuty, SMTP saliente, etc.) alcanzados a través
#     de los "transports" de notificación.
#   - component type "batch_job": tareas periódicas de mantenimiento
#     (poda de datos) que no son daemons permanentes ni microservicios.
#   - connector type "smtp": ping entrante por correo electrónico.
#   - connector type "poll": sondeo de tablas de base de datos usado en vez
#     de un broker de mensajes (no hay RabbitMQ/Kafka en este proyecto).

GRAMMAR = r'''
Model:
    'architecture' ':' elements*=Element;

Element:
      Layer
    | Component
    | Connector;

Layer:
    'layer' name=ID label=STRING;

Component:
    'component' layer=[Layer|ID] type=ComponentType name=ID label=STRING;

Connector:
    'connector' type=ConnectorType source=[Component|ID] '->' target=[Component|ID] label=STRING;

ComponentType:
      'client'
    | 'gateway'
    | 'identity'
    | 'microservice'
    | 'reactive_service'
    | 'batch_job'
    | 'database'
    | 'cache'
    | 'object_storage'
    | 'external_service';

ConnectorType:
      'http'
    | 'rest'
    | 'smtp'
    | 'sql'
    | 'poll'
    | 'object_upload'
    | 'cache_access'
    | 'event_publish'
    | 'retry';

ID:
    /[a-zA-Z_][a-zA-Z0-9_]*/;
'''


# ============================================================
# Modelo DSL: arquitectura REAL de Healthchecks
# ============================================================
#
# Capas:
#   Clientes      -> actores externos que generan tráfico de entrada.
#   Borde         -> servidor de aplicación (uWSGI) que recibe y enruta.
#   Nucleo        -> apps Django del monolito (dominio y presentación).
#   Background    -> daemons y jobs que corren junto al proceso uWSGI.
#   Persistencia  -> almacenamiento de datos.
#   Integraciones -> servicios de terceros usados para notificar.

ARCHITECTURE_MODEL = r'''
architecture :

layer Clientes "Capa de Clientes (actores externos)"
layer Borde "Capa de Borde (servidor de aplicacion)"
layer Nucleo "Capa de Nucleo de Dominio (apps Django del monolito)"
layer Background "Capa de Procesos en Segundo Plano (daemons y cron)"
layer Persistencia "Capa de Persistencia"
layer Integraciones "Capa de Integraciones Externas (canales de notificacion)"

component Clientes client MonitoredSystems "Sistemas Monitoreados\n(cron jobs, servicios, baterias/IoT)\nEnvian pings via HTTP(S) o correo electronico"
component Clientes client Browser "Navegador Web\n(login, dashboard, gestion de proyectos y canales)"
component Clientes client ApiConsumers "Clientes de API\n(automatizaciones de terceros via API Key)"

component Borde gateway UWSGI "Servidor de aplicacion uWSGI\n[Pattern: Process Supervisor]\nTactics: 4 procesos worker, harakiri=10s, hook-pre-app (migrate), attach-daemon (supervisa sendalerts/sendreports/smtpd), activos estaticos inmutables + gzip (WhiteNoise/compressor)"

component Nucleo identity AccountsApp "hc.accounts\n(autenticacion, proyectos, equipos, WebAuthn, modo sudo)\nTactics: Argon2 password hashing, WebAuthn (llave de seguridad), autorizacion por rol en Project/Member"
component Nucleo microservice ApiApp "hc.api\n(dominio core: Check, Ping, Flip, Channel, Notification, TokenBucket)\nAPI REST v1/v2/v3\nTactics: rate limiting (TokenBucket), idempotencia por UUID de check"
component Nucleo microservice FrontApp "hc.front\n(panel web / dashboard de checks y badges)"
component Nucleo microservice PaymentsApp "hc.payments\n(suscripciones de facturacion)\n[Feature flag: USE_PAYMENTS]"
component Nucleo microservice LogsApp "hc.logs\n(visor de historial de pings y eventos)"
component Nucleo microservice IntegrationsApps "hc.integrations.*\n(28 canales de notificacion: slack, email, webhook, sms, telegram, pagerduty, etc.)\n[Pattern: Strategy / Plugin]\nTactics: interfaz comun Transport.notify(), despacho polimorfico via Channel.kind"

component Background reactive_service SendAlerts "sendalerts (daemon)\n[Pattern: Polling Consumer sobre cola basada en tabla]\nTactics: ThreadPoolExecutor para notificaciones concurrentes, deteccion de cambios de estado (Flip), timeout por Check.alert_after"
component Background reactive_service SendReports "sendreports --loop (daemon)\n(reportes semanales/mensuales y recordatorios de inactividad)"
component Background reactive_service Smtpd "smtpd (daemon opcional)\n[Pattern: Protocol Translator]\nTraduce ping por correo electronico a un ping HTTP interno"
component Background batch_job MaintenanceJobs "Tareas de mantenimiento (cron externo)\npruneobjects, prunepingsslow, prunetokenbucket, submitchallenge\nTactics: poda/retencion de datos expirados"

component Persistencia database PostgreSQL "PostgreSQL 16\n(modelo principal: Check, Ping, Flip, Channel, Project, Member, Profile, TokenBucket, Subscription)\nAlternativas soportadas: SQLite (desarrollo), MySQL/MariaDB"
component Persistencia cache Redis "Redis 7 (AOF)\n[declarado en docker-compose; REDIS_URL aun no esta cableado a settings.CACHES]"
component Persistencia object_storage ObjectStorage "Almacenamiento de objetos S3 / MinIO\n(cuerpos de ping que superan PING_BODY_LIMIT)\n[opcional: si no esta configurado, se guardan en PostgreSQL]"

component Integraciones external_service ChatOps "Canales ChatOps\n(Slack, Discord, Telegram, Matrix, Mattermost, Zulip, RocketChat, Google Chat, MS Teams, Gotify, ntfy, Apprise, Pushbullet, Pushover)"
component Integraciones external_service IncidentMgmt "Gestion de Incidentes\n(PagerDuty, Opsgenie, VictorOps, PagerTree, Spike)"
component Integraciones external_service VoiceSms "Voz y SMS\n(llamada telefonica, SMS, WhatsApp, Signal)"
component Integraciones external_service DevTools "Herramientas de Desarrollo\n(GitHub, Trello, Webhook generico, Shell local)"
component Integraciones external_service EmailRelay "Relay SMTP saliente\n(verificacion de cuenta, reportes, alertas por email)"

connector http MonitoredSystems -> UWSGI "HTTP(S) GET/POST/HEAD a /ping/<uuid>"
connector smtp MonitoredSystems -> Smtpd "Ping por correo a <uuid>@PING_EMAIL_DOMAIN"
connector http Browser -> UWSGI "HTTPS (sesion Django, CSRF)"
connector rest ApiConsumers -> UWSGI "REST API v1/v2/v3 (header X-Api-Key)"

connector http UWSGI -> AccountsApp "Enrutamiento Django (hc/urls.py)"
connector http UWSGI -> ApiApp "Enrutamiento Django (hc/urls.py)"
connector http UWSGI -> FrontApp "Enrutamiento Django (hc/urls.py)"
connector http UWSGI -> PaymentsApp "Enrutamiento Django (hc/urls.py)"
connector http UWSGI -> LogsApp "Enrutamiento Django (hc/urls.py)"

connector sql AccountsApp -> PostgreSQL "ORM Django"
connector sql ApiApp -> PostgreSQL "ORM Django"
connector sql FrontApp -> PostgreSQL "ORM Django (lectura de dashboard)"
connector sql PaymentsApp -> PostgreSQL "ORM Django"
connector sql LogsApp -> PostgreSQL "ORM Django"

connector object_upload ApiApp -> ObjectStorage "Subida de cuerpos de ping grandes (cliente minio-py)"
connector cache_access FrontApp -> Redis "Framework de cache de Django (pendiente de activar en settings.py)"

connector poll SendAlerts -> PostgreSQL "Sondeo de Check/Flip pendientes (sin broker de mensajeria)"
connector poll SendReports -> PostgreSQL "Sondeo de perfiles para reportes periodicos"
connector sql Smtpd -> PostgreSQL "Resolucion de Check por UUID + creacion de Ping"
connector sql MaintenanceJobs -> PostgreSQL "Borrado de registros expirados (TokenBucket, Ping, Notification)"
connector object_upload MaintenanceJobs -> ObjectStorage "Purga de cuerpos de ping huerfanos (pruneobjects)"

connector event_publish SendAlerts -> IntegrationsApps "Flip.select_channels() + Channel.notify()"

connector event_publish IntegrationsApps -> ChatOps "Transport.notify() (Strategy)"
connector event_publish IntegrationsApps -> IncidentMgmt "Transport.notify() (Strategy)"
connector event_publish IntegrationsApps -> VoiceSms "Transport.notify() (Strategy)"
connector event_publish IntegrationsApps -> DevTools "Transport.notify() (Strategy)"
connector event_publish IntegrationsApps -> EmailRelay "Transport.notify() / verificacion de cuenta"
connector retry IntegrationsApps -> ChatOps "Reintento ante fallo HTTP (metrica statsd: hc.notifications.<kind>.fail)"
'''


# Tipos de componente que representan infraestructura / preocupaciones
# transversales (lo que el laboratorio llama "componentes arquitectónicos"):
ARCHITECTURAL_COMPONENT_TYPES = {
    "gateway",
    "database",
    "cache",
    "object_storage",
    "external_service",
    "batch_job",
}

# Tipos de componente que implementan la lógica de negocio / dominio
# (lo que el laboratorio llama "componentes de servicio"):
SERVICE_COMPONENT_TYPES = {
    "identity",
    "microservice",
    "reactive_service",
}

# Tipo que representa actores externos (no se clasifica como
# "arquitectónico" ni "de servicio": está fuera del sistema).
ACTOR_COMPONENT_TYPES = {"client"}


LAYER_COLORS = {
    "Clientes": "#D6ECFF",
    "Borde": "#FFF0CC",
    "Nucleo": "#DDF5E5",
    "Background": "#FFE1E1",
    "Persistencia": "#E5E8EF",
    "Integraciones": "#F3E5F5",
}

COMPONENT_SHAPES = {
    "client": "box",
    "gateway": "box",
    "identity": "box",
    "microservice": "box",
    "reactive_service": "box",
    "batch_job": "note",
    "database": "cylinder",
    "cache": "cylinder",
    "object_storage": "cylinder",
    "external_service": "box3d",
}

CONNECTOR_STYLES = {
    "http": ("#34495E", "solid", "1.5"),
    "rest": ("#34495E", "solid", "1.5"),
    "smtp": ("#34495E", "dashed", "1.5"),
    "sql": ("#3498DB", "solid", "1.6"),
    "poll": ("#8E44AD", "dotted", "1.6"),
    "object_upload": ("#3498DB", "solid", "1.6"),
    "cache_access": ("#9B59B6", "dotted", "1.6"),
    "event_publish": ("#E74C3C", "bold", "2.0"),
    "retry": ("#E67E22", "dashed", "1.6"),
}


def construir_modelo_arquitectura():
    """Parsea ``ARCHITECTURE_MODEL`` con la gramática textX y lo retorna.

    Retorna ``None`` si textX no está instalado en el entorno actual.
    """
    if metamodel_from_str is None:
        print(
            "AVISO: textX no está instalado. Ejecuta 'pip install textX' "
            "para construir y graficar el modelo de arquitectura.",
            file=sys.stderr,
        )
        return None

    mm = metamodel_from_str(GRAMMAR)
    return mm.model_from_str(ARCHITECTURE_MODEL)


def analizar_arquitectura(modelo) -> None:
    """Imprime un resumen de capas, componentes y conectores del modelo."""
    layers = [e for e in modelo.elements if e.__class__.__name__ == "Layer"]
    components = [e for e in modelo.elements if e.__class__.__name__ == "Component"]
    connectors = [e for e in modelo.elements if e.__class__.__name__ == "Connector"]

    print("=" * 70)
    print("ANÁLISIS DE LA ARQUITECTURA — Healthchecks")
    print("=" * 70)
    print(f"Capas:       {len(layers)}")
    print(f"Componentes: {len(components)}")
    print(f"Conectores:  {len(connectors)}")

    for layer in layers:
        comps = [c for c in components if c.layer.name == layer.name]
        print(f"\n■ {layer.name} — {layer.label}")
        for c in comps:
            primera_linea = re.split(r"\\n|\n", c.label)[0]
            print(f"   [{c.type}] {c.name}: {primera_linea}")

    print("\nConectores:")
    for con in connectors:
        print(f"   ({con.type}) {con.source.name} -> {con.target.name}: {con.label}")


def clasificar_componentes(modelo) -> dict:
    """Separa los componentes del modelo en arquitectónicos, de servicio y actores.

    Esta función responde directamente a los requisitos del laboratorio:
    "indicar los componentes arquitectónicos" e "indicar los componentes de
    servicios".
    """
    components = [e for e in modelo.elements if e.__class__.__name__ == "Component"]

    arquitectonicos = [c for c in components if str(c.type) in ARCHITECTURAL_COMPONENT_TYPES]
    de_servicio = [c for c in components if str(c.type) in SERVICE_COMPONENT_TYPES]
    actores = [c for c in components if str(c.type) in ACTOR_COMPONENT_TYPES]

    print("\n" + "=" * 70)
    print("COMPONENTES ARQUITECTÓNICOS (infraestructura / preocupaciones transversales)")
    print("=" * 70)
    for c in arquitectonicos:
        primera_linea = re.split(r"\\n|\n", c.label)[0]
        print(f"   [{c.type}] {c.name} ({c.layer.name}): {primera_linea}")

    print("\n" + "=" * 70)
    print("COMPONENTES DE SERVICIO (lógica de negocio / dominio)")
    print("=" * 70)
    for c in de_servicio:
        primera_linea = re.split(r"\\n|\n", c.label)[0]
        print(f"   [{c.type}] {c.name} ({c.layer.name}): {primera_linea}")

    print("\n" + "=" * 70)
    print("ACTORES EXTERNOS (fuera del sistema, no se clasifican como arriba)")
    print("=" * 70)
    for c in actores:
        primera_linea = re.split(r"\\n|\n", c.label)[0]
        print(f"   [{c.type}] {c.name} ({c.layer.name}): {primera_linea}")

    return {
        "arquitectonicos": arquitectonicos,
        "de_servicio": de_servicio,
        "actores": actores,
    }


def graficar_arquitectura(modelo, nombre_archivo: str = "arquitectura_healthchecks") -> Optional[Path]:
    """Genera el diagrama de arquitectura con Graphviz.

    Si el binario ``dot`` no está disponible, igual se escribe el archivo
    fuente ``.gv`` para poder renderizarlo en otro entorno.
    """
    if Digraph is None:
        print(
            "AVISO: el paquete 'graphviz' no está instalado. "
            "Ejecuta 'pip install graphviz' para generar el diagrama.",
            file=sys.stderr,
        )
        return None

    layers = [e for e in modelo.elements if e.__class__.__name__ == "Layer"]
    components = [e for e in modelo.elements if e.__class__.__name__ == "Component"]
    connectors = [e for e in modelo.elements if e.__class__.__name__ == "Connector"]

    dot = Digraph("arquitectura_healthchecks", format="png")
    dot.attr(rankdir="LR", fontsize="11", fontname="Helvetica")
    dot.attr("node", fontname="Helvetica", fontsize="10")
    dot.attr("edge", fontname="Helvetica", fontsize="8")

    for layer in layers:
        with dot.subgraph(name=f"cluster_{layer.name}") as cluster:
            layer_color = LAYER_COLORS.get(layer.name, "#FFFFFF")
            cluster.attr(
                label=layer.label,
                style="filled,rounded",
                color="#BDC3C7",
                fillcolor=layer_color,
                fontsize="12",
            )
            for c in components:
                if c.layer.name != layer.name:
                    continue
                shape = COMPONENT_SHAPES.get(str(c.type), "box")
                label = c.label.replace("\\n", "\n")
                cluster.node(c.name, label=f"{label}", shape=shape, style="filled", fillcolor="white")

    for con in connectors:
        color, style, penwidth = CONNECTOR_STYLES.get(str(con.type), ("black", "solid", "1.0"))
        dot.edge(
            con.source.name,
            con.target.name,
            label=f"{con.type}\n{con.label}",
            color=color,
            style=style,
            penwidth=penwidth,
        )

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    destino = SALIDA_DIR / nombre_archivo
    gv_path = destino.with_suffix(".gv")
    try:
        archivo_png = dot.render(str(destino), cleanup=True)
        print(f"\nDiagrama de arquitectura generado en: {archivo_png}")
        return Path(archivo_png)
    except Exception as exc:  # binario 'dot' ausente u otro error de render
        # dot.render() ya pudo haber escrito el archivo fuente sin extensión
        # antes de fallar; lo removemos para no dejar un duplicado del .gv.
        archivo_sin_extension = SALIDA_DIR / nombre_archivo
        if archivo_sin_extension.exists() and archivo_sin_extension != gv_path:
            archivo_sin_extension.unlink()
        gv_path.write_text(dot.source, encoding="utf-8")
        print(
            f"\nAVISO: no se pudo renderizar el PNG ({exc}). "
            f"Se escribió el código fuente de Graphviz en: {gv_path}\n"
            "Puedes renderizarlo manualmente con 'dot -Tpng' o pegarlo en "
            "https://dreampuf.github.io/GraphvizOnline/",
            file=sys.stderr,
        )
        return gv_path


# ===========================================================================
# PARTE 2 — METAMODELO DE CALIDAD: Pattern / Tactic / QualityAttribute / ...
# ===========================================================================
#
# Mismo esquema de dataclasses que en references/metamodelo.ipynb, poblado
# con tácticas y patrones REALES identificados en el código de Healthchecks
# (no son ilustrativos como en el notebook de referencia).


def elemento(cls):
    """Dataclass con identidad por referencia (eq=False) y repr compacto."""
    return dataclass(eq=False, repr=False)(cls)


@elemento
class Element:
    name: str
    description: str = ""

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


@elemento
class ComponentType(Element):
    pass


@elemento
class ConnectorType(Element):
    pass


@elemento
class Component(Element):
    component_type: Optional[ComponentType] = None


@elemento
class Connector(Element):
    connector_type: Optional[ConnectorType] = None
    source: Optional[Component] = None
    target: Optional[Component] = None


@elemento
class QualityAttribute(Element):
    category: str = ""
    sub_attributes: List["QualityAttribute"] = field(default_factory=list)


@elemento
class QualityScenario(Element):
    source: str = ""
    stimulus: str = ""
    environment: str = ""
    artifact: str = ""
    response: str = ""
    response_measure: str = ""
    quality_attribute: Optional[QualityAttribute] = None


@elemento
class Pattern(Element):
    intent: str = ""
    context: str = ""
    problem: str = ""
    solution: str = ""
    consequences: List[str] = field(default_factory=list)
    forces: List[str] = field(default_factory=list)
    applicability: str = ""
    addresses: List[QualityAttribute] = field(default_factory=list)
    composed_of: List["Tactic"] = field(default_factory=list)
    uses: List["Pattern"] = field(default_factory=list)
    realized_by: List[Union[Component, Connector]] = field(default_factory=list)
    constrains: List[Component] = field(default_factory=list)


@elemento
class Tactic(Element):
    rationale: str = ""
    mechanism: str = ""
    preconditions: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    addresses: List[QualityAttribute] = field(default_factory=list)
    applies_to: List[Union[Component, Connector]] = field(default_factory=list)
    refines: List[Pattern] = field(default_factory=list)
    conflicts_with: List["Tactic"] = field(default_factory=list)
    complements: List["Tactic"] = field(default_factory=list)


Relacion = namedtuple("Relacion", "origen nombre atributo destinos")

RELATIONS = [
    Relacion(Tactic, "addresses", "addresses", (QualityAttribute,)),
    Relacion(Tactic, "appliesTo", "applies_to", (Component, Connector)),
    Relacion(Tactic, "refines", "refines", (Pattern,)),
    Relacion(Tactic, "conflictsWith", "conflicts_with", (Tactic,)),
    Relacion(Tactic, "complements", "complements", (Tactic,)),
    Relacion(Pattern, "addresses", "addresses", (QualityAttribute,)),
    Relacion(Pattern, "composedOf", "composed_of", (Tactic,)),
    Relacion(Pattern, "uses", "uses", (Pattern,)),
    Relacion(Pattern, "realizedBy", "realized_by", (Component, Connector)),
    Relacion(Pattern, "constrains", "constrains", (Component,)),
]


def validar_modelo(elementos) -> List[str]:
    """Comprueba que cada relación apunte al tipo permitido y que ninguna
    táctica esté a la vez en conflicto y en complemento con otra."""
    errores = []
    for el in elementos:
        for r in RELATIONS:
            if not isinstance(el, r.origen):
                continue
            for destino in getattr(el, r.atributo):
                if not isinstance(destino, r.destinos):
                    esperado = " | ".join(d.__name__ for d in r.destinos)
                    errores.append(
                        f"{el!r} ──{r.nombre}──> {destino!r}: "
                        f"se esperaba {esperado}, se recibió {type(destino).__name__}"
                    )
        if isinstance(el, Tactic):
            for otra in el.conflicts_with:
                if otra in el.complements:
                    errores.append(
                        f"{el!r} y {otra!r} están a la vez en conflictsWith y complements"
                    )
    return errores


def importar_arquitectura(modelo):
    """Convierte el modelo textX (Layer/Component/Connector) en instancias
    del metamodelo de calidad: Component, Connector, ComponentType y
    ConnectorType. Permite enlazar Pattern/Tactic con los componentes reales
    de la arquitectura de Healthchecks."""
    tipos_componente, tipos_conector = {}, {}
    componentes, conectores = {}, {}

    for e in modelo.elements:
        if e.__class__.__name__ != "Component":
            continue
        tipo = str(e.type)
        tipos_componente.setdefault(tipo, ComponentType(name=tipo))
        descripcion = re.split(r"\\n|\n", e.label)[0]
        componentes[e.name] = Component(
            name=e.name,
            description=descripcion,
            component_type=tipos_componente[tipo],
        )

    for e in modelo.elements:
        if e.__class__.__name__ != "Connector":
            continue
        tipo = str(e.type)
        tipos_conector.setdefault(tipo, ConnectorType(name=tipo))
        origen, destino = componentes[e.source.name], componentes[e.target.name]
        conectores[(origen.name, destino.name)] = Connector(
            name=f"{origen.name}->{destino.name}",
            description=e.label,
            connector_type=tipos_conector[tipo],
            source=origen,
            target=destino,
        )

    return componentes, conectores, list(tipos_componente.values()), list(tipos_conector.values())


def construir_metamodelo_calidad(componentes: dict):
    """Puebla QualityAttribute/QualityScenario/Tactic/Pattern con hallazgos
    reales del código de Healthchecks, enlazados a los componentes de la
    arquitectura real (parámetro ``componentes``, resultado de
    ``importar_arquitectura``)."""

    C = componentes  # atajo

    # --- Atributos de calidad -------------------------------------------------
    authentication = QualityAttribute(
        "authentication", "Verificar la identidad de usuarios y clientes de API", category="security"
    )
    authorization = QualityAttribute(
        "authorization", "Restringir acciones según el rol dentro de un proyecto", category="security"
    )
    security = QualityAttribute(
        "security", "Proteger cuentas, proyectos y canales de notificación", category="security",
        sub_attributes=[authentication, authorization],
    )
    availability = QualityAttribute(
        "availability", "Detectar y notificar caídas de los sistemas monitoreados a tiempo", category="reliability"
    )
    performance = QualityAttribute(
        "performance", "Responder rápido a los pings entrantes y despachar notificaciones sin bloquear", category="performance"
    )
    scalability = QualityAttribute(
        "scalability", "Soportar crecimiento en número de checks, pings y canales sin degradar el servicio", category="performance"
    )
    extensibility = QualityAttribute(
        "extensibility", "Agregar nuevos canales de notificación sin modificar el núcleo", category="maintainability"
    )
    observability = QualityAttribute(
        "observability", "Medir el éxito/fallo de cada notificación y cada ciclo de polling", category="maintainability"
    )

    # --- Escenarios de calidad (derivados del comportamiento real) -----------
    escenarios = [
        QualityScenario(
            "ping_timeout_detection",
            source="sendalerts (daemon)",
            stimulus="Un sistema monitoreado deja de enviar pings y supera su periodo de gracia",
            environment="Operación normal",
            artifact="Check / Flip (hc.api)",
            response="sendalerts detecta el Check vencido, crea un Flip y notifica a los canales del proyecto",
            response_measure="Detectado y notificado dentro del ciclo de polling (segundos, configurable)",
            quality_attribute=availability,
        ),
        QualityScenario(
            "brute_force_login",
            source="Atacante externo",
            stimulus="Múltiples intentos de login o de uso de API key inválidos en poco tiempo",
            environment="Producción, tráfico malicioso",
            artifact="hc.accounts / hc.api + TokenBucket",
            response="El sistema limita la tasa de intentos mediante TokenBucket antes de agotar recursos",
            response_measure="Los intentos excedentes son rechazados sin afectar a usuarios legítimos",
            quality_attribute=authentication,
        ),
        QualityScenario(
            "large_ping_body",
            source="Sistema monitoreado",
            stimulus="El cuerpo del ping supera PING_BODY_LIMIT",
            environment="Operación normal con object storage configurado",
            artifact="hc.api (Ping) + Object Storage (S3/MinIO)",
            response="El cuerpo se sube a almacenamiento de objetos en lugar de la base de datos relacional",
            response_measure="La respuesta HTTP al cliente que envía el ping no se bloquea ni crece el tamaño de la BD",
            quality_attribute=performance,
        ),
    ]

    # --- Tácticas (mecanismos concretos encontrados en el código) ------------
    table_based_polling = Tactic(
        "table_based_polling",
        "sendalerts sondea periódicamente la tabla Check/Flip en vez de usar un broker de mensajes",
        rationale="No hay RabbitMQ/Kafka en el stack; Postgres actúa como cola implícita",
        mechanism="Query periódica + actualización atómica de estado (Flip)",
        addresses=[availability],
        applies_to=[C["SendAlerts"]],
    )
    thread_pool_dispatch = Tactic(
        "thread_pool_dispatch",
        "sendalerts despacha notificaciones en paralelo usando ThreadPoolExecutor",
        rationale="Evita que un canal lento (ej. SMTP con timeout) bloquee a los demás",
        mechanism="concurrent.futures.ThreadPoolExecutor (--num-workers configurable)",
        addresses=[performance],
        applies_to=[C["SendAlerts"]],
    )
    token_bucket_rate_limit = Tactic(
        "token_bucket_rate_limit",
        "Modelo TokenBucket y comando prunetokenbucket para limitar tasa de operaciones sensibles",
        rationale="Mitigar fuerza bruta y abuso de endpoints sin estado persistente complejo",
        mechanism="Token bucket por clave + purga de entradas con más de 1 día (prunetokenbucket)",
        addresses=[authentication],
        applies_to=[C["AccountsApp"], C["ApiApp"], C["MaintenanceJobs"]],
    )
    argon2_hashing = Tactic(
        "argon2_hashing",
        "Argon2 como primer hasher de contraseñas en PASSWORD_HASHERS",
        rationale="Argon2 es resistente a ataques por GPU/ASIC, recomendado por OWASP",
        mechanism="django.contrib.auth.hashers.Argon2PasswordHasher",
        addresses=[authentication],
        applies_to=[C["AccountsApp"]],
    )
    webauthn_mfa = Tactic(
        "webauthn_mfa",
        "Soporte de llaves de seguridad (WebAuthn) como segundo factor",
        rationale="Reduce el riesgo de robo de cuenta frente a solo usuario/contraseña",
        mechanism="hc.lib.webauthn + modelo Credential",
        addresses=[authentication],
        applies_to=[C["AccountsApp"]],
    )
    object_storage_offload = Tactic(
        "object_storage_offload",
        "Los cuerpos de ping grandes se delegan a almacenamiento de objetos S3/MinIO",
        rationale="Evita inflar la base de datos relacional con payloads grandes",
        mechanism="hc.lib.s3 (cliente Minio) + PING_BODY_LIMIT",
        addresses=[performance, scalability],
        applies_to=[C["ApiApp"]],
    )
    strategy_transport_dispatch = Tactic(
        "strategy_transport_dispatch",
        "Cada canal de notificación implementa una interfaz Transport común",
        rationale="Permite agregar canales nuevos sin tocar el núcleo de alertas",
        mechanism="diccionario TRANSPORTS (hc.api.models) + Channel.notify()",
        addresses=[extensibility],
        applies_to=[C["IntegrationsApps"]],
    )
    statsd_monitoring = Tactic(
        "statsd_monitoring",
        "Métricas de éxito/fallo por canal enviadas a StatsD",
        rationale="Permite observar la salud del subsistema de notificaciones en producción",
        mechanism="hc.lib.statsd -> hc.notifications.<kind>.success|fail",
        addresses=[observability],
        applies_to=[C["SendAlerts"], C["IntegrationsApps"]],
    )
    retention_pruning = Tactic(
        "retention_pruning",
        "Comandos de poda periódica para datos expirados o huérfanos",
        rationale="Mantener el tamaño de la base de datos y el almacenamiento de objetos acotado",
        mechanism="pruneobjects, prunepingsslow, prunetokenbucket",
        addresses=[scalability],
        applies_to=[C["MaintenanceJobs"]],
    )

    thread_pool_dispatch.complements.append(statsd_monitoring)
    statsd_monitoring.complements.append(thread_pool_dispatch)

    tacticas = [
        table_based_polling,
        thread_pool_dispatch,
        token_bucket_rate_limit,
        argon2_hashing,
        webauthn_mfa,
        object_storage_offload,
        strategy_transport_dispatch,
        statsd_monitoring,
        retention_pruning,
    ]

    # --- Patrones (combinan tácticas y se realizan en componentes reales) ---
    pattern_table_queue = Pattern(
        "table_based_queue",
        intent="Desacoplar la detección de caídas del envío de notificaciones sin un broker dedicado",
        context="Monolito con una sola base de datos relacional y sin infraestructura de mensajería",
        problem="¿Cómo implementar un flujo asíncrono de eventos (caída -> notificación) de forma simple?",
        solution="Usar la tabla Flip como cola: sendalerts sondea, marca como procesado y despacha en paralelo",
        addresses=[availability, performance],
        composed_of=[table_based_polling, thread_pool_dispatch],
        realized_by=[C["SendAlerts"], C["PostgreSQL"]],
    )
    pattern_process_supervisor = Pattern(
        "process_supervisor",
        intent="Mantener vivos los procesos en segundo plano junto al servidor web sin orquestación externa",
        context="Despliegue de un solo contenedor (docker-compose) sin Celery/K8s CronJob",
        problem="¿Cómo ejecutar daemons de larga duración (alertas, reportes, SMTP) sin procesos separados?",
        solution="uWSGI 'attach-daemon' supervisa y reinicia sendalerts, sendreports y smtpd",
        addresses=[availability],
        realized_by=[C["UWSGI"], C["SendAlerts"], C["SendReports"], C["Smtpd"]],
    )
    pattern_strategy_channels = Pattern(
        "strategy_notification_channels",
        intent="Soportar decenas de canales de notificación heterogéneos sin acoplar el núcleo a cada API externa",
        context="28 integraciones con proveedores externos distintos (chat, email, SMS, incidentes, webhooks)",
        problem="¿Cómo agregar/mantener canales de notificación sin modificar sendalerts ni los modelos core?",
        solution="Cada integración implementa Transport.notify(); Channel.kind selecciona la implementación en tiempo de ejecución",
        addresses=[extensibility, observability],
        composed_of=[strategy_transport_dispatch, statsd_monitoring],
        realized_by=[C["IntegrationsApps"]],
        constrains=[C["IntegrationsApps"]],
    )
    pattern_tiered_storage = Pattern(
        "tiered_overflow_storage",
        intent="Mantener la base de datos relacional liviana ante payloads de ping variables",
        context="Pings pueden traer cuerpos pequeños (texto) o grandes (logs/JSON extensos)",
        problem="¿Dónde guardar cuerpos de ping sin penalizar el tamaño/backup de la base de datos principal?",
        solution="Los cuerpos por debajo de PING_BODY_LIMIT van a PostgreSQL; por encima, a S3/MinIO",
        addresses=[performance, scalability],
        composed_of=[object_storage_offload],
        realized_by=[C["ApiApp"], C["ObjectStorage"], C["PostgreSQL"]],
        constrains=[C["ApiApp"]],
    )

    patrones = [
        pattern_table_queue,
        pattern_process_supervisor,
        pattern_strategy_channels,
        pattern_tiered_storage,
    ]

    return {
        "atributos": [security, authentication, authorization, availability, performance, scalability, extensibility, observability],
        "raices": [security, availability, performance, scalability, extensibility, observability],
        "escenarios": escenarios,
        "tacticas": tacticas,
        "patrones": patrones,
    }


def alcance(qa: QualityAttribute) -> List[QualityAttribute]:
    """El atributo de calidad y todos sus sub-atributos."""
    resultado = [qa]
    for sub in qa.sub_attributes:
        resultado += alcance(sub)
    return resultado


def _nombres(elementos) -> str:
    return ", ".join(e.name for e in elementos)


def reporte_trazabilidad(raices: List[QualityAttribute], escenarios, tacticas, patrones) -> None:
    """Recorre QualityAttribute -> Pattern -> Tactic -> Component/Connector
    y señala explícitamente los atributos sin patrón o táctica asociada."""
    print("\n" + "=" * 70)
    print("TRAZABILIDAD: QualityAttribute → Pattern → Tactic → Component/Connector")
    print("=" * 70)

    for qa in raices:
        ambito = alcance(qa)
        sub = f" (sub: {_nombres(qa.sub_attributes)})" if qa.sub_attributes else ""
        print(f"\n■ {qa.name} [{qa.category}]{sub}")

        for esc in escenarios:
            if esc.quality_attribute in ambito:
                print(f"   Scenario : {esc.name} → {esc.response_measure}")

        patrones_qa = [p for p in patrones if any(a in ambito for a in p.addresses)]
        tacticas_qa = [t for t in tacticas if any(a in ambito for a in t.addresses)]

        for p in patrones_qa:
            print(f"   Pattern  : {p.name}")
            for etiqueta, lista in (("realizedBy", p.realized_by), ("constrains", p.constrains), ("composedOf", p.composed_of)):
                if lista:
                    print(f"       {etiqueta:11}: {_nombres(lista)}")
        if not patrones_qa:
            print("   Pattern  : — (sin patrones asociados; oportunidad de mejora)")

        for t in tacticas_qa:
            print(f"   Tactic   : {t.name}")
            for etiqueta, lista in (("appliesTo", t.applies_to), ("complements", t.complements), ("conflictsWith", t.conflicts_with)):
                if lista:
                    print(f"       {etiqueta:11}: {_nombres(lista)}")
        if not tacticas_qa:
            print("   Tactic   : — (sin tácticas asociadas; oportunidad de mejora)")


# ===========================================================================
# PUNTO DE ENTRADA
# ===========================================================================

def main() -> int:
    modelo = construir_modelo_arquitectura()
    if modelo is None:
        return 1

    analizar_arquitectura(modelo)
    clasificar_componentes(modelo)
    graficar_arquitectura(modelo)

    componentes, _conectores, _tipos_c, _tipos_k = importar_arquitectura(modelo)
    calidad = construir_metamodelo_calidad(componentes)

    elementos_a_validar = calidad["atributos"] + calidad["escenarios"] + calidad["tacticas"] + calidad["patrones"]
    errores = validar_modelo(elementos_a_validar)
    print("\n" + "=" * 70)
    print("VALIDACIÓN DEL METAMODELO DE CALIDAD")
    print("=" * 70)
    if errores:
        for e in errores:
            print(f"   ERROR: {e}")
    else:
        print("   Sin errores: todas las relaciones apuntan a tipos permitidos.")

    reporte_trazabilidad(calidad["raices"], calidad["escenarios"], calidad["tacticas"], calidad["patrones"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
