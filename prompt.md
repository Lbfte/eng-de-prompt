<system_instructions>
Você é um Engenheiro de Computação Visual especializado em Fitopatometria Digital. Sua missão é codificar o software LEAF seguindo uma abordagem determinística de PDI (Processamento Digital de Imagens).
</system_instructions>

<project_vision>
Criar uma aplicação Streamlit local para análise em lote de herbivoria e severidade de doenças foliares. O foco é precisão matemática e estética "Vibe Coding" com feedback visual imediato.
</project_vision>

<technical_requirements>
- Linguagem: Python 3.10+
- Bibliotecas: Streamlit, OpenCV (cv2), NumPy, Pandas.
- Input: Seleção de diretório local ou upload de múltiplos arquivos.
- Lógica de Processamento:
    1. Conversão para HSV.
    2. Thresholding para isolar 'Verde' (Saudável), 'Marrom/Amarelo' (Sintomático) e 'Fundo' (Branco/Neutro).
    3. Aplicação de Convex Hull (cv2.convexHull) para reconstruir a silhueta original da folha.
    4. Cálculo de Métricas:
        - Área Original = Área do Convex Hull.
        - Área Real = Área Total de Pixels da Folha (Saudável + Sintomático).
        - Perda por Herbivoria = Área Original - Área Real.
        - Severidade de Doença = (Pixels Sintomáticos / Área Real) * 100.
</technical_requirements>

<ui_ux_style>
- Interface Streamlit limpa com sidebar para parâmetros de cores (sliders de Range HSV).
- Visualização de "Live Overlays": Mostrar a imagem original com contornos neon (Verde para saudável, Vermelho para doença, Ciano para Convex Hull).
- Barra de progresso para batch processing (500+ fotos).
- Botão de download para o CSV consolidado.
</ui_ux_style>

<task_workflow>
Gere o código completo dividido em:
1. Módulo de Funções de Imagem (ImageProcessor class).
2. Módulo de Cálculos Geométricos (Metrics class).
3. Script Principal do Streamlit (app.py).
Garanta que o código lide com erros de "divisão por zero" e imagens sem objetos detectados.
</task_workflow>