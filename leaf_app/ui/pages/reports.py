import customtkinter as ctk
import tkinter.filedialog as filedialog
import pandas as pd
import json
import io
import cv2
from PIL import Image
from ui.theme import Fonts, Colors, Layout
from ui.state import app_state
from metrics import Metrics

class ReportsPage(ctk.CTkScrollableFrame):
    PAGE_ID = "reports"
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20), padx=20)
        
        ctk.CTkLabel(self.header_frame, text="Relatórios Consolidados", font=Fonts.header2(), text_color=Colors.INK).pack(anchor="w")
        
        # Content container
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20)
        
        self.refresh()

    def refresh(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        batch = app_state.get("batch_metrics", [])
        if not batch:
            self._render_empty()
            return
            
        agg = Metrics.aggregate(batch)
        
        # 1. Metricas Agregadas
        metrics_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=(0, 20))
        metrics_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        def add_metric_box(parent, row, col, label, value, val_color=Colors.INK):
            box = ctk.CTkFrame(parent, fg_color=Colors.SURFACE, corner_radius=10, border_width=1, border_color=Colors.LINE)
            box.grid(row=row, column=col, sticky="nsew", padx=5)
            ctk.CTkLabel(box, text=label, font=Fonts.small(), text_color=Colors.MUTED).pack(anchor="center", pady=(15, 5))
            ctk.CTkLabel(box, text=str(value), font=Fonts.header2(), text_color=val_color).pack(anchor="center", pady=(0, 15))

        add_metric_box(metrics_frame, 0, 0, "Folhas Analisadas", agg.get("total_imagens", 0))
        add_metric_box(metrics_frame, 0, 1, "Herbivoria Média", f"{agg.get('herbivoria_media_%', 0):.1f}%", Colors.YELLOW)
        add_metric_box(metrics_frame, 0, 2, "Severidade Média", f"{agg.get('severidade_media_%', 0):.1f}%", Colors.PURPLE)
        
        # 2. Botoes de exportacao
        export_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        export_frame.pack(fill="x", pady=(0, 30))
        
        btn_csv = ctk.CTkButton(export_frame, text="📥 Baixar CSV Lote", fg_color=Colors.SURFACE, text_color=Colors.PRIMARY, border_width=1, border_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_SOFT, command=self._export_csv)
        btn_csv.pack(side="left", padx=(0, 10))
        
        btn_json = ctk.CTkButton(export_frame, text="📥 Baixar JSON Metadados", fg_color=Colors.SURFACE, text_color=Colors.PRIMARY, border_width=1, border_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_SOFT, command=self._export_json)
        btn_json.pack(side="left")
        
        # 3. Galeria (Thumbnails)
        ctk.CTkLabel(self.content_frame, text="Galeria do lote processado", font=Fonts.body_bold(), text_color=Colors.INK).pack(anchor="w", pady=(0, 10))
        self._render_gallery(batch)

    def _render_empty(self):
        empty_box = ctk.CTkFrame(self.content_frame, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE)
        empty_box.pack(fill="both", expand=True, pady=20)
        ctk.CTkLabel(empty_box, text="📊", font=(Fonts.FAMILY, 40)).pack(pady=(40, 10))
        ctk.CTkLabel(empty_box, text="Nenhum relatório disponível", font=Fonts.body_bold(), text_color=Colors.INK).pack()
        ctk.CTkLabel(empty_box, text="Realize análises no menu Início para gerar os resultados e visualizá-los aqui.", font=Fonts.small(), text_color=Colors.MUTED).pack(pady=(5, 40))

    def _render_gallery(self, batch_metrics):
        gallery_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        gallery_frame.pack(fill="x")
        
        overlays = app_state.get("batch_overlays", [])
        
        cols_per_row = 4
        limit = min(12, len(batch_metrics)) # Exibe ate 12 thumbnails para nao engasgar muito
        
        for i in range(cols_per_row):
            gallery_frame.grid_columnconfigure(i, weight=1)
            
        for i in range(limit):
            row = i // cols_per_row
            col = i % cols_per_row
            
            card = ctk.CTkFrame(gallery_frame, fg_color=Colors.SURFACE, corner_radius=8)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            
            m = batch_metrics[i]
            overlay_bgr = overlays[i] if i < len(overlays) else None
            
            if overlay_bgr is not None:
                # Converter para thumbnail usando opencv resize rapido
                rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                target_w = 200
                target_h = int((target_w/w)*h)
                rgb_small = cv2.resize(rgb, (target_w, target_h), interpolation=cv2.INTER_AREA)
                pil_img = Image.fromarray(rgb_small)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 160))
                
                img_lbl = ctk.CTkLabel(card, text="", image=ctk_img)
                img_lbl.image = ctk_img
                img_lbl.pack(pady=(10, 5))
            
            title = m.filename if len(m.filename) < 15 else m.filename[:12]+"..."
            ctk.CTkLabel(card, text=title, font=Fonts.body_bold()).pack(pady=(0, 2))
            ctk.CTkLabel(card, text=f"🐛 {m.herbivory_pct:.1f}%  |  ☇ {m.disease_severity_pct:.1f}%", font=Fonts.small(), text_color=Colors.MUTED).pack(pady=(0, 10))
            
        if len(batch_metrics) > limit:
            ctk.CTkLabel(gallery_frame, text=f"... e mais {len(batch_metrics) - limit} imagens.", text_color=Colors.MUTED, font=Fonts.small()).grid(row=row+1, column=0, columnspan=cols_per_row, pady=10)

    def _export_csv(self):
        batch = app_state.get("batch_metrics", [])
        if not batch: return
        filepath = filedialog.asksaveasfilename(title="Salvar Resultados CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="leaf_resultados_lote.csv")
        if filepath:
            df = pd.DataFrame([m.to_dict() for m in batch])
            df.to_csv(filepath, index=False, encoding="utf-8-sig")

    def _export_json(self):
        batch = app_state.get("batch_metrics", [])
        if not batch: return
        filepath = filedialog.asksaveasfilename(title="Salvar Metadados JSON", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="leaf_metadados_lote.json")
        if filepath:
            agg_data = Metrics.aggregate(batch)
            # Para não recriar a estrutura de processing parameters inteira de forma complexa, pegamos o setup base
            class ParamStub:
                def to_dict(self): return {"info": "Extracted from state", "color_mode": app_state["color_mode"], "ppm": app_state["ppm"]}
            meta = Metrics.export_metadata(ParamStub(), agg_data)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4, ensure_ascii=False)
