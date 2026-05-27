import customtkinter as ctk
from ui.theme import Fonts, Colors, Layout
from ui.state import app_state

class SettingsPage(ctk.CTkScrollableFrame):
    PAGE_ID = "settings"
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(self.header_frame, text="Configurações e calibração", font=Fonts.header2(), text_color=Colors.INK).pack(anchor="w")
        ctk.CTkLabel(self.header_frame, text="Ajustes avançados para controle de ruído, contornos e reconstrução.", font=Fonts.body(), text_color=Colors.MUTED).pack(anchor="w")
        
        # Area Principal
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x")
        self.grid_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Coluna 1
        self.col1 = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.col1.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        # PPM
        ctk.CTkLabel(self.col1, text="Fator de conversão (pixels por cm)", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        
        self.ppm_var = ctk.StringVar(value=str(app_state["ppm"]))
        self.ppm_entry = ctk.CTkEntry(self.col1, textvariable=self.ppm_var)
        self.ppm_entry.pack(fill="x", pady=(0, 20))
        self.ppm_var.trace_add("write", self._on_ppm_change)
        
        # Color Mode
        ctk.CTkLabel(self.col1, text="Espaço de cores para segmentação", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        self.color_mode_option = ctk.CTkOptionMenu(self.col1, values=["HSV", "CIELAB"], command=self._on_color_mode_change)
        self.color_mode_option.set(app_state["color_mode"])
        self.color_mode_option.pack(fill="x", pady=(0, 20))
        
        # Hull Method
        ctk.CTkLabel(self.col1, text="Método de reconstrução da silhueta", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        self.hull_method_option = ctk.CTkOptionMenu(self.col1, values=["Convex Hull", "Fechamento Morfologico"], command=self._on_hull_change)
        self.hull_method_option.set(app_state["hull_method"])
        self.hull_method_option.pack(fill="x", pady=(0, 20))
        
        # Coluna 2
        self.col2 = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.col2.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        
        # Min Area
        ctk.CTkLabel(self.col2, text="Área mínima de contorno", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        self.min_area_val = ctk.CTkLabel(self.col2, text=str(app_state["min_area"]), text_color=Colors.PRIMARY)
        self.min_area_val.pack(anchor="e")
        self.min_area_slider = ctk.CTkSlider(self.col2, from_=20, to=2000, number_of_steps=100, command=self._on_min_area_change)
        self.min_area_slider.set(app_state["min_area"])
        self.min_area_slider.pack(fill="x", pady=(0, 20))
        
        # Morph Kernel
        ctk.CTkLabel(self.col2, text="Kernel morfológico", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        self.morph_kernel_val = ctk.CTkLabel(self.col2, text=str(app_state["morph_kernel_size"]), text_color=Colors.PRIMARY)
        self.morph_kernel_val.pack(anchor="e")
        self.morph_kernel_slider = ctk.CTkSlider(self.col2, from_=5, to=101, number_of_steps=48, command=self._on_morph_change)
        self.morph_kernel_slider.set(app_state["morph_kernel_size"])
        self.morph_kernel_slider.pack(fill="x", pady=(0, 20))
        
        # GrabCut — Isolamento de Fundo
        ctk.CTkFrame(self.col2, height=1, fg_color=Colors.LINE).pack(fill="x", pady=(0, 15))
        
        self.grabcut_switch = ctk.CTkSwitch(
            self.col2,
            text="Isolamento de fundo (GrabCut)",
            font=Fonts.body_bold(),
            command=self._on_grabcut_toggle,
            button_color=Colors.PRIMARY,
            progress_color=Colors.PRIMARY_SOFT
        )
        if app_state["use_background_removal"]:
            self.grabcut_switch.select()
        self.grabcut_switch.pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            self.col2,
            text="Remove pixels de fundo antes da análise de cor.\nMais lento, mas muito mais preciso.",
            font=Fonts.small(),
            text_color=Colors.MUTED,
            justify="left"
        ).pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(self.col2, text="Nível GrabCut (precisão vs. velocidade)", font=Fonts.body_bold()).pack(anchor="w", pady=(0, 5))
        self.grabcut_iter_val = ctk.CTkLabel(self.col2, text=f"{app_state['grabcut_iterations']:.1f}", text_color=Colors.PRIMARY)
        self.grabcut_iter_val.pack(anchor="e")
        self.grabcut_iter_slider = ctk.CTkSlider(self.col2, from_=1.0, to=10.0, number_of_steps=90, command=self._on_grabcut_iter_change)
        self.grabcut_iter_slider.set(app_state["grabcut_iterations"])
        self.grabcut_iter_slider.pack(fill="x", pady=(0, 20))
        
        # Limiares Avançados (HSV/LAB)
        self.adv_frame = ctk.CTkFrame(self, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE)
        self.adv_frame.pack(fill="x", pady=30, padx=5)
        
        ctk.CTkLabel(self.adv_frame, text="Limiares de Cor Avançados", font=Fonts.body_bold()).pack(anchor="w", padx=20, pady=(15, 5))
        self.limiar_container = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        self.limiar_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self._build_advanced_thresholds()
        
    def _on_ppm_change(self, *args):
        try:
            val = float(self.ppm_var.get())
            app_state["ppm"] = val
        except ValueError:
            pass

    def _on_color_mode_change(self, value):
        app_state["color_mode"] = value
        self._build_advanced_thresholds()

    def _on_hull_change(self, value):
        app_state["hull_method"] = value

    def _on_min_area_change(self, value):
        val = int(value)
        self.min_area_val.configure(text=str(val))
        app_state["min_area"] = val

    def _on_morph_change(self, value):
        val = int(value)
        # Kernel deve ser impar preferencialmente, mas o OpenCV cuida de arredondar, mesmo assim:
        if val % 2 == 0: val += 1
        self.morph_kernel_val.configure(text=str(val))
        app_state["morph_kernel_size"] = val

    def _on_grabcut_toggle(self):
        app_state["use_background_removal"] = self.grabcut_switch.get() == 1

    def _on_grabcut_iter_change(self, value):
        val = round(float(value), 1)
        self.grabcut_iter_val.configure(text=f"{val:.1f}")
        app_state["grabcut_iterations"] = val

    def _build_advanced_thresholds(self):
        # Limpa o container
        for widget in self.limiar_container.winfo_children():
            widget.destroy()
            
        self.limiar_container.grid_columnconfigure((0, 1), weight=1)
        mode = app_state["color_mode"]
        
        # Saudável
        f_green = ctk.CTkFrame(self.limiar_container, fg_color="transparent")
        f_green.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(f_green, text="Verde saudável", font=Fonts.body_bold(), text_color=Colors.PRIMARY).pack(anchor="w", pady=(0, 10))
        
        # Sintomático
        f_symp = ctk.CTkFrame(self.limiar_container, fg_color="transparent")
        f_symp.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        ctk.CTkLabel(f_symp, text="Área sintomática", font=Fonts.body_bold(), text_color=Colors.YELLOW).pack(anchor="w", pady=(0, 10))
        
        if mode == "HSV":
            labels = ["H (Matiz)", "S (Saturação)", "V (Valor)"]
            limits = [(0, 179), (0, 255), (0, 255)]
            state_g = app_state["hsv_green"]
            state_s = app_state["hsv_symp"]
            state_key_g = "hsv_green"
            state_key_s = "hsv_symp"
        else:
            labels = ["L* (Luminância)", "a* (Verde/Vermelho)", "b* (Azul/Amarelo)"]
            limits = [(0, 255), (0, 255), (0, 255)]
            state_g = app_state["lab_green"]
            state_s = app_state["lab_symp"]
            state_key_g = "lab_green"
            state_key_s = "lab_symp"
            
        # Helper para criar os range sliders fake (já que CTk não tem range slider nativo)
        # Vamos usar 2 sliders para cada componente (min, max)
        
        def add_range(parent, label, min_val, max_val, current_min, current_max, on_change_min, on_change_max):
            ctk.CTkLabel(parent, text=label, font=Fonts.small()).pack(anchor="w")
            
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 10))
            
            min_l = ctk.CTkLabel(row, text=str(current_min), width=30)
            min_l.pack(side="left")
            s_min = ctk.CTkSlider(row, from_=min_val, to=max_val, width=100)
            s_min.set(current_min)
            s_min.pack(side="left", padx=5, expand=True, fill="x")
            
            s_max = ctk.CTkSlider(row, from_=min_val, to=max_val, width=100)
            s_max.set(current_max)
            s_max.pack(side="left", padx=5, expand=True, fill="x")
            max_l = ctk.CTkLabel(row, text=str(current_max), width=30)
            max_l.pack(side="left")
            
            def wrap_min(val):
                v = int(val)
                min_l.configure(text=str(v))
                on_change_min(v)
            def wrap_max(val):
                v = int(val)
                max_l.configure(text=str(v))
                on_change_max(v)
                
            s_min.configure(command=wrap_min)
            s_max.configure(command=wrap_max)
        
        # Constrói para os 3 canais de Verde
        for i in range(3):
            def make_updater(idx, is_min, key):
                def updater(val):
                    current = list(app_state[key])
                    # idx*2 é o min, idx*2+1 é o max
                    pos = idx * 2 if is_min else idx * 2 + 1
                    current[pos] = val
                    app_state[key] = tuple(current)
                return updater
                
            add_range(
                f_green, labels[i], limits[i][0], limits[i][1],
                state_g[i*2], state_g[i*2+1],
                make_updater(i, True, state_key_g),
                make_updater(i, False, state_key_g)
            )
            
            add_range(
                f_symp, labels[i], limits[i][0], limits[i][1],
                state_s[i*2], state_s[i*2+1],
                make_updater(i, True, state_key_s),
                make_updater(i, False, state_key_s)
            )
