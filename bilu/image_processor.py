"""
LEAF - Modulo de Processamento de Imagem
Classe ImageProcessor: pipeline de PDI deterministico para segmentacao foliar.
Suporta espacos de cores HSV e CIELAB, e reconstrucao por Convex Hull ou Fechamento Morfologico.
"""

from enum import Enum
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple


class ColorMode(Enum):
    HSV = "HSV"
    CIELAB = "CIELAB"


class HullMethod(Enum):
    CONVEX_HULL = "Convex Hull"
    MORPHOLOGICAL_CLOSURE = "Fechamento Morfologico"


@dataclass
class HSVRange:
    """Faixa HSV para segmentacao de uma classe de pixel."""
    lower: np.ndarray
    upper: np.ndarray

    @staticmethod
    def from_sliders(
        h_min: int, h_max: int,
        s_min: int, s_max: int,
        v_min: int, v_max: int,
    ) -> "HSVRange":
        return HSVRange(
            lower=np.array([h_min, s_min, v_min], dtype=np.uint8),
            upper=np.array([h_max, s_max, v_max], dtype=np.uint8),
        )


@dataclass
class LABRange:
    """Faixa CIELAB para segmentacao de uma classe de pixel."""
    lower: np.ndarray
    upper: np.ndarray

    @staticmethod
    def from_sliders(
        l_min: int, l_max: int,
        a_min: int, a_max: int,
        b_min: int, b_max: int,
    ) -> "LABRange":
        return LABRange(
            lower=np.array([l_min, a_min, b_min], dtype=np.uint8),
            upper=np.array([l_max, a_max, b_max], dtype=np.uint8),
        )


@dataclass
class SegmentationResult:
    """Resultado bruto da segmentacao de uma imagem."""
    original_bgr: np.ndarray
    color_converted: np.ndarray  # HSV ou LAB convertido
    mask_healthy: np.ndarray
    mask_symptomatic: np.ndarray
    mask_leaf: np.ndarray
    mask_background: np.ndarray
    rebuilt_silhouette_mask: np.ndarray  # Convex Hull ou Fechamento Morfologico
    contours_healthy: list = field(default_factory=list)
    contours_symptomatic: list = field(default_factory=list)
    hull_points: Optional[np.ndarray] = None  # Apenas se usar Convex Hull
    silhouette_contour: Optional[np.ndarray] = None  # Contorno da silhueta reconstruida
    overlay: Optional[np.ndarray] = None
    color_mode: ColorMode = ColorMode.HSV
    reconstruction_method: HullMethod = HullMethod.CONVEX_HULL
    error: Optional[str] = None


