"""
LEAF - Modulo de Calculos Geometricos e Fitometricos
Classe Metrics: calcula todas as metricas de herbivoria e doenca em pixel e em cm².
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import numpy as np
import cv2

from image_processor import SegmentationResult


@dataclass
class ProcessingParameters:
    """Parametros utilizados no processamento para fins de reprodutibilidade."""
    color_mode: str
    reconstruction_method: str
    ppm: float  # Pixels Per Metric (pixels por cm)
    min_contour_area: int
    morph_kernel_size: int
    green_lower: List[int]
    green_upper: List[int]
    symptomatic_lower: List[int]
    symptomatic_upper: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Modo_Cores": self.color_mode,
            "Metodo_Reconstrucao": self.reconstruction_method,
            "Pixels_por_cm_PPM": self.ppm,
            "Area_Minima_Contorno_px": self.min_contour_area,
            "Kernel_Morfologico_Reconstrucao": self.morph_kernel_size,
            "Limiar_Verde_Inferior": self.green_lower,
            "Limiar_Verde_Superior": self.green_upper,
            "Limiar_Sintomas_Inferior": self.symptomatic_lower,
            "Limiar_Sintomas_Superior": self.symptomatic_upper,
        }


@dataclass
class LeafMetrics:
    """Conjunto completo de metricas fitometricas de uma imagem foliar."""
    filename: str

    # Contagem de pixels
    pixels_healthy: int
    pixels_symptomatic: int
    pixels_leaf: int          # saudavel + sintomatic
    pixels_silhouette: int    # area reconstruida da silhueta (Convex Hull ou Fechamento)

    # Metricas derivadas em Pixels
    area_original_px: int     # Silhueta reconstruida
    area_real_px: int         # Saudavel + Sintomatic
    herbivory_loss_px: int    # Area original - Area real

    # Metricas derivadas em cm² (usando PPM)
    ppm_used: float
    area_original_cm2: float
    area_real_cm2: float
    herbivory_loss_cm2: float

    # Metricas percentuais (%)
    disease_severity_pct: float  # (pixels_symptomatic / area_real_px) * 100
    herbivory_pct: float         # (herbivory_loss_px / area_original_px) * 100

    # Metadata
    image_width: int
    image_height: int
    reconstruction_method: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "Arquivo":                     self.filename,
            "Largura_px":                  self.image_width,
            "Altura_px":                   self.image_height,
            "Pixels_Saudaveis":            self.pixels_healthy,
            "Pixels_Sintomaticos":         self.pixels_symptomatic,
            "Pixels_Folha_Real":           self.pixels_leaf,
            "Pixels_Silhueta_Original":    self.pixels_silhouette,
            "PPM_Fator":                   self.ppm_used,
            "Area_Original_px2":           self.area_original_px,
            "Area_Real_px2":               self.area_real_px,
            "Perda_Herbivoria_px2":        self.herbivory_loss_px,
            "Area_Original_cm2":           round(self.area_original_cm2, 4),
            "Area_Real_cm2":               round(self.area_real_cm2, 4),
            "Perda_Herbivoria_cm2":        round(self.herbivory_loss_cm2, 4),
            "Severidade_Doenca_%":         round(self.disease_severity_pct, 4),
            "Herbivoria_%":                round(self.herbivory_pct, 4),
            "Metodo_Reconstrucao":         self.reconstruction_method,
            "Erro":                        self.error or "",
        }


class Metrics:
    """
    Calcula metricas fitometricas a partir de um SegmentationResult.
    Suporta conversao de escala por PPM (pixels por cm).
    """

    @staticmethod
    def compute(
        result: SegmentationResult,
        filename: str,
        ppm: float = 1.0,
    ) -> LeafMetrics:
        """
        Calcula as metricas fitometricas e retorna um LeafMetrics.
        Protegido contra divisao por zero.
        """
        h, w = result.original_bgr.shape[:2]

        # Fator PPM seguro (evitar divisao por zero se configurado incorretamente)
        safe_ppm = max(0.0001, ppm)
        ppm_divisor = safe_ppm ** 2

        # --- Retorno de emergencia se resultado invalido ---
        if result.error:
            return LeafMetrics(
                filename=filename,
                pixels_healthy=0, pixels_symptomatic=0,
                pixels_leaf=0, pixels_silhouette=0,
                area_original_px=0, area_real_px=0,
                herbivory_loss_px=0,
                ppm_used=safe_ppm,
                area_original_cm2=0.0, area_real_cm2=0.0,
                herbivory_loss_cm2=0.0,
                disease_severity_pct=0.0, herbivory_pct=0.0,
                image_width=w, image_height=h,
                reconstruction_method=result.reconstruction_method.value,
                error=result.error,
            )

        # --- Contagem de pixels ---
        pixels_healthy     = int(cv2.countNonZero(result.mask_healthy))
        pixels_symptomatic = int(cv2.countNonZero(result.mask_symptomatic))
        pixels_leaf        = pixels_healthy + pixels_symptomatic
        pixels_silhouette  = int(cv2.countNonZero(result.rebuilt_silhouette_mask))

        # --- Metricas geometricas em Pixels ---
        area_original_px = pixels_silhouette
        area_real_px     = pixels_leaf
        herbivory_loss_px = max(0, area_original_px - area_real_px)

        # --- Conversao para cm² ---
        area_original_cm2 = area_original_px / ppm_divisor
        area_real_cm2     = area_real_px / ppm_divisor
        herbivory_loss_cm2 = herbivory_loss_px / ppm_divisor

        # --- Metricas percentuais ---
        if area_real_px > 0:
            disease_severity_pct = (pixels_symptomatic / area_real_px) * 100.0
        else:
            disease_severity_pct = 0.0

        if area_original_px > 0:
            herbivory_pct = (herbivory_loss_px / area_original_px) * 100.0
        else:
            herbivory_pct = 0.0

        return LeafMetrics(
            filename=filename,
            pixels_healthy=pixels_healthy,
            pixels_symptomatic=pixels_symptomatic,
            pixels_leaf=pixels_leaf,
            pixels_silhouette=pixels_silhouette,
            area_original_px=area_original_px,
            area_real_px=area_real_px,
            herbivory_loss_px=herbivory_loss_px,
            ppm_used=safe_ppm,
            area_original_cm2=area_original_cm2,
            area_real_cm2=area_real_cm2,
            herbivory_loss_cm2=herbivory_loss_cm2,
            disease_severity_pct=disease_severity_pct,
            herbivory_pct=herbivory_pct,
            image_width=w,
            image_height=h,
            reconstruction_method=result.reconstruction_method.value,
        )

    @staticmethod
    def aggregate(metrics_list: List[LeafMetrics]) -> dict:
        """
        Agrega estatisticas descritivas de uma lista de LeafMetrics.
        """
        if not metrics_list:
            return {}

        valid = [m for m in metrics_list if m.error is None]
        if not valid:
            return {"total": len(metrics_list), "validos": 0}

        sev        = np.array([m.disease_severity_pct for m in valid])
        herb       = np.array([m.herbivory_pct for m in valid])
        area_px    = np.array([m.area_real_px for m in valid])
        area_cm2   = np.array([m.area_real_cm2 for m in valid])

        return {
            "total_imagens":             len(metrics_list),
            "imagens_validas":           len(valid),
            "imagens_com_erro":          len(metrics_list) - len(valid),
            "severidade_media_%":        float(round(sev.mean(), 3)),
            "severidade_desvio_%":       float(round(sev.std(), 3)),
            "severidade_min_%":          float(round(sev.min(), 3)),
            "severidade_max_%":          float(round(sev.max(), 3)),
            "herbivoria_media_%":        float(round(herb.mean(), 3)),
            "herbivoria_desvio_%":       float(round(herb.std(), 3)),
            "herbivoria_min_%":          float(round(herb.min(), 3)),
            "herbivoria_max_%":          float(round(herb.max(), 3)),
            "area_real_media_px2":       float(round(area_px.mean(), 1)),
            "area_real_media_cm2":       float(round(area_cm2.mean(), 4)),
        }

    @staticmethod
    def export_metadata(
        params: ProcessingParameters,
        aggregate_results: dict,
    ) -> Dict[str, Any]:
        """Gera dicionario de metadados consolidado para reprodutibilidade cientifica."""
        import datetime
        return {
            "Software": "LEAF (Leaf Evaluation & Analysis Framework)",
            "Versao": "2.0.0",
            "Data_Processamento": datetime.datetime.now().isoformat(),
            "Parametros_Configuracao": params.to_dict(),
            "Estatisticas_Agregadas": aggregate_results,
        }
