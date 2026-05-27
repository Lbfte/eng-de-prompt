"""
Design System do LEAF para CustomTkinter.
Concentra paleta de cores (modo Light/Dark), fontes e constantes de layout.
As cores em tuplas representam (Light Mode, Dark Mode).
"""

class Colors:
    # Cores principais (fixas para light/dark)
    PRIMARY = "#1F7A35"
    PRIMARY_DARK = "#145A27"
    YELLOW = "#E3B505"
    BLUE = "#4F8FCF"
    PURPLE = "#9B59B6"
    ORANGE = "#D8911D"
    
    # Tons adaptáveis (Light, Dark)
    PAGE_BG = ("#FBFCFA", "#0F172A")
    SURFACE = ("#FFFFFF", "#1F2937")
    SURFACE_HOVER = ("#F7FAF7", "#2C3B4E")
    
    # Tons de texto e linha (Light, Dark)
    INK = ("#1F2937", "#F3F4F6")
    INK_SECONDARY = ("#374151", "#D1D5DB")
    MUTED = ("#6B7280", "#9CA3AF")
    LINE = ("#E5E7EB", "#374151")
    
    # Cores com opacidade (simuladas misturando com o background)
    # Primary Soft no Light é #EAF6EC e no Dark usaremos um tom translúcido adaptado
    PRIMARY_SOFT = ("#EAF6EC", "#1B3B28")
    
    # Badge colors
    SEVERITY_GREEN = "#25A64A"
    SEVERITY_YELLOW = "#D7C51B"
    SEVERITY_ORANGE = "#F1A114"
    SEVERITY_RED = "#B91C1C"

class Fonts:
    # No Windows, 'Inter' pode não estar instalada. O fallback nativo costuma ser 'Segoe UI'.
    FAMILY = "Segoe UI"
    
    @classmethod
    def header1(cls):
        return (cls.FAMILY, 36, "bold")
        
    @classmethod
    def header2(cls):
        return (cls.FAMILY, 24, "bold")
        
    @classmethod
    def header3(cls):
        return (cls.FAMILY, 18, "bold")
        
    @classmethod
    def body_large(cls):
        return (cls.FAMILY, 16, "normal")
        
    @classmethod
    def body(cls):
        return (cls.FAMILY, 14, "normal")
        
    @classmethod
    def body_bold(cls):
        return (cls.FAMILY, 14, "bold")
        
    @classmethod
    def small(cls):
        return (cls.FAMILY, 12, "normal")

class Layout:
    CORNER_RADIUS = 12
    PADDING_SMALL = 10
    PADDING_MEDIUM = 20
    PADDING_LARGE = 30
