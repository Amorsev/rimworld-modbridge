"""
Модуль стилей для тёмного неонового интерфейса.
Определяет цветовую схему и стили виджетов PyQt6.
"""

# Цветовая палитра - тёмный неоновый стиль
COLORS = {
    # Основные цвета фона
    "bg_dark": "#0d0d0d",           # Самый тёмный фон
    "bg_primary": "#1a1a2e",        # Основной фон
    "bg_secondary": "#16213e",      # Вторичный фон
    "bg_tertiary": "#1f2940",       # Третичный фон (для карточек)
    "bg_input": "#0f1624",          # Фон полей ввода
    
    # Неоновые акценты
    "neon_cyan": "#00f5ff",         # Основной неоновый цвет
    "neon_purple": "#bf00ff",       # Фиолетовый неон
    "neon_pink": "#ff00ff",         # Розовый неон
    "neon_green": "#00ff88",        # Зелёный неон (успех)
    "neon_yellow": "#ffff00",       # Жёлтый неон (предупреждение)
    "neon_red": "#ff0055",          # Красный неон (ошибка)
    "neon_orange": "#ff8800",       # Оранжевый неон
    "neon_blue": "#0088ff",         # Синий неон
    
    # Текст
    "text_primary": "#ffffff",      # Основной текст
    "text_secondary": "#b0b0b0",    # Вторичный текст
    "text_muted": "#666666",        # Приглушённый текст
    
    # Границы
    "border_dark": "#2a2a4a",       # Тёмная граница
    "border_light": "#3a3a5a",      # Светлая граница
    "border_glow": "#00f5ff40",     # Свечение границы
    
    # Состояния
    "hover": "#2a3a5a",             # При наведении
    "pressed": "#1a2a4a",           # При нажатии
    "disabled": "#333333",          # Отключено
}

# Уровни логирования и их цвета
LOG_COLORS = {
    "INFO": COLORS["neon_cyan"],
    "SUCCESS": COLORS["neon_green"],
    "WARNING": COLORS["neon_yellow"],
    "ERROR": COLORS["neon_red"],
    "DEBUG": COLORS["neon_purple"],
}


