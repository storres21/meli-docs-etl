"""Fijación de semillas para reproducibilidad."""

from __future__ import annotations

import logging
import os
import random

log = logging.getLogger(__name__)


def set_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np  # opcional: aún no es dependencia

        np.random.seed(seed)
    except ImportError:
        pass
    log.debug("Semilla fijada en %d", seed)