class ImageProcessor:
    """
    Pipeline deterministico de PDI para analise foliar.
    """

    # Parametros padrao HSV
    DEFAULT_GREEN_HSV = HSVRange.from_sliders(35, 85, 40, 255, 40, 255)
    DEFAULT_SYMPTOMATIC_HSV = HSVRange.from_sliders(10, 34, 40, 255, 40, 255)

    # Parametros padrao CIELAB (L*, a*, b*)
    # a* baixo representa tons verdes, a* alto representa tons vermelhos/marrons.
    # b* alto representa tons amarelados.
    DEFAULT_GREEN_LAB = LABRange.from_sliders(20, 255, 0, 120, 128, 255)
    DEFAULT_SYMPTOMATIC_LAB = LABRange.from_sliders(20, 255, 121, 255, 120, 255)

    # Elementos estruturantes para morfologia fina
    _KERNEL_CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    _KERNEL_OPEN  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # Cores no overlay (BGR)
    COLOR_HEALTHY     = (31, 122, 53)    # Verde
    COLOR_SYMPTOMATIC = (90, 89, 186)    # Roxo/Vermelho suave
    COLOR_SILHOUETTE  = (5, 181, 227)   # Amarelo/Dourado

    def __init__(
        self,
        color_mode: ColorMode = ColorMode.HSV,
        hull_method: HullMethod = HullMethod.CONVEX_HULL,
        green_hsv: Optional[HSVRange] = None,
        symptomatic_hsv: Optional[HSVRange] = None,
        green_lab: Optional[LABRange] = None,
        symptomatic_lab: Optional[LABRange] = None,
        min_contour_area: int = 200,
        morph_kernel_size: int = 25,
    ) -> None:
        self.color_mode = color_mode
        self.hull_method = hull_method
        self.green_hsv = green_hsv or self.DEFAULT_GREEN_HSV
        self.symptomatic_hsv = symptomatic_hsv or self.DEFAULT_SYMPTOMATIC_HSV
        self.green_lab = green_lab or self.DEFAULT_GREEN_LAB
        self.symptomatic_lab = symptomatic_lab or self.DEFAULT_SYMPTOMATIC_LAB
        self.min_contour_area = min_contour_area
        self.morph_kernel_size = morph_kernel_size

    def process(self, image_data: bytes) -> SegmentationResult:
        """
        Processa bytes de imagem e retorna SegmentationResult.
        """
        bgr = self._decode(image_data)
        if bgr is None:
            return SegmentationResult(
                original_bgr=np.zeros((1, 1, 3), np.uint8),
                color_converted=np.zeros((1, 1, 3), np.uint8),
                mask_healthy=np.zeros((1, 1), np.uint8),
                mask_symptomatic=np.zeros((1, 1), np.uint8),
                mask_leaf=np.zeros((1, 1), np.uint8),
                mask_background=np.zeros((1, 1), np.uint8),
                rebuilt_silhouette_mask=np.zeros((1, 1), np.uint8),
                color_mode=self.color_mode,
                reconstruction_method=self.hull_method,
                error="Nao foi possivel decodificar a imagem.",
            )

        # 1. Conversao de Espaco de Cores
        if self.color_mode == ColorMode.CIELAB:
            color_converted = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            mask_healthy = self._threshold_lab(color_converted, self.green_lab)
            mask_symptomatic = self._threshold_lab(color_converted, self.symptomatic_lab)
        else:
            color_converted = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            mask_healthy = self._threshold_hsv(color_converted, self.green_hsv)
            mask_symptomatic = self._threshold_hsv(color_converted, self.symptomatic_hsv)

        # 2. Mascara da Folha
        mask_leaf = cv2.bitwise_or(mask_healthy, mask_symptomatic)
        mask_background = cv2.bitwise_not(mask_leaf)

        # 3. Reconstrucao da Silhueta (Convex Hull vs Fechamento Morfologico Adaptativo)
        if self.hull_method == HullMethod.CONVEX_HULL:
            rebuilt_mask, hull_pts = self._compute_convex_hull(mask_leaf, bgr.shape[:2])
            silhouette_contour = hull_pts
        else:
            rebuilt_mask, silhouette_contour = self._compute_morphological_closure(
                mask_leaf, bgr.shape[:2], self.morph_kernel_size
            )
            hull_pts = None

        # 4. Extracao de Contornos Finais para Visualizacao
        contours_healthy, _ = cv2.findContours(
            mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contours_symptomatic, _ = cv2.findContours(
            mask_symptomatic, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        contours_healthy = [
            c for c in contours_healthy if cv2.contourArea(c) >= self.min_contour_area
        ]
        contours_symptomatic = [
            c for c in contours_symptomatic if cv2.contourArea(c) >= self.min_contour_area
        ]

        # 5. Criacao do Overlay Visual
        overlay = self._build_overlay(
            bgr, contours_healthy, contours_symptomatic, silhouette_contour
        )

        return SegmentationResult(
            original_bgr=bgr,
            color_converted=color_converted,
            mask_healthy=mask_healthy,
            mask_symptomatic=mask_symptomatic,
            mask_leaf=mask_leaf,
            mask_background=mask_background,
            rebuilt_silhouette_mask=rebuilt_mask,
            contours_healthy=contours_healthy,
            contours_symptomatic=contours_symptomatic,
            hull_points=hull_pts,
            silhouette_contour=silhouette_contour,
            overlay=overlay,
            color_mode=self.color_mode,
            reconstruction_method=self.hull_method,
        )

    @staticmethod
    def _decode(data: bytes) -> Optional[np.ndarray]:
        """Decodifica bytes para array BGR."""
        buf = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return img

    def _threshold_hsv(self, hsv: np.ndarray, hsv_range: HSVRange) -> np.ndarray:
        """Thresholding no espaco HSV com morfologia para reducao de ruido."""
        lower, upper = hsv_range.lower, hsv_range.upper

        if lower[0] <= upper[0]:
            mask = cv2.inRange(hsv, lower, upper)
        else:
            lower_a = np.array([lower[0], lower[1], lower[2]], dtype=np.uint8)
            upper_a = np.array([179,       upper[1], upper[2]], dtype=np.uint8)
            lower_b = np.array([0,         lower[1], lower[2]], dtype=np.uint8)
            upper_b = np.array([upper[0],  upper[1], upper[2]], dtype=np.uint8)
            mask = cv2.bitwise_or(
                cv2.inRange(hsv, lower_a, upper_a),
                cv2.inRange(hsv, lower_b, upper_b),
            )

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._KERNEL_CLOSE)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._KERNEL_OPEN)
        return mask

    def _threshold_lab(self, lab: np.ndarray, lab_range: LABRange) -> np.ndarray:
        """Thresholding no espaco CIELAB resistente a sombras."""
        lower, upper = lab_range.lower, lab_range.upper
        mask = cv2.inRange(lab, lower, upper)

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._KERNEL_CLOSE)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._KERNEL_OPEN)
        return mask

    @staticmethod
    def _compute_convex_hull(
        mask_leaf: np.ndarray,
        shape: Tuple[int, int],
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Calcula o convex hull sobre todos os pontos da folha."""
        hull_mask = np.zeros(shape, dtype=np.uint8)
        points = cv2.findNonZero(mask_leaf)
        if points is None or len(points) < 3:
            return hull_mask, None

        hull = cv2.convexHull(points)
        cv2.fillPoly(hull_mask, [hull], 255)
        return hull_mask, hull

    @staticmethod
    def _compute_morphological_closure(
        mask_leaf: np.ndarray,
        shape: Tuple[int, int],
        kernel_size: int,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Metodo alternativo ao Convex Hull para folhas lobadas.
        Faz uma Dilatacao robusta para unir as bordas da folha seguida de Erosao.
        Evita a convexidade forcada de reentrancias.
        """
        rebuilt_mask = np.zeros(shape, dtype=np.uint8)
        if cv2.countNonZero(mask_leaf) == 0:
            return rebuilt_mask, None

        # Garante kernel impar
        k_size = kernel_size if kernel_size % 2 != 0 else kernel_size + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))

        # Dilata para fechar buracos externos e lobulos
        dilated = cv2.dilate(mask_leaf, kernel, iterations=1)
        # Preenche os contornos internos para garantir silhueta sólida
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cv2.drawContours(dilated, contours, -1, 255, -1)

        # Erode de volta ao tamanho original da borda externa
        rebuilt_mask = cv2.erode(dilated, kernel, iterations=1)

        # Pega o maior contorno resultante da silhueta para visualizacao
        silh_contours, _ = cv2.findContours(rebuilt_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if silh_contours:
            largest_contour = max(silh_contours, key=cv2.contourArea)
            return rebuilt_mask, largest_contour

        return rebuilt_mask, None

    def _build_overlay(
        self,
        bgr: np.ndarray,
        contours_healthy: list,
        contours_symptomatic: list,
        silhouette_contour: Optional[np.ndarray],
    ) -> np.ndarray:
        """Gera imagem overlay com estilo cientifico sutil."""
        overlay = bgr.copy()
        alpha_layer = bgr.copy()

        # Preenchimento semitransparente
        if contours_healthy:
            cv2.drawContours(alpha_layer, contours_healthy, -1, self.COLOR_HEALTHY, cv2.FILLED)
        if contours_symptomatic:
            cv2.drawContours(alpha_layer, contours_symptomatic, -1, self.COLOR_SYMPTOMATIC, cv2.FILLED)

        overlay = cv2.addWeighted(overlay, 0.75, alpha_layer, 0.25, 0)

        # Contornos finos e precisos
        if contours_healthy:
            cv2.drawContours(overlay, contours_healthy, -1, self.COLOR_HEALTHY, 1, cv2.LINE_AA)
        if contours_symptomatic:
            cv2.drawContours(overlay, contours_symptomatic, -1, self.COLOR_SYMPTOMATIC, 1, cv2.LINE_AA)

        # Contorno da Silhueta Reconstruida
        if silhouette_contour is not None:
            cv2.drawContours(overlay, [silhouette_contour], -1, self.COLOR_SILHOUETTE, 2, cv2.LINE_AA)

        return overlay
