# LEAF — Levantamento e Estimativa de Anomalias Foliares

Dashboard profissional em Streamlit para análise de imagens de folhas, com interface inspirada em software AgriTech/SaaS e pipeline de PDI para estimativa de herbivoria e sintomas foliares.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```text
leaf_app/
├── app.py
├── image_processor.py
├── metrics.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── docs/
    ├── LEAF_pesquisa_base_NotebookLM.md
    ├── prompts.md
    └── instrucoes.md
```

## Observação

O LEAF é um protótipo acadêmico de triagem visual. Os resultados representam hipóteses e estimativas calculadas por processamento de imagem, não diagnóstico fitossanitário definitivo.