def get_main_stylesheet() -> str:
    """
    Получить основную таблицу стилей приложения.
    
    Returns:
        CSS-подобная строка стилей для PyQt6.
    """
    return f"""
    /* Основное окно */
    QMainWindow {{
        background-color: {COLORS["bg_primary"]};
    }}
    
    QWidget {{
        background-color: {COLORS["bg_primary"]};
        color: {COLORS["text_primary"]};
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }}
    
    /* Метки */
    QLabel {{
        color: {COLORS["text_primary"]};
        background-color: transparent;
        padding: 2px;
    }}
    
    QLabel[class="title"] {{
        font-size: 18px;
        font-weight: bold;
        color: {COLORS["neon_cyan"]};
    }}
    
    QLabel[class="subtitle"] {{
        font-size: 12px;
        color: {COLORS["text_secondary"]};
    }}
    
    /* Поля ввода */
    QLineEdit {{
        background-color: {COLORS["bg_input"]};
        border: 2px solid {COLORS["border_dark"]};
        border-radius: 8px;
        padding: 10px 15px;
        color: {COLORS["text_primary"]};
        font-size: 13px;
        selection-background-color: {COLORS["neon_cyan"]};
        selection-color: {COLORS["bg_dark"]};
    }}
    
    QLineEdit:focus {{
        border-color: {COLORS["neon_cyan"]};
        box-shadow: 0 0 10px {COLORS["border_glow"]};
    }}
    
    QLineEdit:hover {{
        border-color: {COLORS["border_light"]};
    }}
    
    QLineEdit:disabled {{
        background-color: {COLORS["disabled"]};
        color: {COLORS["text_muted"]};
    }}
    
    /* Кнопки */
    QPushButton {{
        background-color: {COLORS["bg_tertiary"]};
        border: 2px solid {COLORS["neon_cyan"]};
        border-radius: 8px;
        padding: 10px 20px;
        color: {COLORS["neon_cyan"]};
        font-size: 13px;
        font-weight: bold;
        min-height: 20px;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS["hover"]};
        border-color: {COLORS["neon_cyan"]};
        color: {COLORS["text_primary"]};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS["pressed"]};
        border-color: {COLORS["neon_purple"]};
    }}
    
    QPushButton:disabled {{
        background-color: {COLORS["disabled"]};
        border-color: {COLORS["text_muted"]};
        color: {COLORS["text_muted"]};
    }}
    
    QPushButton[class="primary"] {{
        background-color: {COLORS["neon_cyan"]};
        color: {COLORS["bg_dark"]};
        border-color: {COLORS["neon_cyan"]};
    }}
    
    QPushButton[class="primary"]:hover {{
        background-color: {COLORS["neon_blue"]};
        border-color: {COLORS["neon_blue"]};
    }}
    
    QPushButton[class="danger"] {{
        border-color: {COLORS["neon_red"]};
        color: {COLORS["neon_red"]};
    }}
    
    QPushButton[class="danger"]:hover {{
        background-color: {COLORS["neon_red"]};
        color: {COLORS["text_primary"]};
    }}
    
    QPushButton[class="success"] {{
        border-color: {COLORS["neon_green"]};
        color: {COLORS["neon_green"]};
    }}
    
    QPushButton[class="success"]:hover {{
        background-color: {COLORS["neon_green"]};
        color: {COLORS["bg_dark"]};
    }}
    
    /* Текстовое поле (логи) */
    QTextEdit {{
        background-color: {COLORS["bg_dark"]};
        border: 2px solid {COLORS["border_dark"]};
        border-radius: 8px;
        padding: 10px;
        color: {COLORS["text_primary"]};
        font-family: 'Consolas', 'Courier New', monospace;
    }}
    
    QTextEdit:focus {{
        border-color: {COLORS["neon_purple"]};
    }}
    
    /* Полоса прокрутки */
    QScrollBar:vertical {{
        background-color: {COLORS["bg_dark"]};
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLORS["border_light"]};
        border-radius: 6px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS["neon_cyan"]};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}
    
    /* Радиокнопки */
    QRadioButton {{
        color: {COLORS["text_primary"]};
        spacing: 10px;
        padding: 5px;
    }}
    
    QRadioButton::indicator {{
        width: 20px;
        height: 20px;
        border-radius: 10px;
        border: 2px solid {COLORS["border_light"]};
        background-color: {COLORS["bg_input"]};
    }}
    
    QRadioButton::indicator:checked {{
        background-color: {COLORS["neon_cyan"]};
        border-color: {COLORS["neon_cyan"]};
    }}
    
    QRadioButton::indicator:hover {{
        border-color: {COLORS["neon_cyan"]};
    }}
    
    /* Чекбоксы */
    QCheckBox {{
        color: {COLORS["text_primary"]};
        spacing: 10px;
        padding: 5px;
    }}
    
    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid {COLORS["border_light"]};
        background-color: {COLORS["bg_input"]};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {COLORS["neon_cyan"]};
        border-color: {COLORS["neon_cyan"]};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {COLORS["neon_cyan"]};
    }}
    
    /* Группы */
    QGroupBox {{
        border: 2px solid {COLORS["border_dark"]};
        border-radius: 10px;
        margin-top: 15px;
        padding-top: 15px;
        font-weight: bold;
        color: {COLORS["neon_cyan"]};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 5px 15px;
        background-color: {COLORS["bg_primary"]};
        border-radius: 5px;
    }}
    
    /* Прогресс-бар */
    QProgressBar {{
        background-color: {COLORS["bg_dark"]};
        border: 2px solid {COLORS["border_dark"]};
        border-radius: 8px;
        text-align: center;
        color: {COLORS["text_primary"]};
        font-weight: bold;
        min-height: 25px;
    }}
    
    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS["neon_purple"]},
            stop:1 {COLORS["neon_cyan"]}
        );
        border-radius: 6px;
    }}
    
    /* Спинбокс */
    QSpinBox {{
        background-color: {COLORS["bg_input"]};
        border: 2px solid {COLORS["border_dark"]};
        border-radius: 8px;
        padding: 5px 10px;
        color: {COLORS["text_primary"]};
        font-size: 13px;
    }}
    
    QSpinBox:focus {{
        border-color: {COLORS["neon_cyan"]};
    }}
    
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {COLORS["bg_tertiary"]};
        border: none;
        width: 20px;
    }}
    
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {COLORS["hover"]};
    }}
    
    /* Разделитель */
    QFrame[frameShape="4"] {{
        background-color: {COLORS["border_dark"]};
        max-height: 2px;
    }}
    
    QFrame[frameShape="5"] {{
        background-color: {COLORS["border_dark"]};
        max-width: 2px;
    }}
    
    /* Всплывающие подсказки */
    QToolTip {{
        background-color: {COLORS["bg_tertiary"]};
        border: 1px solid {COLORS["neon_cyan"]};
        border-radius: 5px;
        padding: 8px;
        color: {COLORS["text_primary"]};
        font-size: 12px;
    }}
    
    /* Меню */
    QMenu {{
        background-color: {COLORS["bg_secondary"]};
        border: 1px solid {COLORS["border_dark"]};
        border-radius: 8px;
        padding: 5px;
    }}
    
    QMenu::item {{
        padding: 8px 25px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {COLORS["hover"]};
        color: {COLORS["neon_cyan"]};
    }}
    
    /* Диалоги выбора файлов */
    QFileDialog {{
        background-color: {COLORS["bg_primary"]};
    }}
    """


