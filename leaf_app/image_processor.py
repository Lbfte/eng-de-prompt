"""
LEAF - Modulo de Processamento de Imagem
Classe ImageProcessor: pipeline de PDI deterministico para segmentacao foliar.
Suporta espacos de cores HSV e CIELAB, e reconstrucao por Convex Hull ou Fechamento Morfologico.
Etapa opcional de isolamento de fundo via GrabCut (BackgroundRemover).
"""

from enum import Enum
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple
from background_removal import BackgroundRemover


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
    fg_mask: Optional[np.ndarray] = None           # Mascara de foreground do GrabCut
    leaf_count: int = 1                             # Numero de folhas detectadas
    leaf_masks: list = field(default_factory=list)   # Mascaras individuais por folha
    overlay: Optional[np.ndarray] = None
    color_mode: ColorMode = ColorMode.HSV
    reconstruction_method: HullMethod = HullMethod.CONVEX_HULL
    background_removal_used: bool = False
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
        use_background_removal: bool = True,
        grabcut_iterations: int = 5,
    ) -> None:
        self.color_mode = color_mode
        self.hull_method = hull_method
        self.green_hsv = green_hsv or self.DEFAULT_GREEN_HSV
        self.symptomatic_hsv = symptomatic_hsv or self.DEFAULT_SYMPTOMATIC_HSV
        self.green_lab = green_lab or self.DEFAULT_GREEN_LAB
        self.symptomatic_lab = symptomatic_lab or self.DEFAULT_SYMPTOMATIC_LAB
        self.min_contour_area = min_contour_area
        self.morph_kernel_size = morph_kernel_size
        self.use_background_removal = use_background_removal
        self.grabcut_iterations = grabcut_iterations
        if use_background_removal:
            self._bg_remover = BackgroundRemover(grabcut_iterations=grabcut_iterations)
        else:
            self._bg_remover = None

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

        # 0. Isolamento de Fundo via GrabCut (opcional)
        fg_mask = None
        bg_removal_used = False
        if self._bg_remover is not None:
            fg_mask, success = self._bg_remover.remove(bgr)
            bg_removal_used = success

        # 1. Conversao de Espaco de Cores
        if self.color_mode == ColorMode.CIELAB:
            color_converted = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            mask_healthy = self._threshold_lab(color_converted, self.green_lab)
            mask_symptomatic = self._threshold_lab(color_converted, self.symptomatic_lab)
        else:
            color_converted = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            mask_healthy = self._threshold_hsv(color_converted, self.green_hsv)
            mask_symptomatic = self._threshold_hsv(color_converted, self.symptomatic_hsv)

        # 1b. Aplicar máscara de foreground para excluir pixels de fundo
        if fg_mask is not None and bg_removal_used:
            mask_healthy = cv2.bitwise_and(mask_healthy, fg_mask)
            mask_symptomatic = cv2.bitwise_and(mask_symptomatic, fg_mask)

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

        # 4.5 Detectar folhas individuais a partir da fg_mask
        leaf_count = 1
        leaf_masks = []
        if fg_mask is not None and bg_removal_used:
            leaf_count, leaf_masks = self._detect_individual_leaves(fg_mask)

        # 5. Criacao do Overlay Visual
        overlay = self._build_overlay(
            bgr, contours_healthy, contours_symptomatic, silhouette_contour,
            fg_mask if bg_removal_used else None, leaf_masks
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
            fg_mask=fg_mask,
            leaf_count=leaf_count,
            leaf_masks=leaf_masks,
            overlay=overlay,
            color_mode=self.color_mode,
            reconstruction_method=self.hull_method,
            background_removal_used=bg_removal_used,
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

    @staticmethod
    def _detect_individual_leaves(
        fg_mask: np.ndarray,
        dist_threshold_ratio: float = 0.45,
    ) -> Tuple[int, list]:
        """
        Identifica folhas individuais na mascara de foreground usando Watershed
        com Distance Transform para separar folhas que se encostam.
        
        Pipeline:
        1. Separar componentes conectados iniciais
        2. Para cada componente, aplicar Distance Transform
        3. Limiarizar para encontrar picos (centros de folhas)
        4. Se houver multiplos picos, aplicar Watershed para separar
        5. Retornar mascaras individuais por folha
        
        Args:
            fg_mask: Mascara binaria de foreground (255=folha, 0=fundo)
            dist_threshold_ratio: Limiar relativo ao maximo da distance transform
                                  (0.0–1.0). Mais baixo = mais agressivo na separacao.
        """
        h, w = fg_mask.shape[:2]
        min_leaf_area = h * w * 0.01  # folha deve ter pelo menos 1% da imagem

        # Passo 1: Componentes conectados iniciais (separa folhas ja isoladas)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, connectivity=8)

        leaf_masks = []

        for label_id in range(1, num_labels):  # pula 0 (fundo)
            area = stats[label_id, cv2.CC_STAT_AREA]
            if area < min_leaf_area:
                continue  # descarta ruido

            # Mascara deste componente unico
            component_mask = np.where(labels == label_id, np.uint8(255), np.uint8(0))

            # Passo 2: Distance Transform neste componente
            dist = cv2.distanceTransform(component_mask, cv2.DIST_L2, 5)
            dist_max = dist.max()

            if dist_max < 5:
                # Componente muito fino/pequeno — nao faz sentido tentar separar
                leaf_masks.append(component_mask)
                continue

            # Passo 3: Limiarizar para encontrar picos (centros provavais de cada folha)
            _, sure_fg = cv2.threshold(dist, dist_threshold_ratio * dist_max, 255, 0)
            sure_fg = np.uint8(sure_fg)

            # Encontrar marcadores nos picos
            num_markers, marker_labels = cv2.connectedComponents(sure_fg)

            if num_markers <= 2:
                # Apenas 1 pico (num_markers inclui o fundo=0) → folha unica, sem separacao
                leaf_masks.append(component_mask)
                continue

            # Passo 4: Preparar marcadores para Watershed
            # Watershed precisa: marcadores > 0 para sementes, 0 para regiao desconhecida, -1 sera fronteira
            # Dilatacao para criar "zona desconhecida" entre sure_fg e a borda
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            sure_bg = cv2.dilate(component_mask, kernel, iterations=3)
            unknown = cv2.subtract(sure_bg, sure_fg)

            # Incrementar marcadores em +1 para que o fundo=0 vire 1 e as sementes 2,3,...
            markers = marker_labels + 1
            markers[unknown == 255] = 0  # regiao desconhecida

            # Watershed precisa de uma imagem BGR de 3 canais
            # Criamos uma imagem falsa a partir do componente para o watershed operar
            component_bgr = cv2.cvtColor(component_mask, cv2.COLOR_GRAY2BGR)
            markers_ws = np.int32(markers)
            cv2.watershed(component_bgr, markers_ws)

            # Passo 5: Extrair mascaras individuais de cada regiao do watershed
            unique_markers = set(markers_ws.flatten())
            for marker_val in unique_markers:
                if marker_val <= 1:
                    continue  # 0=desconhecido, 1=fundo, -1=fronteira
                
                individual = np.where(markers_ws == marker_val, np.uint8(255), np.uint8(0))
                # Aplicar AND com a fg_mask original para nao extrapolar
                individual = cv2.bitwise_and(individual, component_mask)
                
                ind_area = cv2.countNonZero(individual)
                if ind_area >= min_leaf_area:
                    leaf_masks.append(individual)

        count = max(1, len(leaf_masks))
        return count, leaf_masks

    def _build_overlay(
        self,
        bgr: np.ndarray,
        contours_healthy: list,
        contours_symptomatic: list,
        silhouette_contour: Optional[np.ndarray],
        fg_mask: Optional[np.ndarray] = None,
        leaf_masks: list = None,
    ) -> np.ndarray:
        """Gera imagem overlay com estilo cientifico sutil."""
        overlay = bgr.copy()
        alpha_layer = bgr.copy()

        # Escurecer o fundo se a mascara de foreground estiver disponivel
        if fg_mask is not None:
            bg_mask = cv2.bitwise_not(fg_mask)
            overlay[bg_mask > 0] = (overlay[bg_mask > 0] * 0.35).astype(np.uint8)
            alpha_layer[bg_mask > 0] = (alpha_layer[bg_mask > 0] * 0.35).astype(np.uint8)

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

        # Contorno de cada folha detectada + numeracao
        if fg_mask is not None:
            fg_contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if fg_contours:
                # Desenhar contorno de TODAS as folhas (nao apenas a maior)
                for fc in fg_contours:
                    if cv2.contourArea(fc) > 100:
                        cv2.drawContours(overlay, [fc], -1, (200, 220, 255), 2, cv2.LINE_AA)

        # Numerar cada folha no centroide
        if leaf_masks and len(leaf_masks) > 1:
            for idx, lm in enumerate(leaf_masks):
                moments = cv2.moments(lm)
                if moments["m00"] > 0:
                    cx = int(moments["m10"] / moments["m00"])
                    cy = int(moments["m01"] / moments["m00"])
                    label_text = f"#{idx + 1}"
                    # Fundo do texto (pill)
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(overlay, (cx - tw//2 - 6, cy - th - 8), (cx + tw//2 + 6, cy + 8), (30, 30, 30), cv2.FILLED)
                    cv2.rectangle(overlay, (cx - tw//2 - 6, cy - th - 8), (cx + tw//2 + 6, cy + 8), (200, 220, 255), 1, cv2.LINE_AA)
                    cv2.putText(overlay, label_text, (cx - tw//2, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        return overlay
