import customtkinter as ctk
import tkinter.filedialog as filedialog
import threading
from ui.theme import Fonts, Colors, Layout
from ui.components.preview_card import PreviewCard
from ui.components.metric_card import MetricCard
from ui.components.summary_card import SummaryCard
from ui.state import app_state
from image_processor import ImageProcessor, ColorMode, HullMethod, HSVRange, LABRange
from metrics import Metrics
import time
import os

# Helper logic from the original streamlit app
def label_from_pct(value: float) -> str:
    if value >= 25: return "Alta"
    if value >= 8: return "Moderada"
    return "Baixa"

def severity_from_pct(value: float):
    if value >= 55: return "Crítica", Colors.SEVERITY_RED
    if value >= 25: return "Moderada", Colors.SEVERITY_ORANGE
    return "Baixa", Colors.SEVERITY_GREEN

def clamp_pct(value: float) -> float:
    try: return max(0.0, min(100.0, float(value)))
    except Exception: return 0.0
    
def estimate_confidence(seg_result, leaf_m) -> float:
    if seg_result is None or leaf_m is None or leaf_m.error: return 92.0
    if leaf_m.pixels_leaf <= 0 or leaf_m.area_original_px <= 0: return 38.0
    coverage = min(1.0, leaf_m.pixels_leaf / max(1, seg_result.original_bgr.shape[0] * seg_result.original_bgr.shape[1]))
    contour_bonus = min(20, len(seg_result.contours_healthy) * 2 + len(seg_result.contours_symptomatic))
    confidence = 62 + coverage * 18 + contour_bonus
    return clamp_pct(confidence)

