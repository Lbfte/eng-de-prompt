# LEAF - Levantamento e Estimativa de Anomalias Foliares

Pesquisa base para software de identificação de pragas, doenças e distúrbios foliares por imagem. Documento preparado para NotebookLM. Data: 21/05/2026.

## Resumo executivo

O LEAF deve validar a imagem, segmentar a folha, localizar anomalias, medir severidade e classificar a causa provável com confiança e justificativa. A saída correta é uma triagem interpretável, não diagnóstico definitivo.

## Características eliminatórias primárias

- Tecido faltando, furos, bordas comidas ou frass favorecem herbivoria/pragas.
- Trilhas sinuosas dentro da folha favorecem minadores.
- Pó, mofo, pústulas, micélio ou esporos favorecem doença fúngica/oomiceto.
- Lesões encharcadas, halo amarelo e exsudação favorecem bactéria.
- Mosaico, deformação e enrugamento sem sinais visíveis favorecem virose ou fitotoxicidade.
- Padrões uniformes, geométricos ou distribuídos por idade da folha favorecem abiótico/cuidados.
- Foto borrada, escura ou sem folha central deve ser rejeitada.

## Fontes principais

- [R01] Embrapa - Manual Básico de Técnicas Fitopatológicas: PDF técnico em português; define sintomas, sinais, pragas e doenças no contexto fitopatológico. https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1054670/1/CartilhaManualFito21514Hermes.pdf

- [R02] APS - Plant Disease Diagnosis: Guia técnico sobre diagnóstico, sinais de agentes bióticos, micélio, esporos, frass, ovos, exsudação bacteriana e sintomas. https://www.apsnet.org/edcenter/Pages/PlantDiseaseDiagnosis.aspx

- [R03] APS - Introduction to Abiotic Disorders in Plants: Base para diferenciar distúrbios não infecciosos de doenças e pragas. https://www.apsnet.org/edcenter/Pages/Abiotic.aspx

- [R04] MSU Extension - Signs and symptoms of plant disease: fungal, viral or bacterial: Resumo prático de sinais e sintomas de doenças fúngicas, bacterianas e virais. https://www.canr.msu.edu/news/signs_and_symptoms_of_plant_disease_is_it_fungal_viral_or_bacterial

- [R05] Iowa State University Extension - Nutrient Deficiencies and Application Injuries in Field Crops: PDF com padrões de deficiências nutricionais e lesões por aplicação/cultivo. https://crops.extension.iastate.edu/files/article/nutrientdeficiency.pdf

- [R06] University of Minnesota Extension - Leafminers in home gardens: Guia de sintomas visuais de minadores: minas sinuosas e manchas nas folhas. https://extension.umn.edu/yard-and-garden-insects/leafminers

- [R07] Utah State University Extension - Leafminers of Vegetable Crops: PDF técnico sobre dano de minadores, frass, túneis serpentinados, pontuações e impacto na fotossíntese. https://extension.usu.edu/planthealth/research/leafminers-vegetables.pdf

- [R08] Machado et al. - BioLeaf: mobile app to measure foliar damage caused by insect herbivory: Artigo sobre medição automática de dano foliar por herbivoria com segmentação de Otsu e curvas de Bezier. https://arxiv.org/abs/1609.08004

- [R09] Elliott et al. - Comparison of ImageJ and machine-learning image analysis for cassava bacterial blight: Artigo de Plant Methods comparando ImageJ e SVM/few-shot para severidade de lesões de mandioca. https://link.springer.com/article/10.1186/s13007-022-00906-x

- [R10] R4PDE - Measuring foliar severity: Material didático-científico sobre cálculo de severidade por segmentação de pixels: doente, saudável e fundo. https://r4pde.net/data-actual-severity

- [R11] TensorFlow Datasets - PlantVillage: Catálogo do dataset PlantVillage: imagens saudáveis/doentes por espécie e doença. https://www.tensorflow.org/datasets/catalog/plant_village

- [R12] PlantDoc Dataset - GitHub: Dataset com imagens reais para detecção visual de doenças de plantas. https://github.com/pratikkayal/PlantDoc-Dataset

- [R13] TensorFlow Datasets - Cassava: Dataset de mandioca com folhas saudáveis e quatro condições/danos/doenças. https://www.tensorflow.org/datasets/catalog/cassava

- [R14] Pacal et al. - Systematic review of deep learning techniques for plant diseases: Revisão sistemática de 160 artigos entre 2020 e 2024 sobre classificação, detecção e segmentação. https://link.springer.com/article/10.1007/s10462-024-10944-7

- [R15] Siddiqua et al. - Evaluating Plant Disease Detection Mobile Applications: Avaliação de 17 aplicativos móveis de diagnóstico vegetal, incluindo Plantix e Leaf Doctor. https://www.mdpi.com/2073-4395/12/8/1869

- [R16] Quantitative Plant - Assess 2.0: Base sobre software de quantificação de doença, área foliar, lesão e porcentagem de doença. https://www.quantitative-plant.org/software/assess

- [R17] Quantitative Plant - LAMINA: Ferramenta para quantificar área, forma e área ausente em folhas. https://www.quantitative-plant.org/software/lamina

- [R18] CGIAR Big Data - Plantix case study: Estudo de caso sobre Plantix, geotagging, base de imagens e escala de uso. https://bigdata.cgiar.org/digital-intervention/plant-disease-diagnosis-using-artificial-intelligence-a-case-study-on-plantix/

- [R19] Richter & Kim - Comprehensive benchmark of transfer learning on open datasets: Benchmark recente de CNNs em datasets abertos; alerta sobre falta de consenso e generalização campo/laboratório. https://www.nature.com/articles/s41598-025-03235-w

- [R20] Krishna - Plant Leaf Disease Detection Using Deep Learning: A Multi-Dataset Approach: Estudo 2025 com PlantDoc + imagens web; avalia EfficientNet, ResNet e DenseNet em condições mais diversas. https://www.mdpi.com/2571-8800/8/1/4

- [R21] Frontiers in Plant Science - Review of plant leaf disease identification by deep learning algorithms: Revisão 2025 com panorama de bases de dados e algoritmos recentes. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1637241/full
