from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class Inciso:
    marker: str
    texto: str


@dataclass(frozen=True, slots=True)
class Paragrafo:
    numero: str | None
    texto: str
    incisos: list[Inciso] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Articulo:
    kind: Literal["reglamento", "acuerdo"]
    numero: int | None
    ordinal: str | None
    capitulo_numero: int | None
    capitulo_romano: str | None
    capitulo_titulo: str | None
    texto: str
    incisos: list[Inciso] = field(default_factory=list)
    paragrafos: list[Paragrafo] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0
    ocr_confidence_mean: float | None = None
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ParseRepair:
    pagina: int
    original: str
    corregido: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ParseReport:
    repairs: list[ParseRepair] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    removed_lines_count: int = 0
    statistics: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_file: str
    num_pages: int
    preambulo: str
    articulos: list[Articulo]
    cierre: str
    report: ParseReport

