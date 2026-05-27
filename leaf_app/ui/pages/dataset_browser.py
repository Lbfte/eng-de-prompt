"""
LEAF - Página de Navegação do Dataset Kaggle
Permite baixar, navegar categorias e selecionar imagens do dataset
"New Plant Diseases Dataset" para análise no Dashboard.
"""

import customtkinter as ctk
import threading
import os
from PIL import Image, ImageTk
from ui.theme import Fonts, Colors, Layout
from ui.state import app_state
from dataset_manager import DatasetManager


class DatasetBrowserPage(ctk.CTkScrollableFrame):
    PAGE_ID = "dataset"

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self._manager = DatasetManager()
        self._thumbnail_refs = []  # manter referências para GC não limpar
        self._selected_paths = set()
        self._checkboxes = {}

        # ── Header ──
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            self.header, text="Banco de Imagens", font=Fonts.header2(), text_color=Colors.INK
        ).pack(anchor="w")
        ctk.CTkLabel(
            self.header,
            text="Dataset Kaggle — New Plant Diseases (38 categorias · ~87K imagens)",
            font=Fonts.body(), text_color=Colors.MUTED,
        ).pack(anchor="w")

        # ── Download area ──
        self.download_frame = ctk.CTkFrame(self, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS)
        self.download_frame.pack(fill="x", pady=(0, 20))

        self.download_btn = ctk.CTkButton(
            self.download_frame,
            text="⬇ Baixar Dataset (válida · ~350 MB)",
            font=Fonts.body_bold(),
            height=45,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_DARK,
            command=self._on_download,
        )
        self.download_btn.pack(padx=20, pady=15)

        self.download_status = ctk.CTkLabel(
            self.download_frame, text="", font=Fonts.small(), text_color=Colors.MUTED
        )
        self.download_status.pack(padx=20, pady=(0, 10))

        self.download_progress = ctk.CTkProgressBar(
            self.download_frame, progress_color=Colors.PRIMARY, height=6
        )
        self.download_progress.set(0)
        self.download_progress.pack(fill="x", padx=20, pady=(0, 15))
        self.download_progress.pack_forget()

        # ── Browse area (inicialmente oculta) ──
        self.browse_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Barra de controles
        self.controls = ctk.CTkFrame(self.browse_frame, fg_color="transparent")
        self.controls.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(self.controls, text="Categoria:", font=Fonts.body_bold()).pack(side="left", padx=(0, 10))

        self.category_var = ctk.StringVar(value="")
        self.category_dropdown = ctk.CTkOptionMenu(
            self.controls, variable=self.category_var,
            values=["Carregando..."], command=self._on_category_change,
            width=350, font=Fonts.body(),
        )
        self.category_dropdown.pack(side="left", padx=(0, 20))

        self.img_count_label = ctk.CTkLabel(
            self.controls, text="", font=Fonts.small(), text_color=Colors.MUTED
        )
        self.img_count_label.pack(side="left")

        # Botões de ação
        self.action_frame = ctk.CTkFrame(self.browse_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(0, 10))

        self.select_all_btn = ctk.CTkButton(
            self.action_frame, text="☑ Selecionar todas",
            font=Fonts.body(), height=35,
            fg_color=Colors.SURFACE, text_color=Colors.INK_SECONDARY,
            border_width=1, border_color=Colors.LINE,
            hover_color=Colors.SURFACE_HOVER,
            command=self._select_all,
        )
        self.select_all_btn.pack(side="left", padx=(0, 10))

        self.deselect_all_btn = ctk.CTkButton(
            self.action_frame, text="☐ Desmarcar todas",
            font=Fonts.body(), height=35,
            fg_color=Colors.SURFACE, text_color=Colors.INK_SECONDARY,
            border_width=1, border_color=Colors.LINE,
            hover_color=Colors.SURFACE_HOVER,
            command=self._deselect_all,
        )
        self.deselect_all_btn.pack(side="left", padx=(0, 20))

        self.selection_label = ctk.CTkLabel(
            self.action_frame, text="0 selecionadas", font=Fonts.body(), text_color=Colors.PRIMARY
        )
        self.selection_label.pack(side="left", padx=(0, 20))

        self.analyze_btn = ctk.CTkButton(
            self.action_frame, text="⌁ Analisar selecionadas",
            font=Fonts.body_bold(), height=40,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_DARK,
            command=self._on_analyze_selected,
        )
        self.analyze_btn.pack(side="right")

        # Grid de thumbnails
        self.grid_frame = ctk.CTkFrame(self.browse_frame, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

        # Se o dataset já foi baixado anteriormente (ex: ao navegar de volta)
        if self._manager.is_downloaded:
            self._show_browser()

    # ── Download ──

    def _on_download(self):
        self.download_btn.configure(state="disabled", text="Baixando...")
        self.download_progress.pack(fill="x", padx=20, pady=(0, 15))
        self.download_progress.set(0)
        self.download_progress.configure(mode="indeterminate")
        self.download_progress.start()

        thread = threading.Thread(target=self._download_thread, daemon=True)
        thread.start()

    def _download_thread(self):
        try:
            def progress_cb(msg):
                self.after(0, lambda m=msg: self.download_status.configure(text=m))

            self._manager.download(progress_callback=progress_cb)
            self.after(0, self._download_complete)

        except Exception as e:
            self.after(0, lambda err=str(e): self._download_error(err))

    def _download_complete(self):
        self.download_progress.stop()
        self.download_progress.pack_forget()
        self.download_btn.configure(text="✓ Dataset disponível", state="disabled",
                                     fg_color=Colors.SEVERITY_GREEN)
        self.download_status.configure(text=f"{len(self._manager.get_categories())} categorias carregadas.")
        self._show_browser()

    def _download_error(self, error: str):
        self.download_progress.stop()
        self.download_progress.pack_forget()
        self.download_btn.configure(state="normal", text="⬇ Tentar novamente")
        self.download_status.configure(text=f"Erro: {error}", text_color=Colors.SEVERITY_RED)

    # ── Browser ──

    def _show_browser(self):
        categories = self._manager.get_categories()
        if not categories:
            return

        display_names = [self._manager.get_category_display_name(c) for c in categories]
        self.category_dropdown.configure(values=display_names)
        self.category_dropdown.set(display_names[0])

        self.browse_frame.pack(fill="both", expand=True)
        self._on_category_change(display_names[0])

    def _on_category_change(self, display_name: str):
        # Encontrar a categoria real pelo display name
        categories = self._manager.get_categories()
        display_map = {self._manager.get_category_display_name(c): c for c in categories}
        category = display_map.get(display_name, "")
        if not category:
            return

        # Limpar seleção anterior
        self._selected_paths.clear()
        self._checkboxes.clear()
        self._thumbnail_refs.clear()
        self._update_selection_label()

        # Limpar grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Carregar imagens (mostrar até 24 thumbnails)
        images = self._manager.get_images(category, limit=24)
        total = self._manager.get_image_count(category)
        self.img_count_label.configure(text=f"({total} imagens, exibindo {len(images)})")

        # Criar grid responsivo
        cols = 6
        for idx, img_path in enumerate(images):
            row = idx // cols
            col = idx % cols
            self._create_thumbnail(img_path, row, col)

        # Configurar colunas do grid
        for c in range(cols):
            self.grid_frame.grid_columnconfigure(c, weight=1)

    def _create_thumbnail(self, img_path: str, row: int, col: int):
        """Cria um card thumbnail com checkbox de seleção."""
        card = ctk.CTkFrame(self.grid_frame, fg_color=Colors.SURFACE, corner_radius=8)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        # Thumbnail
        try:
            pil_img = Image.open(img_path)
            pil_img.thumbnail((120, 120), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 120))
            self._thumbnail_refs.append(ctk_img)  # evitar GC

            img_label = ctk.CTkLabel(card, image=ctk_img, text="")
            img_label.pack(padx=5, pady=(5, 2))
        except Exception:
            ctk.CTkLabel(card, text="⚠", font=("Segoe UI", 28)).pack(padx=5, pady=5)

        # Checkbox de seleção
        var = ctk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            card,
            text=os.path.basename(img_path)[:15],
            font=Fonts.small(),
            variable=var,
            checkbox_width=18, checkbox_height=18,
            command=lambda p=img_path, v=var: self._on_checkbox_toggle(p, v),
        )
        cb.pack(padx=5, pady=(0, 5))
        self._checkboxes[img_path] = (cb, var)

    def _on_checkbox_toggle(self, path: str, var: ctk.BooleanVar):
        if var.get():
            self._selected_paths.add(path)
        else:
            self._selected_paths.discard(path)
        self._update_selection_label()

    def _select_all(self):
        for path, (cb, var) in self._checkboxes.items():
            var.set(True)
            self._selected_paths.add(path)
        self._update_selection_label()

    def _deselect_all(self):
        for path, (cb, var) in self._checkboxes.items():
            var.set(False)
        self._selected_paths.clear()
        self._update_selection_label()

    def _update_selection_label(self):
        n = len(self._selected_paths)
        self.selection_label.configure(text=f"{n} selecionada{'s' if n != 1 else ''}")

    # ── Análise ──

    def _on_analyze_selected(self):
        if not self._selected_paths:
            return

        # Salvar caminhos selecionados no app_state para o Dashboard consumir
        app_state["dataset_selected_files"] = list(self._selected_paths)

        # Navegar ao dashboard — o main_window cuida disso
        main_win = self.winfo_toplevel()
        if hasattr(main_win, "navigate_and_analyze"):
            main_win.navigate_and_analyze("dashboard")

    def refresh(self):
        """Chamado ao navegar para esta página."""
        if self._manager.is_downloaded:
            self._show_browser()
