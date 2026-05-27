"""
LEAF - Estado global da aplicação com persistência em disco.
O histórico de análises é salvo automaticamente em JSON para sobreviver entre sessões.
"""

import json
import os

# Arquivo de persistência (ao lado do executável)
_STATE_DIR = os.path.dirname(os.path.abspath(__file__))
_HISTORY_FILE = os.path.join(_STATE_DIR, "..", "leaf_history.json")

app_state = {
    "hsv_green": (35, 85, 40, 255, 40, 255),
    "hsv_symp": (10, 34, 40, 255, 40, 255),
    "lab_green": (20, 255, 0, 120, 128, 255),
    "lab_symp": (20, 255, 121, 255, 120, 255),
    "color_mode": "HSV",
    "hull_method": "Convex Hull",
    "min_area": 200,
    "morph_kernel_size": 25,
    "ppm": 37.8,
    "use_background_removal": True,
    "grabcut_iterations": 3,
    "analysis_history": [],
    "batch_metrics": [],
    "batch_overlays": [],
    "last_result": None
}


def load_history():
    """Carrega o histórico de análises do disco, se existir."""
    try:
        path = os.path.normpath(_HISTORY_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                app_state["analysis_history"] = data
    except (json.JSONDecodeError, IOError, OSError):
        pass  # arquivo corrompido ou inacessível — ignorar silenciosamente


def save_history():
    """Salva o histórico de análises em disco (JSON)."""
    try:
        path = os.path.normpath(_HISTORY_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(app_state["analysis_history"], f, ensure_ascii=False, indent=2)
    except (IOError, OSError):
        pass  # falha silenciosa — não impedir o encerramento do app


# Carregar histórico ao importar o módulo
load_history()
