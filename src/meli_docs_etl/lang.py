"""Detección de idioma es/en basada en stopwords.

Determinista, sin dependencias y explicable. Para textos cortos devuelve
"unknown" en lugar de adivinar. Se excluyen palabras ambiguas entre ambos
idiomas ("a", "no", "me", "can"...).
"""

from __future__ import annotations

from dataclasses import dataclass

from meli_docs_etl.md_utils import strip_noise, words

ES_STOPWORDS = frozenset(
    """
    el la los las un una unos unas del al y o pero si sino que qué cual cuál
    cuando cuándo donde dónde como cómo porque para por con sin sobre entre hasta
    desde es son está están ser estar fue era hay tiene tienen puede pueden debe
    deben este esta estos estas ese esa eso esto su sus nuestro nuestra se lo le
    les ya muy más también cada todo todos toda todas otro otra mismo cuenta
    través según mediante dentro hacia sea será han ha sido siendo
    """.split()
)

EN_STOPWORDS = frozenset(
    """
    the of and or but if that which who when where how why for with without about
    between until from is are was were be been being has have had does do did this
    these those their there they them its it's our your you we will would should
    could must may might into onto than then also each every all any other same
    through within toward towards by an not only just more most such what
    """.split()
)


@dataclass(frozen=True)
class LangResult:
    label: str  # es | en | mixed | unknown
    es_hits: int
    en_hits: int


def detect_language(
    markdown: str, min_stopwords: int = 3, mixed_threshold: float = 0.7
) -> LangResult:
    toks = words(strip_noise(markdown))
    es = sum(t in ES_STOPWORDS for t in toks)
    en = sum(t in EN_STOPWORDS for t in toks)
    total = es + en
    if total < min_stopwords:
        return LangResult("unknown", es, en)
    if max(es, en) / total < mixed_threshold:
        return LangResult("mixed", es, en)
    return LangResult("es" if es > en else "en", es, en)