def get_log_html_style(level: str, message: str, timestamp: str = "") -> str:
    """
    Получить HTML-форматированную строку лога.
    
    Args:
        level: Уровень логирования (INFO, SUCCESS, WARNING, ERROR, DEBUG).
        message: Текст сообщения.
        timestamp: Временная метка (опционально).
        
    Returns:
        HTML-строка с цветным форматированием.
    """
    color = LOG_COLORS.get(level, COLORS["text_primary"])
    
    timestamp_html = ""
    if timestamp:
        timestamp_html = f'<span style="color: {COLORS["text_muted"]};">[{timestamp}]</span> '
    
    level_html = f'<span style="color: {color}; font-weight: bold;">[{level}]</span>'
    message_html = f'<span style="color: {COLORS["text_primary"]};">{message}</span>'
    
    return f'{timestamp_html}{level_html} {message_html}<br>'


def get_progress_gradient(progress: float) -> str:
    """
    Получить градиент для прогресс-бара в зависимости от прогресса.
    
    Args:
        progress: Значение прогресса от 0 до 1.
        
    Returns:
        CSS градиент.
    """
    if progress < 0.3:
        return f"background: {COLORS['neon_red']};"
    elif progress < 0.7:
        return f"background: {COLORS['neon_yellow']};"
    else:
        return f"background: {COLORS['neon_green']};"


# Дополнительные стили для специфических виджетов
PANEL_STYLE = f"""
    background-color: {COLORS["bg_secondary"]};
    border: 1px solid {COLORS["border_dark"]};
    border-radius: 12px;
    padding: 15px;
"""

CARD_STYLE = f"""
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border_dark"]};
    border-radius: 10px;
    padding: 12px;
"""

GLOW_EFFECT = f"""
    border: 2px solid {COLORS["neon_cyan"]};
    box-shadow: 0 0 15px {COLORS["border_glow"]};
"""


# Пример использования
if __name__ == "__main__":
    print("Цветовая палитра:")
    for name, color in COLORS.items():
        print(f"  {name}: {color}")
    
    print("\nПример HTML лога:")
    print(get_log_html_style("INFO", "Тестовое сообщение", "12:00:00"))
    print(get_log_html_style("SUCCESS", "Операция завершена"))
    print(get_log_html_style("ERROR", "Произошла ошибка"))
