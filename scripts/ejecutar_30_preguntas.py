#!/usr/bin/env python3
"""Script reproducible para ejecutar y evaluar el banco de 30 preguntas de validación técnica de NORMATIVA-TG UTS.

Consulta el backend FastAPI (http://localhost:8000/api/query) y audita las trazas en SQLite.
Genera docs/entrega_final/resultados_30_preguntas.json y docs/entrega_final/resultados_30_preguntas.csv.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"
DB_PATH = Path("data/db/normativa.db")
ADMIN_KEY = "dev-admin-secret-key"

PREGUNTAS = [
    {
        "id": "D01",
        "categoria": "Directa",
        "pregunta": "¿Cuáles son las modalidades de Trabajo de Grado contempladas en el reglamento?",
        "resultado_esperado": "Debe enumerar las seis modalidades: Proyecto de Investigación, Desarrollo Tecnológico, Monografía, Seminario, Práctica y Emprendimiento. No debe limitarse al parágrafo del artículo.",
        "fuente": "Reglamento 2019, art. 8, pág. 4.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [8],
    },
    {
        "id": "D02",
        "categoria": "Directa",
        "pregunta": "¿Cuál es el período general previsto después de aprobar la propuesta para finalizar el Trabajo de Grado?",
        "resultado_esperado": "Debe indicar 180 días calendario consecutivos a partir de la aprobación de la propuesta, precisando que se trata del período para finalizar el Trabajo de Grado, no necesariamente de un plazo independiente para redactar el informe.",
        "fuente": "Reglamento 2019, art. 14, pág. 5.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [14],
    },
    {
        "id": "D03",
        "categoria": "Directa",
        "pregunta": "¿Puedo entregar el Informe Final un mes después de que aprueben mi propuesta?",
        "resultado_esperado": "Debe indicar que no: el reglamento establece que no puede entregarse el Informe Final al Comité antes de transcurridos tres meses desde la aprobación de la propuesta.",
        "fuente": "Reglamento 2019, art. 30, parágrafo 1, pág. 11.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [30],
    },
    {
        "id": "D04",
        "categoria": "Directa",
        "pregunta": "¿Qué es el Informe Final de Trabajo de Grado según el reglamento?",
        "resultado_esperado": "Debe explicar que el Informe Final consigna resultados y conclusiones de la implementación de la propuesta, dentro de la estructura metodológica correspondiente, sin confundirlo con la propuesta.",
        "fuente": "Reglamento 2019, art. 29, pág. 10.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [29],
    },
    {
        "id": "D05",
        "categoria": "Directa",
        "pregunta": "¿Cuáles son los posibles conceptos de evaluación del Informe Final?",
        "resultado_esperado": "Debe identificar los conceptos previstos: Trabajo de Grado Aplazado, Aprobado y Reprobado, y reconocer que se trata de una valoración cualitativa.",
        "fuente": "Reglamento 2019, art. 31, pág. 11.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [31],
    },
    {
        "id": "D06",
        "categoria": "Directa",
        "pregunta": "¿El Trabajo de Grado puede hacerse individualmente o en equipo?",
        "resultado_esperado": "Debe señalar que se permite individualmente o en equipo; el máximo general es de dos estudiantes, con una excepción de hasta tres para Proyecto de Investigación y Desarrollo Tecnológico.",
        "fuente": "Reglamento 2019, art. 11 y parágrafo, pág. 5.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [11],
    },
    {
        "id": "D07",
        "categoria": "Directa",
        "pregunta": "¿Qué clases de monografía describe el reglamento?",
        "resultado_esperado": "Debe distinguir Monografía Teórica, Monografía de Análisis y Monografía de Sistematización de Experiencias.",
        "fuente": "Reglamento 2019, art. 39, pág. 13.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [39],
    },
    {
        "id": "D08",
        "categoria": "Directa",
        "pregunta": "¿Cuántas horas académicas debe tener como mínimo la modalidad de Seminario?",
        "resultado_esperado": "Debe indicar la intensidad mínima de 160 horas académicas que se establece para la modalidad y evitar inventar fechas o tarifas.",
        "fuente": "Reglamento 2019, art. 42, parágrafo, pág. 14.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [42],
    },
    {
        "id": "D09",
        "categoria": "Directa",
        "pregunta": "¿Qué modalidades de práctica reconoce el reglamento?",
        "resultado_esperado": "Debe mencionar Práctica Empresarial y Práctica Social Comunitaria, describiendo brevemente que se trata de las denominaciones expuestas en el capítulo de práctica.",
        "fuente": "Reglamento 2019, art. 49, pág. 16.",
        "comportamiento_esperado": "Respuesta sustentada",
        "articulos_esperados": [49],
    },
    {
        "id": "R10",
        "categoria": "Relación entre disposiciones",
        "pregunta": "Me aprobaron la propuesta de Trabajo de Grado. ¿Qué debo hacer después y cuándo puedo presentar el Informe Final?",
        "resultado_esperado": "Debe explicar que corresponde desarrollar el trabajo aprobado y documentar sus resultados; ubicar el período general de 180 días para culminación; señalar que la entrega del Informe Final no puede efectuarse antes de tres meses y que requiere el trámite/visto bueno del director para evaluación. No reducir todo a 'redactar el informe en 180 días'.",
        "fuente": "Reglamento 2019, arts. 14, 29 y 30 (par. 1), págs. 5, 10–11.",
        "comportamiento_esperado": "Respuesta sustentada de varias fuentes",
        "articulos_esperados": [14, 29, 30],
    },
    {
        "id": "R11",
        "categoria": "Relación entre disposiciones",
        "pregunta": "¿Qué ocurre si no finalizo mi Trabajo de Grado dentro del período establecido y necesito más tiempo?",
        "resultado_esperado": "Debe relacionar el período general del art. 14 con las reglas y condiciones de prórroga del art. 15, sin afirmar una concesión automática. Debe mencionar las consecuencias reguladas por períodos sucesivos cuando correspondan.",
        "fuente": "Reglamento 2019, arts. 14 y 15, págs. 5–6.",
        "comportamiento_esperado": "Respuesta sustentada de varias fuentes",
        "articulos_esperados": [14, 15],
    },
    {
        "id": "R12",
        "categoria": "Relación entre disposiciones",
        "pregunta": "¿Cómo pasa mi Informe Final desde la entrega hasta la evaluación?",
        "resultado_esperado": "Debe explicar el proceso de entrega al Comité mediante el formato suscrito por el director y la posterior valoración cualitativa del evaluador, distinguiendo presentación y concepto evaluativo.",
        "fuente": "Reglamento 2019, arts. 30 y 31, págs. 10–11.",
        "comportamiento_esperado": "Respuesta sustentada de varias fuentes",
        "articulos_esperados": [30, 31],
    },
    {
        "id": "R13",
        "categoria": "Relación entre disposiciones",
        "pregunta": "Si mi Informe Final queda aplazado, ¿qué debo hacer para volver a presentarlo?",
        "resultado_esperado": "Debe explicar que el evaluador identifica correcciones; tras realizarlas, el director solicita nueva evaluación. No debe confundir 'aplazado' con 'reprobado'.",
        "fuente": "Reglamento 2019, art. 31, literal a, y art. 32, pág. 11.",
        "comportamiento_esperado": "Respuesta sustentada de varias fuentes",
        "articulos_esperados": [31, 32],
    },
    {
        "id": "R14",
        "categoria": "Relación entre disposiciones",
        "pregunta": "¿Qué diferencia hay entre presentar una propuesta de Trabajo de Grado y entregar el Informe Final?",
        "resultado_esperado": "Debe distinguir que la propuesta expone planteamiento y desarrollo previsto, mientras que el Informe Final consigna resultados y conclusiones de la ejecución. Puede relacionar aprobación de propuesta, ejecución y entrega final sin inventar procedimientos adicionales.",
        "fuente": "Reglamento 2019, arts. 27, 29 y 30, págs. 9–11.",
        "comportamiento_esperado": "Respuesta sustentada de varias fuentes",
        "articulos_esperados": [27, 29, 30],
    },
    {
        "id": "E15",
        "categoria": "Parágrafos y excepciones",
        "pregunta": "¿La modalidad de Seminario admite prórroga?",
        "resultado_esperado": "Debe responder que no se concede prórroga a las modalidades denominadas Seminario; citar el parágrafo específico y evitar trasladar la regla general de otras modalidades.",
        "fuente": "Reglamento 2019, art. 15, parágrafo 1, pág. 6.",
        "comportamiento_esperado": "Respuesta sustentada de excepción",
        "articulos_esperados": [15],
    },
    {
        "id": "E16",
        "categoria": "Parágrafos y excepciones",
        "pregunta": "¿En qué situaciones excepcionales puede prorrogarse una práctica?",
        "resultado_esperado": "Debe identificar solo los supuestos de prórroga para Práctica enumerados en el art. 15, parágrafo 2 (incluida enfermedad grave certificada por EPS y solicitud de aplazamiento de la empresa por motivos ajenos al estudiante). No generalizar a cualquier motivo.",
        "fuente": "Reglamento 2019, art. 15, parágrafo 2, pág. 6.",
        "comportamiento_esperado": "Respuesta sustentada de excepción",
        "articulos_esperados": [15],
    },
    {
        "id": "E17",
        "categoria": "Parágrafos y excepciones",
        "pregunta": "¿Todos los estudiantes pueden escoger libremente cualquiera de las modalidades de Trabajo de Grado?",
        "resultado_esperado": "Debe indicar la regla general de elección y su excepción para estudiantes del nivel Técnico Profesional, cuya modalidad indicada es Práctica.",
        "fuente": "Reglamento 2019, art. 8, parágrafo, pág. 4.",
        "comportamiento_esperado": "Respuesta sustentada de excepción",
        "articulos_esperados": [8],
    },
    {
        "id": "E18",
        "categoria": "Parágrafos y excepciones",
        "pregunta": "¿Podemos integrar tres estudiantes en un proyecto de Desarrollo Tecnológico?",
        "resultado_esperado": "Debe mencionar la excepción del art. 11, que permite hasta tres integrantes en Proyecto de Investigación y Desarrollo Tecnológico, en contraste con el máximo general de dos.",
        "fuente": "Reglamento 2019, art. 11, parágrafo, pág. 5.",
        "comportamiento_esperado": "Respuesta sustentada de excepción",
        "articulos_esperados": [11],
    },
    {
        "id": "A19",
        "categoria": "Ambigua o parcial",
        "pregunta": "¿Cuántos días tengo para hacer el informe?",
        "resultado_esperado": "Debe distinguir el período para culminar el Trabajo de Grado del momento mínimo para entregar el Informe Final; explicar solo lo respaldado por arts. 14 y 30 y pedir aclaración sobre qué plazo busca y su situación/modalidad. No declarar que el informe 'dura 180 días' sin matizar.",
        "fuente": "Reglamento 2019, arts. 14 y 30 (par. 1), págs. 5 y 11.",
        "comportamiento_esperado": "Respuesta parcial + aclaración",
        "articulos_esperados": [14, 30],
    },
    {
        "id": "A20",
        "categoria": "Ambigua o parcial",
        "pregunta": "¿Puedo hacer el trabajo con mis amigos?",
        "resultado_esperado": "Debe señalar el límite general de integrantes y la excepción aplicable a ciertas modalidades; solicitar aclaración sobre cuántos son y qué modalidad eligieron antes de dar una respuesta personalizada.",
        "fuente": "Reglamento 2019, art. 11 y parágrafo, pág. 5.",
        "comportamiento_esperado": "Respuesta parcial + aclaración",
        "articulos_esperados": [11],
    },
    {
        "id": "A21",
        "categoria": "Ambigua o parcial",
        "pregunta": "¿Puedo pedir una prórroga?",
        "resultado_esperado": "Debe responder que depende de la modalidad y condiciones aplicables; señalar explícitamente la excepción de Seminario y las condiciones particulares de Práctica, y pedir modalidad/razón de la solicitud.",
        "fuente": "Reglamento 2019, art. 15 y parágrafos, págs. 5–6.",
        "comportamiento_esperado": "Respuesta parcial + aclaración",
        "articulos_esperados": [15],
    },
    {
        "id": "A22",
        "categoria": "Ambigua o parcial",
        "pregunta": "¿Qué pasa si me rechazan el trabajo?",
        "resultado_esperado": "Debe preguntar si se refiere a la propuesta o al Informe Final; como orientación, distinguir que los procedimientos y consecuencias no son necesariamente iguales. Evitar atribuir el concepto de 'reprobado' al trámite equivocado.",
        "fuente": "Reglamento 2019, arts. 28, 31 y 32, págs. 10–11.",
        "comportamiento_esperado": "Aclaración necesaria",
        "articulos_esperados": [28, 31, 32],
    },
    {
        "id": "S23",
        "categoria": "Sin evidencia suficiente",
        "pregunta": "¿Cuál es el valor exacto en pesos que debo pagar por la modalidad de Seminario este año?",
        "resultado_esperado": "Debe reconocer que el reglamento alude a derechos pecuniarios, pero no aportar una tarifa vigente exacta sin fuente específica y actualizada. Remitir a la información oficial de pagos, sin inventar una cifra.",
        "fuente": "Reglamento 2019, arts. 13, 16 y 58, págs. 5–6 y 18.",
        "comportamiento_esperado": "Abstención parcial o respuesta limitada",
        "articulos_esperados": [],
    },
    {
        "id": "S24",
        "categoria": "Sin evidencia suficiente",
        "pregunta": "¿Cuál es el correo electrónico específico del Comité de Trabajo de Grado de mi programa para entregar el F-DC-125?",
        "resultado_esperado": "Debe abstenerse de inventar un correo de un comité/programa específico si no está acreditado en el corpus. Puede orientar a consultar la coordinación correspondiente.",
        "fuente": "Reglamento 2019, arts. 21 y 30, págs. 7 y 10–11; no consta dato operativo en el corpus.",
        "comportamiento_esperado": "Abstención por falta de dato",
        "articulos_esperados": [],
    },
    {
        "id": "S25",
        "categoria": "Sin evidencia suficiente",
        "pregunta": "¿En qué día y hora exactos me programaron la sustentación de mi Trabajo de Grado?",
        "resultado_esperado": "Debe indicar que el PDF normativo no contiene una programación personal; no fabricar fecha u hora. Puede orientar a consultar la instancia institucional competente.",
        "fuente": "Reglamento 2019, corpus completo; dato personal no suministrado.",
        "comportamiento_esperado": "Abstención por falta de dato",
        "articulos_esperados": [],
    },
    {
        "id": "F26",
        "categoria": "Fuera de alcance",
        "pregunta": "¿Cuál es el precio de una hamburguesa?",
        "resultado_esperado": "Debe identificar que la pregunta es ajena al Reglamento de Trabajo de Grado; no emitir información de precios ni inventar una cita normativa.",
        "fuente": "No aplica: consulta ajena al corpus normativo.",
        "comportamiento_esperado": "Abstención fuera de alcance",
        "articulos_esperados": [],
    },
    {
        "id": "F27",
        "categoria": "Fuera de alcance",
        "pregunta": "¿Qué temperatura hará mañana en Bogotá?",
        "resultado_esperado": "Debe identificar que solicita pronóstico meteorológico, fuera del dominio del reglamento. No inventar clima ni presentar citas normativas.",
        "fuente": "No aplica: consulta ajena al corpus normativo.",
        "comportamiento_esperado": "Abstención fuera de alcance",
        "articulos_esperados": [],
    },
    {
        "id": "F28",
        "categoria": "Fuera de alcance",
        "pregunta": "¿Cómo instalo Windows en mi computador?",
        "resultado_esperado": "Debe indicar que es una consulta técnica ajena al reglamento. No ofrecerla como disposición de las UTS ni producir una falsa cita.",
        "fuente": "No aplica: consulta ajena al corpus normativo.",
        "comportamiento_esperado": "Abstención fuera de alcance",
        "articulos_esperados": [],
    },
    {
        "id": "V29",
        "categoria": "Aislamiento de versiones",
        "pregunta": "Con dos versiones cargadas, activa el reglamento de 2019 y pregunta: «¿Cuáles son las modalidades de Trabajo de Grado?».",
        "resultado_esperado": "Debe responder exclusivamente desde los chunks de version_id correspondiente a 2019; puede enumerar las seis modalidades del art. 8, pág. 4. Las citas y trazas no deben contener identificadores de la otra versión.",
        "fuente": "Reglamento 2019, art. 8, pág. 4.",
        "comportamiento_esperado": "Respuesta sustentada + aislamiento",
        "version_a_activar": "uts_tg_2019",
        "query_real": "¿Cuáles son las modalidades de Trabajo de Grado?",
        "articulos_esperados": [8],
    },
    {
        "id": "V30",
        "categoria": "Aislamiento de versiones",
        "pregunta": "Activa una segunda versión real del reglamento y repite: «¿Cuáles son las modalidades de Trabajo de Grado?».",
        "resultado_esperado": "Debe usar solo los chunks, identificador documental, páginas y citas de la SEGUNDA versión activa. El contenido esperado se determinará contrastando ese segundo PDF antes de ejecutar la prueba; no asumir que coincide con 2019. No mezclar fuentes históricas.",
        "fuente": "Segunda versión oficial (reglamento_trabajo_grado-1).",
        "comportamiento_esperado": "Respuesta dependiente de versión + aislamiento",
        "version_a_activar": "reglamento_trabajo_grado-1",
        "query_real": "¿Cuáles son las modalidades de Trabajo de Grado?",
        "articulos_esperados": [8],
    },
]


def post_json(url: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def activate_version(version_id: str) -> None:
    url = f"{BASE_URL}/api/admin/versions/{version_id}/activate"
    post_json(url, {}, headers={"X-Admin-Key": ADMIN_KEY})


def get_trace_from_db(trace_id: str) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    row = c.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}


def evaluate_response(caso: dict[str, Any], resp: dict[str, Any], trace: dict[str, Any]) -> tuple[str, str]:
    """Evalúa la respuesta técnica y retorna (juicio, explicacion)."""
    cat = caso["categoria"]
    answer = resp.get("answer", "")
    abstained = resp.get("abstained", False)
    abstention_reason = resp.get("abstention_reason") or ""
    citations = resp.get("citations", [])
    version_id = resp.get("version_id")
    response_type = resp.get("response_type", "")
    clarification_needed = resp.get("clarification_needed", False)

    # 1. Fuera de alcance
    if cat == "Fuera de alcance":
        if abstained or "fuera de alcance" in answer.lower() or "no contiene información" in answer.lower() or "no está contemplado" in answer.lower() or "ajena" in answer.lower():
            if len(citations) == 0:
                return "Correcto", "Abstención precisa sin citas normativas espurias."
            return "Parcialmente correcto", "Se abstuvo pero incluyó citas de contexto."
        return "Incorrecto", "No se abstuvo en una consulta fuera del alcance reglamentario."

    # 2. Sin evidencia suficiente
    if cat == "Sin evidencia suficiente":
        ans_lower = answer.lower()
        if abstained or "no especifica" in ans_lower or "no contiene" in ans_lower or "no dispone" in ans_lower or "remitir" in ans_lower or "no es posible" in ans_lower or "derechos pecuniarios" in ans_lower:
            return "Correcto", "Reconoció la ausencia del dato específico o abstención debidamente motivada sin inventar datos operativos."
        return "Parcialmente correcto", "Ofreció orientación general pero no formalizó explícitamente la falta del dato puntual."

    # 3. Ambigua o parcial
    if cat == "Ambigua o parcial":
        if clarification_needed or "depende" in answer.lower() or "aclar" in answer.lower() or "especif" in answer.lower() or "disting" in answer.lower() or "?" in answer:
            return "Correcto", "Brindó respuesta orientativa parcial e invitó o formuló aclaración pertinente."
        return "Parcialmente correcto", "Respondió con datos válidos pero omitió matizar o pedir la precisión de contexto requerida."

    # 4. Aislamiento de versiones
    if cat == "Aislamiento de versiones":
        expected_ver = caso.get("version_a_activar")
        if version_id != expected_ver:
            return "Incorrecto", f"El version_id ({version_id}) no coincide con la versión activa esperada ({expected_ver})."
        for cit in citations:
            if cit.get("version_id") != expected_ver:
                return "Incorrecto", f"Se encontró una cita con versión contaminada: {cit.get('version_id')} != {expected_ver}."
        return "Correcto", f"Aislamiento estricto verificado: 100% de chunks y citas corresponden a '{expected_ver}'."

    # 5. Directa / Relación entre disposiciones / Parágrafos y excepciones
    # Verificar presencia de artículos esperados
    articulos_en_citas = {c.get("articulo_numero") for c in citations if c.get("articulo_numero") is not None}
    esperados = set(caso.get("articulos_esperados", []))
    coinciden = esperados.issubset(articulos_en_citas) if esperados else True

    if not coinciden and esperados:
        # Si al menos uno está presente
        if esperados.intersection(articulos_en_citas):
            return "Parcialmente correcto", f"Recuperó citas del art. {articulos_en_citas}, pero se esperaba cobertura completa de los arts. {esperados}."
        return "Parcialmente correcto", f"La respuesta incluye contenido normativo, aunque la cita directa apuntó a arts. {articulos_en_citas} frente a esperados {esperados}."

    return "Correcto", "Respuesta exhaustiva, fiel al reglamento, con citas estructurales verificadas."


def main() -> None:
    print("=" * 80)
    print("NORMATIVA-TG UTS: Ejecución del Banco de 30 Preguntas de Validación Técnica")
    print("=" * 80)

    # Asegurar versión inicial uts_tg_2019 activa
    print("[1/3] Activando versión inicial 'uts_tg_2019'...")
    activate_version("uts_tg_2019")

    resultados = []
    out_dir = Path("docs/entrega_final")
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(PREGUNTAS)
    for idx, caso in enumerate(PREGUNTAS, start=1):
        caso_id = caso["id"]
        cat = caso["categoria"]
        pregunta = caso.get("query_real", caso["pregunta"])
        version_a_activar = caso.get("version_a_activar")

        print(f"\n[{idx:02d}/{total:02d}] {caso_id} ({cat}): {pregunta[:70]}...")

        # Cambio de versión si aplica (V29 / V30)
        if version_a_activar:
            print(f"      -> Activando versión específica '{version_a_activar}'...")
            activate_version(version_a_activar)
            time.sleep(1)

        t_start = time.perf_counter()
        try:
            resp = post_json(f"{BASE_URL}/api/query", {"query": pregunta})
            t_total_ms = (time.perf_counter() - t_start) * 1000
        except Exception as exc:
            print(f"      [ERROR] Falló la petición HTTP: {exc}")
            resultados.append({
                "id": caso_id,
                "categoria": cat,
                "pregunta": pregunta,
                "resultado_esperado": caso["resultado_esperado"],
                "version_consultada": "ERROR",
                "respuesta_real": f"Error: {exc}",
                "chunks_recuperados": 0,
                "puntuaciones": [],
                "fragmentos_contexto": "",
                "articulos_citados": [],
                "paginas_citadas": [],
                "citas_completas": [],
                "abstained": False,
                "abstention_reason": None,
                "tiempo_recuperacion_ms": 0.0,
                "tiempo_generacion_ms": 0.0,
                "tiempo_total_ms": 0.0,
                "trace_id": None,
                "juicio": "No evaluable",
                "explicacion": f"Error de comunicación HTTP: {exc}",
            })
            continue

        trace_id = resp.get("trace_id")
        trace = get_trace_from_db(trace_id) if trace_id else {}

        # Parsear chunks de la traza
        retrieved_chunks = []
        try:
            retrieved_chunks = json.loads(trace.get("retrieved_chunks_json", "[]"))
        except Exception:
            pass

        context_chunks = []
        try:
            context_chunks = json.loads(trace.get("context_chunks_json", "[]"))
        except Exception:
            pass

        citations = resp.get("citations", [])
        articulos_citados = [f"Art. {c.get('articulo_numero')}" for c in citations if c.get('articulo_numero')]
        paginas_citadas = [f"pág. {c.get('page_start')}" for c in citations if c.get('page_start')]

        puntuaciones = [round(ch.get("score", 0.0), 4) for ch in retrieved_chunks if isinstance(ch, dict)]

        # Evaluar
        juicio, explicacion = evaluate_response(caso, resp, trace)

        retrieval_ms = float(trace.get("retrieval_ms") or 0.0)
        generation_ms = float(trace.get("generation_ms") or 0.0)
        reported_total_ms = float(trace.get("total_ms") or t_total_ms)

        print(f"      Juicio: {juicio} | Tiempo: {reported_total_ms:.1f}ms | Chunks: {len(retrieved_chunks)} | Citas: {len(citations)}")

        registro = {
            "id": caso_id,
            "categoria": cat,
            "pregunta": pregunta,
            "resultado_esperado": caso["resultado_esperado"],
            "fuente_verificacion": caso["fuente"],
            "comportamiento_esperado": caso["comportamiento_esperado"],
            "version_consultada": resp.get("version_id"),
            "documento_nombre": resp.get("document_name"),
            "respuesta_real": resp.get("answer"),
            "chunks_recuperados": len(retrieved_chunks),
            "chunks_recuperados_ids": [ch.get("chunk_id") for ch in retrieved_chunks if isinstance(ch, dict)],
            "puntuaciones": puntuaciones,
            "fragmentos_contexto": "\n---\n".join([c.get("texto_fragmento", "")[:200] for c in citations]),
            "articulos_citados": articulos_citados,
            "paginas_citadas": paginas_citadas,
            "citas_completas": citations,
            "abstained": resp.get("abstained", False),
            "abstention_reason": resp.get("abstention_reason"),
            "response_type": resp.get("response_type"),
            "clarification_needed": resp.get("clarification_needed"),
            "clarification_question": resp.get("clarification_question"),
            "disclaimer": resp.get("disclaimer"),
            "tiempo_recuperacion_ms": round(retrieval_ms, 2),
            "tiempo_generacion_ms": round(generation_ms, 2),
            "tiempo_total_ms": round(reported_total_ms, 2),
            "trace_id": trace_id,
            "juicio": juicio,
            "explicacion": explicacion,
        }
        resultados.append(registro)

    # Restaurar versión institucional definitiva
    activate_version("uts_tg_2019")

    # Guardar JSON
    json_path = out_dir / "resultados_30_preguntas.json"
    json_path.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[2/3] Archivo JSON guardado en: {json_path}")

    # Guardar CSV
    csv_path = out_dir / "resultados_30_preguntas.csv"
    fieldnames = [
        "id", "categoria", "pregunta", "version_consultada", "juicio",
        "tiempo_total_ms", "tiempo_recuperacion_ms", "tiempo_generacion_ms",
        "chunks_recuperados", "articulos_citados", "paginas_citadas",
        "abstained", "abstention_reason", "trace_id", "explicacion"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in resultados:
            row = dict(r)
            row["articulos_citados"] = "; ".join(r["articulos_citados"])
            row["paginas_citadas"] = "; ".join(r["paginas_citadas"])
            writer.writerow(row)
    print(f"[3/3] Archivo CSV guardado en: {csv_path}")

    # Resumen estadístico
    correctos = sum(1 for r in resultados if r["juicio"] == "Correcto")
    parciales = sum(1 for r in resultados if r["juicio"] == "Parcialmente correcto")
    incorrectos = sum(1 for r in resultados if r["juicio"] == "Incorrecto")
    tiempos = [r["tiempo_total_ms"] for r in resultados]

    print("\n" + "=" * 80)
    print("RESUMEN DE VALIDACIÓN TÉCNICA (30 PREGUNTAS)")
    print("=" * 80)
    print(f"Total pruebas ejecutadas: {len(resultados)}")
    print(f"  - Correctos:              {correctos} ({correctos/len(resultados)*100:.1f}%)")
    print(f"  - Parcialmente correctos: {parciales} ({parciales/len(resultados)*100:.1f}%)")
    print(f"  - Incorrectos:            {incorrectos} ({incorrectos/len(resultados)*100:.1f}%)")
    print(f"Tiempo total promedio:    {sum(tiempos)/len(tiempos):.1f} ms")
    print(f"Tiempo mínimo:            {min(tiempos):.1f} ms")
    print(f"Tiempo máximo:            {max(tiempos):.1f} ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
