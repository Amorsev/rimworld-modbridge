"""
RimWorld Mod Collector

Desktop-приложение для загрузки модов Steam Workshop для RimWorld
и генерации XML-файлов, совместимых с RimPy.

Модули:
    - database: Работа с локальной базой данных SQLite
    - steam_handler: Взаимодействие со Steam Workshop и steamcmd
    - xml_processor: Обработка XML файлов модов
    - settings: Управление настройками приложения
    - styles: Стили тёмного неонового интерфейса
    - main: Главный модуль с GUI

Использование:
    python main.py

Автор: Amorsev
Версия: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Amorsev"

from .database import ModDatabase, ModRecord
from .steam_handler import SteamHandler, CollectionInfo, DownloadStatus, DownloadResult
from .xml_processor import XmlProcessor, ModInfo
from .settings import SettingsManager, AppSettings, WorkMode

__all__ = [
    "ModDatabase",
    "ModRecord",
    "SteamHandler",
    "CollectionInfo",
    "DownloadStatus",
    "DownloadResult",
    "XmlProcessor",
    "ModInfo",
    "SettingsManager",
    "AppSettings",
    "WorkMode",
]