class DashboardPage(ctk.CTkFrame):
    PAGE_ID = "dashboard"
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.grid_rowconfigure(0, weight=3) # Upload + Preview area
        self.grid_rowconfigure(1, weight=2) # Metrics area
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=2) 
        
        # --- Linha Superior ---
        # Area Esquerda (Upload + Status)
        self.left_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15), pady=(0, 15))
        
        self.upload_btn = ctk.CTkButton(
            self.left_panel, 
            text="⇧ Enviar imagens de folhas", 
            font=Fonts.body_bold(),
            height=50,
            command=self._on_upload,
            fg_color=Colors.SURFACE,
            text_color=Colors.PRIMARY,
            border_width=2,
            border_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_SOFT
        )
        self.upload_btn.pack(fill="x", pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(self.left_panel, text="Nenhuma imagem selecionada.", text_color=Colors.MUTED)
        self.status_label.pack(anchor="w")
        
        self.analyze_btn = ctk.CTkButton(
            self.left_panel,
            text="⌁ Analisar folha",
            font=Fonts.header3(),
            height=60,
            command=self._on_analyze,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_DARK
        )
        self.analyze_btn.pack(fill="x", pady=20)
        
        self.progress = ctk.CTkProgressBar(self.left_panel, progress_color=Colors.PRIMARY)
        self.progress.pack(fill="x")
        self.progress.set(0)
        self.progress.pack_forget()
        
        self.log_text = ctk.CTkTextbox(self.left_panel, height=200, fg_color=Colors.SURFACE, text_color=Colors.MUTED, font=Fonts.small())
        self.log_text.pack(fill="both", expand=True, pady=(20, 0))
        self.log_text.insert("0.0", "Logs da análise:\n")
        self.log_text.configure(state="disabled")
        
        # Area Direita (Preview)
        self.preview_card = PreviewCard(self)
        self.preview_card.grid(row=0, column=1, sticky="nsew", pady=(0, 15))
        
        # --- Linha Inferior (Métricas) ---
        self.metrics_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        # Grid para 3 metric cards e 1 summary card grande
        self.metrics_panel.grid_rowconfigure(0, weight=1)
        self.metrics_panel.grid_columnconfigure(0, weight=1)
        self.metrics_panel.grid_columnconfigure(1, weight=1)
        self.metrics_panel.grid_columnconfigure(2, weight=1)
        self.metrics_panel.grid_columnconfigure(3, weight=3) # summary card
        
        # Cards (usamos light mode colors pois CTkFrame as gerencia)
        self.card_herb = MetricCard(self.metrics_panel, "Herbivoria", "🐛", Colors.YELLOW, "#FEF7D4")
        self.card_herb.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.card_fungi = MetricCard(self.metrics_panel, "Fungos", "⌬", Colors.BLUE, "#EAF3FB")
        self.card_fungi.grid(row=0, column=1, sticky="nsew", padx=10)
        
        self.card_disease = MetricCard(self.metrics_panel, "Doenças", "☇", Colors.PURPLE, "#F5EAFB")
        self.card_disease.grid(row=0, column=2, sticky="nsew", padx=10)
        
        self.card_summary = SummaryCard(self.metrics_panel)
        self.card_summary.grid(row=0, column=3, sticky="nsew", padx=(10, 0))
        
        self.selected_files = []
        
    def _log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_upload(self):
        filepaths = filedialog.askopenfilenames(
            title="Selecione imagens foliares",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.tiff *.webp")]
        )
        if filepaths:
            self.selected_files = filepaths
            self.status_label.configure(text=f"{len(filepaths)} imagem(ns) selecionada(s)")
            self._log(f"{len(filepaths)} imagens carregadas.")
            
    def _get_processor(self):
        c_mode = ColorMode.CIELAB if app_state["color_mode"] == "CIELAB" else ColorMode.HSV
        h_method = HullMethod.MORPHOLOGICAL_CLOSURE if app_state["hull_method"] == "Fechamento Morfologico" else HullMethod.CONVEX_HULL
        
        return ImageProcessor(
            color_mode=c_mode,
            hull_method=h_method,
            green_hsv=HSVRange.from_sliders(*app_state["hsv_green"]),
            symptomatic_hsv=HSVRange.from_sliders(*app_state["hsv_symp"]),
            green_lab=LABRange.from_sliders(*app_state["lab_green"]),
            symptomatic_lab=LABRange.from_sliders(*app_state["lab_symp"]),
            min_contour_area=app_state["min_area"],
            morph_kernel_size=app_state["morph_kernel_size"],
            use_background_removal=app_state["use_background_removal"],
            grabcut_iterations=app_state["grabcut_iterations"],
        )

    def _on_analyze(self):
        if not self.selected_files:
            self._log("Erro: Nenhuma imagem selecionada.")
            return
            
        self.analyze_btn.configure(state="disabled")
        self.upload_btn.configure(state="disabled")
        self.progress.pack(fill="x")
        self.progress.set(0)
        self.preview_card.show_analyzing()
        
        thread = threading.Thread(target=self._process_batch)
        thread.start()
        
    def _process_batch(self):
        processor = self._get_processor()
        total = len(self.selected_files)
        
        batch_metrics = []
        batch_overlays = []
        
        # Para salvar a ultima analise
        last_seg = None
        last_m = None
        
        for i, filepath in enumerate(self.selected_files):
            try:
                filename = os.path.basename(filepath)
                self.after(0, lambda f=filename, idx=i, t=total: self._log(f"[{idx+1}/{t}] Processando {f}..."))
                
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                    
                seg_result = processor.process(img_bytes)
                
                # Log de quantidade de folhas detectadas
                lc = seg_result.leaf_count
                if lc > 1:
                    self.after(0, lambda c=lc: self._log(f"   → {c} folhas detectadas na imagem."))
                
                # Se múltiplas folhas, gerar métricas individuais por folha
                if seg_result.leaf_masks and len(seg_result.leaf_masks) > 1:
                    for leaf_idx, leaf_mask in enumerate(seg_result.leaf_masks):
                        leaf_name = f"{filename} [Folha #{leaf_idx + 1}]"
                        
                        # Criar máscaras filtradas para esta folha individual
                        from image_processor import SegmentationResult
                        import cv2 as _cv2
                        individual_healthy = _cv2.bitwise_and(seg_result.mask_healthy, leaf_mask)
                        individual_symptomatic = _cv2.bitwise_and(seg_result.mask_symptomatic, leaf_mask)
                        individual_leaf = _cv2.bitwise_or(individual_healthy, individual_symptomatic)
                        
                        # Reconstruir silhueta individual para esta folha
                        individual_hull, _ = processor._compute_convex_hull(individual_leaf, seg_result.original_bgr.shape[:2])
                        
                        individual_seg = SegmentationResult(
                            original_bgr=seg_result.original_bgr,
                            color_converted=seg_result.color_converted,
                            mask_healthy=individual_healthy,
                            mask_symptomatic=individual_symptomatic,
                            mask_leaf=individual_leaf,
                            mask_background=_cv2.bitwise_not(individual_leaf),
                            rebuilt_silhouette_mask=individual_hull,
                            contours_healthy=seg_result.contours_healthy,
                            contours_symptomatic=seg_result.contours_symptomatic,
                            color_mode=seg_result.color_mode,
                            reconstruction_method=seg_result.reconstruction_method,
                        )
                        
                        leaf_m = Metrics.compute(individual_seg, leaf_name, app_state["ppm"])
                        batch_metrics.append(leaf_m)
                        
                        self.after(0, lambda n=leaf_name, h=leaf_m.herbivory_pct, s=leaf_m.disease_severity_pct:
                            self._log(f"   → {n}: Herb={h:.1f}% Sev={s:.1f}%"))
                        
                        # Histórico individual
                        app_state["analysis_history"].append({
                            "Imagem": leaf_name,
                            "Herbivoria": f"{leaf_m.herbivory_pct:.1f}%",
                            "Severidade": f"{leaf_m.disease_severity_pct:.1f}%",
                            "Método": leaf_m.reconstruction_method,
                        })
                        
                        last_m = leaf_m
                else:
                    # Imagem com folha unica — fluxo original
                    leaf_m = Metrics.compute(seg_result, filename, app_state["ppm"])
                    batch_metrics.append(leaf_m)
                    
                    app_state["analysis_history"].append({
                        "Imagem": filename,
                        "Herbivoria": f"{leaf_m.herbivory_pct:.1f}%",
                        "Severidade": f"{leaf_m.disease_severity_pct:.1f}%",
                        "Método": leaf_m.reconstruction_method,
                    })
                    
                    last_m = leaf_m
                
                # Overlay (sempre a imagem completa)
                if seg_result.overlay is not None:
                    batch_overlays.append(seg_result.overlay)
                else:
                    batch_overlays.append(None)
                    
                last_seg = seg_result
                    
                # Atualizar Progresso
                prog = (i + 1) / total
                self.after(0, lambda p=prog: self.progress.set(p))
                
            except Exception as e:
                self.after(0, lambda err=str(e): self._log(f"Erro na imagem {i}: {err}"))
        
        app_state["batch_metrics"] = batch_metrics
        app_state["batch_overlays"] = batch_overlays
        
        # Mostrar preview
        if batch_overlays and batch_overlays[-1] is not None:
            last_overlay = batch_overlays[-1]
            self.after(0, lambda img=last_overlay: self.preview_card.show_result(img))
        
        # Atualizar Cards
        self.after(0, lambda bm=batch_metrics, ls=last_seg, lm=last_m: self._update_cards(bm, ls, lm))
        self.after(0, self._finish_analysis)
        
    def _update_cards(self, batch, last_seg, last_m):
        if not batch: return
        
        if len(batch) > 1:
            agg = Metrics.aggregate(batch)
            herb_pct = clamp_pct(agg.get("herbivoria_media_%", 0))
            sev_media = agg.get("severidade_media_%", 0)
            fungi_pct = clamp_pct(sev_media * 0.60)
            disease_pct = clamp_pct(sev_media * 0.40)
            total_affected = clamp_pct(herb_pct + sev_media)
            valid_ratio = agg.get("imagens_validas", 0) / max(1, agg.get("total_imagens", 1))
            confidence = clamp_pct(valid_ratio * 100)
        elif last_m is not None:
            herb_pct = clamp_pct(last_m.herbivory_pct)
            fungi_pct = clamp_pct(last_m.disease_severity_pct * 0.60)
            disease_pct = clamp_pct(last_m.disease_severity_pct * 0.40)
            total_affected = clamp_pct(herb_pct + last_m.disease_severity_pct)
            confidence = estimate_confidence(last_seg, last_m)
        else:
            return

        self.card_herb.update_data(herb_pct, label_from_pct(herb_pct))
        self.card_fungi.update_data(fungi_pct, label_from_pct(fungi_pct))
        self.card_disease.update_data(disease_pct, label_from_pct(disease_pct))
        
        sev_label, sev_color = severity_from_pct(total_affected)
        self.card_summary.update_data(total_affected, sev_label, sev_color, confidence)

    def _finish_analysis(self):
        self.analyze_btn.configure(state="normal")
        self.upload_btn.configure(state="normal")
        self.progress.pack_forget()
        self._log("Processamento em lote finalizado.")
        
        # Persistir histórico em disco
        from ui.state import save_history
        save_history()
