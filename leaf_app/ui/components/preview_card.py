import customtkinter as ctk
from PIL import Image
from ui.theme import Colors, Fonts, Layout
import numpy as np
import cv2

class PreviewCard(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Visão computacional", font=Fonts.body_bold(), text_color=Colors.INK)
        self.title_label.pack(side="left")
        
        self.status_badge = ctk.CTkLabel(
            self.header_frame, 
            text=" Aguardando imagem ", 
            font=Fonts.small(), 
            fg_color=Colors.PRIMARY_SOFT, 
            text_color=Colors.PRIMARY_DARK,
            corner_radius=4
        )
        self.status_badge.pack(side="right")
        
        # Canvas de visualizacao
        self.canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.image_label = ctk.CTkLabel(self.canvas_frame, text="Nenhuma imagem carregada\n\nEnvie uma folha para exibir contornos,\náreas afetadas e leitura visual.", text_color=Colors.MUTED, font=Fonts.body())
        self.image_label.grid(row=0, column=0, sticky="nsew")
        
    def show_analyzing(self):
        self.status_badge.configure(text=" Analisando... ", text_color=Colors.ORANGE)
        self.image_label.configure(text="Processando imagem...", image="")
        
    def show_result(self, bgr_image: np.ndarray):
        self.status_badge.configure(text=" Análise Concluída ", text_color=Colors.PRIMARY_DARK)
        
        if bgr_image is not None:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # Create a CTkImage scaled to fit
            # No dashboard o frame tem um tamanho. Vou definir fixo para agora.
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(500, 350))
            self.image_label.configure(text="", image=ctk_img)
            # Precisamos manter a referencia da imagem
            self.image_label.image = ctk_img
        else:
            self.image_label.configure(text="Erro ao carregar imagem.", image="")
