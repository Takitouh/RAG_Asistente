"""Detector de intenciones sociales y saludos para el asistente.

Permite atender interacciones de cortesía (saludos, despedidas y agradecimientos)
de forma instantánea y cordial, orientando al usuario sobre las consultas
normativas que puede realizar, sin disparar búsquedas vectoriales innecesarias
ni incurrir en abstenciones absurdas («fuera de alcance»).
"""
from __future__ import annotations

import re


# Palabras clave normativas que indican que la consulta contiene una pregunta real,
# incluso si comienza con un saludo
_NORMATIVE_KEYWORDS = {
    "modalidad", "modalidades", "articulo", "artículo", "plazo", "plazos",
    "prorroga", "prórroga", "prorrogas", "prórrogas", "informe", "final",
    "propuesta", "anteproyecto", "grado", "comite", "comité", "evaluador",
    "evaluadores", "director", "directores", "reprobacion", "reprobación",
    "calificacion", "calificación", "nota", "notas", "requisito", "requisitos",
    "inscripcion", "inscripción", "seminario", "monografia", "monografía",
    "practica", "práctica", "emprendimiento", "investigacion", "investigación",
    "desarrollo", "tecnologico", "tecnológico", "cancelacion", "cancelación",
    "acuerdo", "reglamento", "capitulo", "capítulo", "paragrafo", "parágrafo",
    "inciso", "derecho", "pecuniario", "pago", "beca", "sustentacion",
    "sustentación", "fecha", "jurado", "hamburguesa", "precio", "costo",
}

# Patrones de saludos simples y sociales
_GREETING_PATTERNS = [
    r"^(?:¡|\s)*hola(?:\s+a\s+todos)?(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*buen(?:os|as)?\s+(?:d[ií]as|tardes|noches)(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*hola[,\s]+(?:buen(?:os|as)?\s+)?(?:d[ií]as|tardes|noches)(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*hola[,\s]+(?:c[oó]mo\s+est[aá]s|qu[eé]\s+tal)(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*qu[eé]\s+tal(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*saludos(?:\s+cordiales)?(?:!|\.|\?|\s)*$",
]

_THANKS_PATTERNS = [
    r"^(?:¡|\s)*gracias(?:\s+muchas)?(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*muchas\s+gracias(?:\s+por\s+.*)?(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*mil\s+gracias(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*gracias\s+por\s+(?:la\s+)?(?:ayuda|informaci[oó]n|tu\s+ayuda|su\s+ayuda)(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*te\s+lo\s+agradezco(?:!|\.|\?|\s)*$",
]

_FAREWELL_PATTERNS = [
    r"^(?:¡|\s)*chao(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*adi[oó]s(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*hasta\s+(?:luego|pronto|la\s+pr[oó]xima)(?:!|\.|\?|\s)*$",
    r"^(?:¡|\s)*nos\s+vemos(?:!|\.|\?|\s)*$",
]


def is_greeting_or_social(query: str, active_doc_name: str | None = None) -> tuple[bool, str | None, str | None]:
    """Evalúa si la consulta es un saludo o interacción social simple.

    Retorna:
        (is_social, response_text, social_type)
        donde social_type es "greeting", "thanks", "farewell" o None.
    """
    clean = query.strip()
    lower = clean.lower()

    # Si la consulta contiene palabras clave normativas sustantivas, no es un saludo simple
    words = set(re.findall(r"\w+", lower))
    has_normative_intent = any(w in _NORMATIVE_KEYWORDS for w in words)
    if has_normative_intent:
        return False, None, None

    # 1. Saludos
    for pat in _GREETING_PATTERNS:
        if re.match(pat, lower):
            doc_context = f" (consultando: {active_doc_name})" if active_doc_name else ""
            msg = (
                f"¡Hola! Soy el asistente orientativo del Reglamento de Trabajo de Grado de las "
                f"Unidades Tecnológicas de Santander (UTS){doc_context}.\n\n"
                f"Puedo orientarte sobre:\n"
                f"• Modalidades de trabajo de grado disponibles.\n"
                f"• Requisitos y plazos para la presentación de propuestas e informes finales.\n"
                f"• Procedimientos y condiciones para solicitar prórrogas.\n"
                f"• Funciones de directores, evaluadores y del Comité de Trabajo de Grado.\n"
                f"• Calificaciones, causales de reprobación y cancelaciones.\n\n"
                f"¿En qué puedo orientarte hoy?"
            )
            return True, msg, "greeting"

    # 2. Agradecimientos
    for pat in _THANKS_PATTERNS:
        if re.match(pat, lower):
            msg = (
                "¡Con mucho gusto! Quedo a tu disposición si necesitas consultar alguna otra disposición "
                "del Reglamento de Trabajo de Grado de las UTS."
            )
            return True, msg, "thanks"

    # 3. Despedidas
    for pat in _FAREWELL_PATTERNS:
        if re.match(pat, lower):
            msg = (
                "¡Hasta pronto! Recuerda consultar a la coordinación de tu programa o al Comité de Trabajo de Grado "
                "para cualquier trámite oficial."
            )
            return True, msg, "farewell"

    return False, None, None
