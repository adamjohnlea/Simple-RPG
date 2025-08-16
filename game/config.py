class Config:
    # Window and performance
    # Common window size presets (WxH)
    RESOLUTIONS = {
        "1080p": (1920, 1080),
        "900p": (1600, 900),
        "768p": (1366, 768),
        "720p": (1280, 720),
        "648p": (1152, 648),
        "576p": (1024, 576),
    }
    # Default window size (change by picking a key from RESOLUTIONS)
    WIDTH, HEIGHT = RESOLUTIONS["720p"]
    TARGET_FPS = 60

    # Movement
    SPEED = 140.0  # px/s
    RUN_MULTIPLIER = 1.5  # Shift to run when Boots acquired

    # Colors
    COLORS = {
        "bg": (30, 30, 40),
        "ground_town": (80, 170, 90),
        "ground_home": (170, 150, 120),
        "ground_farm": (150, 130, 80),
        "road": (180, 180, 180),
        "building": (120, 120, 160),
        "fence": (100, 80, 60),
        "player": (240, 230, 100),
        "prompt_bg": (0, 0, 0),
        "prompt_text": (255, 255, 255),
        "debug_text": (220, 220, 220),
        "trigger": (255, 100, 100),
        "collider": (100, 255, 100),
        # New visual markers
        "door": (200, 80, 40),
        "home_marker": (255, 215, 0),
        # UI additions
        "dialog_bg": (0, 0, 0, 180),
        "dialog_text": (255, 255, 255),
        "coins_text": (255, 220, 100),
        # Props
        "bed": (180, 60, 180),
        # Farming soils
        "soil_untilled": (130, 105, 70),
        "soil_tilled": (110, 85, 55),
        "soil_planted": (60, 130, 60),
        "soil_ready": (200, 170, 60),
    }

    # Farming
    FARM_GROWTH_MINUTES = 720.0  # 12 in-game hours by default

    # Debug
    DEBUG_OVERLAY = False
    DRAW_DEBUG_SHAPES = False

    # Data paths
    DATA_DIR = "game/data"
    SCENES_DIR = f"{DATA_DIR}/scenes"
