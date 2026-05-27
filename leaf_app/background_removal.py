"""
LEAF - Módulo de Remoção de Fundo
Classe BackgroundRemover: isola a folha do fundo via GrabCut (OpenCV) com ROI automático.
Algoritmo clássico de segmentação foreground/background baseado em GMM — sem GPU, sem redes neurais.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class BackgroundRemover:
    """
    Isola a folha do fundo usando GrabCut + detecção automática de ROI.

    Pipeline:
    1. Blur gaussiano para suavizar ruído
    2. Threshold adaptativo + morfologia para encontrar o maior objeto
    3. Bounding box desse objeto = ROI inicial do GrabCut
    4. GrabCut iterativo para separação foreground/background
    5. Refinamento opcional com segunda passada
    """

    def __init__(
        self,
        grabcut_iterations: float = 3.0,
        blur_kernel: int = 5,
        roi_margin_pct: float = 0.02,
    ):
        """
        Args:
            grabcut_iterations: Nível do GrabCut (1.0–10.0). Arredondado para int internamente.
                                Mais alto = mais preciso e mais lento.
            blur_kernel: Tamanho do kernel para o blur gaussiano de pré-processamento.
            roi_margin_pct: Margem extra em torno do bounding box automático (percentual do tamanho da imagem).
        """
        self.grabcut_iterations = max(1, min(10, int(round(grabcut_iterations))))
        self.blur_kernel = blur_kernel if blur_kernel % 2 != 0 else blur_kernel + 1
        self.roi_margin_pct = roi_margin_pct

    def remove(self, bgr: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Processa uma imagem BGR e retorna a máscara de foreground (folha).

        Returns:
            (fg_mask, success)
            - fg_mask: máscara uint8 com 255 = foreground (folha), 0 = fundo
            - success: True se o GrabCut convergiu com um objeto válido
        """
        h, w = bgr.shape[:2]

        # Passo 1: Detectar ROI automaticamente via contorno do maior objeto
        roi_rect = self._auto_roi(bgr, h, w)

        if roi_rect is None:
            # Fallback: usar 90% central da imagem como ROI
            margin_h = int(h * 0.05)
            margin_w = int(w * 0.05)
            roi_rect = (margin_w, margin_h, w - 2 * margin_w, h - 2 * margin_h)

        # Passo 2: Executar GrabCut
        fg_mask = self._run_grabcut(bgr, roi_rect)

        # Passo 3: Pós-processamento morfológico para limpar bordas
        fg_mask = self._postprocess(fg_mask)

        success = cv2.countNonZero(fg_mask) > (h * w * 0.01)  # Pelo menos 1% da imagem
        return fg_mask, success

    def _auto_roi(self, bgr: np.ndarray, h: int, w: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Encontra automaticamente TODOS os objetos significativos (folhas) usando
        threshold + contornos e retorna o bounding box combinado que engloba todos.
        Retorna (x, y, width, height) com margem extra, ou None se falhar.
        """
        # Blur para reduzir ruído de textura
        blurred = cv2.GaussianBlur(bgr, (self.blur_kernel, self.blur_kernel), 0)

        # Converter para escala de cinza
        gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

        # Threshold de Otsu para separação inicial
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morfologia para fechar buracos e remover ruído pequeno
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        # Também testar a versão invertida (caso o fundo seja mais claro que a folha)
        thresh_inv = cv2.bitwise_not(thresh)

        # Limiar mínimo: contornos menores que 1% da imagem são ruído
        min_contour_area = h * w * 0.01

        best_contours = []
        best_total_area = 0

        for candidate in [thresh, thresh_inv]:
            contours, _ = cv2.findContours(candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue

            # Filtrar contornos significativos (possíveis folhas)
            significant = [c for c in contours if cv2.contourArea(c) >= min_contour_area]
            total_area = sum(cv2.contourArea(c) for c in significant)

            if total_area > best_total_area:
                best_total_area = total_area
                best_contours = significant

        if not best_contours:
            return None

        # Calcular o bounding box COMBINADO que engloba todos os contornos significativos
        all_points = np.vstack(best_contours)
        x, y, bw, bh = cv2.boundingRect(all_points)

        # Aplicar margem extra para garantir que o GrabCut "veja" o fundo ao redor
        margin_x = int(w * self.roi_margin_pct)
        margin_y = int(h * self.roi_margin_pct)

        x = max(1, x - margin_x)
        y = max(1, y - margin_y)
        bw = min(w - x - 2, bw + 2 * margin_x)
        bh = min(h - y - 2, bh + 2 * margin_y)

        return (x, y, bw, bh)

    def _run_grabcut(self, bgr: np.ndarray, roi_rect: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Executa o algoritmo GrabCut e retorna a máscara binária de foreground.
        """
        h, w = bgr.shape[:2]

        # Inicializar máscara e modelos internos do GrabCut
        gc_mask = np.zeros((h, w), dtype=np.uint8)
        bgd_model = np.zeros((1, 65), dtype=np.float64)
        fgd_model = np.zeros((1, 65), dtype=np.float64)

        try:
            # Primeira passada: ROI retangular automático
            cv2.grabCut(
                bgr,
                gc_mask,
                roi_rect,
                bgd_model,
                fgd_model,
                self.grabcut_iterations,
                cv2.GC_INIT_WITH_RECT,
            )

            # Converter máscara do GrabCut para binária
            # GC_FGD (1) = definitivo foreground, GC_PR_FGD (3) = provável foreground
            fg_mask = np.where(
                (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD),
                np.uint8(255),
                np.uint8(0),
            )
            return fg_mask

        except cv2.error:
            # Se o GrabCut falhar (ex: ROI inválido), retornar máscara cheia
            return np.ones((h, w), dtype=np.uint8) * 255

    def _postprocess(self, fg_mask: np.ndarray) -> np.ndarray:
        """
        Pós-processamento morfológico: fecha buracos internos e suaviza bordas.
        Mantém todos os componentes conectados acima de um limiar mínimo de área,
        permitindo que múltiplas folhas na mesma imagem sejam preservadas.
        """
        h, w = fg_mask.shape[:2]

        # Fechar buracos internos pequenos
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)

        # Remover ruído (pequenas manchas de foreground espúrias)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open, iterations=1)

        # Manter todos os componentes com área >= 1% da imagem total
        min_component_area = h * w * 0.01
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, connectivity=8)
        if num_labels <= 1:
            return fg_mask

        # Construir máscara mantendo TODOS os componentes significativos
        cleaned_mask = np.zeros_like(fg_mask)
        for label_id in range(1, num_labels):  # pula 0 (fundo)
            area = stats[label_id, cv2.CC_STAT_AREA]
            if area >= min_component_area:
                cleaned_mask[labels == label_id] = 255

        return cleaned_mask
