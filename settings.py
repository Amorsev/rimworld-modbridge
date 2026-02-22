"""
Модуль для управления настройками приложения.
Сохраняет и загружает пользовательские настройки в JSON файл.
"""

import os
import json
from typing import Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class WorkMode(Enum):
    """Режим работы приложения."""
    PERSISTENT = 1  # Режим 1: с кэшем, моды остаются
    TEMPORARY = 2   # Режим 2: временный, моды удаляются


@dataclass
class AppSettings:
    """Настройки приложения."""
    # Пути
    steamcmd_path: str = ""
    output_path: str = ""
    xml_filename: str = "ModList"
    
    # Папки для загрузки модов
    mods_download_path: str = ""  # Папка для постоянного хранения модов (Режим 1)
    temp_download_path: str = ""  # Временная папка для загрузки (Режим 2)
    
    # Режим работы
    work_mode: int = 1  # 1 = PERSISTENT, 2 = TEMPORARY
    
    # Настройки интерфейса
    log_font_size: int = 10
    window_width: int = 1200
    window_height: int = 700
    
    # Расширенные настройки
    verbose_logging: bool = False
    include_workshop_ids_in_xml: bool = True
    download_timeout: int = 300
    retry_count: int = 3
    
    # Последние использованные значения
    last_collection_url: str = ""
    
    def get_work_mode(self) -> WorkMode:
        """Получить режим работы как enum."""
        return WorkMode(self.work_mode)
    
    def set_work_mode(self, mode: WorkMode) -> None:
        """Установить режим работы."""
        self.work_mode = mode.value


class SettingsManager:
    """
    Менеджер настроек приложения.
    Обеспечивает сохранение и загрузку настроек из JSON файла.
    """
    
    DEFAULT_SETTINGS_FILE = "settings.json"
    
    def __init__(self, settings_path: Optional[str] = None):
        """
        Инициализация менеджера настроек.
        
        Args:
            settings_path: Путь к файлу настроек. Если не указан,
                          используется файл в директории приложения.
        """
        if settings_path:
            self.settings_path = settings_path
        else:
            # Определение директории приложения
            app_dir = os.path.dirname(os.path.abspath(__file__))
            self.settings_path = os.path.join(app_dir, self.DEFAULT_SETTINGS_FILE)
        
        self.settings = AppSettings()
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Загрузить настройки из файла."""
        if not os.path.exists(self.settings_path):
            # Файл не существует, используем настройки по умолчанию
            return
        
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Обновление настроек из загруженных данных
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                    
        except json.JSONDecodeError:
            # Файл повреждён, используем настройки по умолчанию
            pass
        except Exception:
            # Другие ошибки, используем настройки по умолчанию
            pass
    
    def save_settings(self) -> bool:
        """
        Сохранить настройки в файл.
        
        Returns:
            True если сохранение успешно, False при ошибке.
        """
        try:
            # Создание директории если не существует
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение настройки.
        
        Args:
            key: Ключ настройки.
            default: Значение по умолчанию.
            
        Returns:
            Значение настройки или default.
        """
        return getattr(self.settings, key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        Установить значение настройки.
        
        Args:
            key: Ключ настройки.
            value: Новое значение.
            
        Returns:
            True если настройка установлена, False если ключ не существует.
        """
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            return True
        return False
    
    def update(self, **kwargs) -> None:
        """
        Обновить несколько настроек одновременно.
        
        Args:
            **kwargs: Пары ключ-значение для обновления.
        """
        for key, value in kwargs.items():
            self.set(key, value)
    
    def reset_to_defaults(self) -> None:
        """Сбросить все настройки к значениям по умолчанию."""
        self.settings = AppSettings()
    
    def export_settings(self, export_path: str) -> bool:
        """
        Экспортировать настройки в указанный файл.
        
        Args:
            export_path: Путь для экспорта.
            
        Returns:
            True если экспорт успешен.
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """
        Импортировать настройки из указанного файла.
        
        Args:
            import_path: Путь к файлу для импорта.
            
        Returns:
            True если импорт успешен.
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            return True
        except Exception:
            return False
    
    # Свойства для удобного доступа к часто используемым настройкам
    
    @property
    def steamcmd_path(self) -> str:
        """Путь к steamcmd."""
        return self.settings.steamcmd_path
    
    @steamcmd_path.setter
    def steamcmd_path(self, value: str) -> None:
        self.settings.steamcmd_path = value
    
    @property
    def output_path(self) -> str:
        """Путь для сохранения XML."""
        return self.settings.output_path
    
    @output_path.setter
    def output_path(self, value: str) -> None:
        self.settings.output_path = value
    
    @property
    def xml_filename(self) -> str:
        """Имя XML файла."""
        return self.settings.xml_filename
    
    @xml_filename.setter
    def xml_filename(self, value: str) -> None:
        self.settings.xml_filename = value
    
    @property
    def work_mode(self) -> WorkMode:
        """Режим работы."""
        return self.settings.get_work_mode()
    
    @work_mode.setter
    def work_mode(self, value: WorkMode) -> None:
        self.settings.set_work_mode(value)
    
    @property
    def log_font_size(self) -> int:
        """Размер шрифта логов."""
        return self.settings.log_font_size
    
    @log_font_size.setter
    def log_font_size(self, value: int) -> None:
        self.settings.log_font_size = max(8, min(24, value))  # Ограничение 8-24
    
    @property
    def verbose_logging(self) -> bool:
        """Расширенное логирование."""
        return self.settings.verbose_logging
    
    @verbose_logging.setter
    def verbose_logging(self, value: bool) -> None:
        self.settings.verbose_logging = value
    
    @property
    def mods_download_path(self) -> str:
        """Папка для постоянного хранения модов (Режим 1)."""
        return self.settings.mods_download_path
    
    @mods_download_path.setter
    def mods_download_path(self, value: str) -> None:
        self.settings.mods_download_path = value
    
    @property
    def temp_download_path(self) -> str:
        """Временная папка для загрузки модов (Режим 2)."""
        return self.settings.temp_download_path
    
    @temp_download_path.setter
    def temp_download_path(self, value: str) -> None:
        self.settings.temp_download_path = value


# Пример использования
if __name__ == "__main__":
    # Создание менеджера настроек
    manager = SettingsManager()
    
    # Установка настроек
    manager.steamcmd_path = "C:/steamcmd/steamcmd.exe"
    manager.output_path = "C:/RimWorld/ModLists"
    manager.xml_filename = "MyModList"
    manager.work_mode = WorkMode.PERSISTENT
    manager.log_font_size = 12
    
    # Сохранение
    if manager.save_settings():
        print("Настройки сохранены")
    
    # Вывод текущих настроек
    print(f"SteamCMD: {manager.steamcmd_path}")
    print(f"Output: {manager.output_path}")
    print(f"Filename: {manager.xml_filename}")
    print(f"Mode: {manager.work_mode}")
    print(f"Font size: {manager.log_font_size}")
