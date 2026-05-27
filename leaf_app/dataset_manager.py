"""
LEAF - Gerenciador do Dataset Kaggle de Doenças Foliares
Baixa, gerencia o cache e fornece acesso organizado ao dataset
"New Plant Diseases Dataset" (vipoooool) via kagglehub.
Utiliza apenas a pasta valid/ (~350MB) para economia de espaço.
"""

import os
import glob
from typing import List, Tuple, Optional


# Constantes
DATASET_ID = "vipoooool/new-plant-diseases-dataset"
VALID_SUBDIR = os.path.join("New Plant Diseases Dataset(Augmented)", "New Plant Diseases Dataset(Augmented)", "valid")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")


class DatasetManager:
    """
    Gerencia o download e acesso ao dataset de doenças foliares do Kaggle.
    O kagglehub faz cache local automático — download só ocorre na primeira vez.
    """

    def __init__(self):
        self._dataset_path: Optional[str] = None
        self._valid_path: Optional[str] = None
        self._categories: List[str] = []
        self._is_downloaded = False

    @property
    def is_downloaded(self) -> bool:
        return self._is_downloaded

    @property
    def valid_path(self) -> Optional[str]:
        return self._valid_path

    def download(self, progress_callback=None) -> str:
        """
        Baixa o dataset (ou usa cache local se já baixado).
        
        Args:
            progress_callback: Função opcional chamada com mensagens de progresso.
            
        Returns:
            Caminho absoluto para a pasta raiz do dataset.
        """
        import kagglehub

        if progress_callback:
            progress_callback("Verificando cache do dataset...")

        self._dataset_path = kagglehub.dataset_download(DATASET_ID)

        # Localizar a pasta valid/
        candidate = os.path.join(self._dataset_path, VALID_SUBDIR)
        if os.path.isdir(candidate):
            self._valid_path = candidate
        else:
            # Fallback: tentar buscar qualquer pasta 'valid' na árvore
            for root, dirs, _ in os.walk(self._dataset_path):
                if "valid" in dirs:
                    self._valid_path = os.path.join(root, "valid")
                    break

        if self._valid_path is None:
            raise FileNotFoundError(
                f"Pasta 'valid' não encontrada no dataset em: {self._dataset_path}"
            )

        # Cachear categorias
        self._categories = sorted([
            d for d in os.listdir(self._valid_path)
            if os.path.isdir(os.path.join(self._valid_path, d))
        ])

        self._is_downloaded = True

        if progress_callback:
            progress_callback(f"Dataset pronto! {len(self._categories)} categorias disponíveis.")

        return self._dataset_path

    def get_categories(self) -> List[str]:
        """Retorna lista de categorias (subpastas dentro de valid/)."""
        return self._categories

    def get_category_display_name(self, category: str) -> str:
        """
        Formata o nome da categoria para exibição.
        Ex: 'Apple___Apple_scab' → 'Apple - Apple scab'
        """
        parts = category.split("___")
        if len(parts) == 2:
            plant = parts[0].replace("_", " ")
            disease = parts[1].replace("_", " ")
            return f"{plant} - {disease}"
        return category.replace("_", " ")

    def get_images(self, category: str, limit: int = 0) -> List[str]:
        """
        Retorna caminhos absolutos das imagens em uma categoria.
        
        Args:
            category: Nome da subpasta (ex: 'Apple___Apple_scab')
            limit: Máximo de imagens a retornar (0 = todas)
            
        Returns:
            Lista de caminhos absolutos para os arquivos de imagem.
        """
        if self._valid_path is None:
            return []

        cat_path = os.path.join(self._valid_path, category)
        if not os.path.isdir(cat_path):
            return []

        images = [
            os.path.join(cat_path, f)
            for f in sorted(os.listdir(cat_path))
            if f.lower().endswith(IMAGE_EXTENSIONS)
        ]

        if limit > 0:
            images = images[:limit]

        return images

    def get_image_count(self, category: str) -> int:
        """Retorna a quantidade de imagens em uma categoria."""
        if self._valid_path is None:
            return 0
        cat_path = os.path.join(self._valid_path, category)
        if not os.path.isdir(cat_path):
            return 0
        return sum(1 for f in os.listdir(cat_path) if f.lower().endswith(IMAGE_EXTENSIONS))

    def get_summary(self) -> List[Tuple[str, str, int]]:
        """
        Retorna uma lista de tuplas (categoria_raw, nome_exibicao, qtd_imagens)
        para todas as categorias.
        """
        return [
            (cat, self.get_category_display_name(cat), self.get_image_count(cat))
            for cat in self._categories
        ]
