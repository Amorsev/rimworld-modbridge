"""
Главный модуль приложения RimWorld Mod Collector.
Реализует графический интерфейс на PyQt6 с тёмным неоновым стилем.
"""

import sys
import os
import asyncio
from datetime import datetime
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QRadioButton,
    QButtonGroup, QGroupBox, QFileDialog, QProgressBar, QSpinBox,
    QFrame, QSplitter, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QIcon

# Импорт модулей приложения
from database import ModDatabase
from steam_handler import SteamHandler, CollectionInfo, DownloadStatus
from xml_processor import XmlProcessor, ModInfo
from settings import SettingsManager, WorkMode
from styles import get_main_stylesheet, get_log_html_style, COLORS


class WorkerThread(QThread):
    """
    Рабочий поток для асинхронной обработки модов.
    Выполняет загрузку и обработку без блокировки UI.
    """
    
    # Сигналы для обновления UI
    log_signal = pyqtSignal(str, str)  # message, level
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(bool, str)  # success, message
    stats_signal = pyqtSignal(int, int, int)  # processed, skipped, errors
    
    def __init__(
        self,
        collection_url: str,
        steamcmd_path: str,
        output_path: str,
        xml_filename: str,
        work_mode: WorkMode,
        download_path: str,
        include_workshop_ids: bool = True,
        verbose: bool = False
    ):
        super().__init__()
        self.collection_url = collection_url
        self.steamcmd_path = steamcmd_path
        self.output_path = output_path
        self.xml_filename = xml_filename
        self.work_mode = work_mode
        self.download_path = download_path
        self.include_workshop_ids = include_workshop_ids
        self.verbose = verbose
        
        self._stop_requested = False
        self.steam_handler: Optional[SteamHandler] = None
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Отправить сообщение в лог."""
        self.log_signal.emit(message, level)
    
    def stop(self) -> None:
        """Запросить остановку обработки."""
        self._stop_requested = True
        if self.steam_handler:
            self.steam_handler.stop()
    
    def run(self) -> None:
        """
        Основной метод выполнения потока.
        
        Логика режимов:
        - Режим 1 (PERSISTENT): моды остаются в папке загрузки
        - Режим 2 (TEMPORARY): сначала выполняется обработка как в режиме 1,
          затем все скачанные моды удаляются после успешной генерации XML
        """
        try:
            # Инициализация компонентов
            db = ModDatabase()
            self.steam_handler = SteamHandler(
                steamcmd_path=self.steamcmd_path,
                download_dir=self.download_path if self.download_path else None,
                log_callback=self.log
            )
            xml_processor = XmlProcessor(log_callback=self.log)
            
            # Проверка steamcmd
            valid, msg = self.steam_handler.validate_steamcmd()
            if not valid:
                self.finished_signal.emit(False, msg)
                return
            
            # Создание директории загрузки
            if not self.steam_handler.ensure_download_dir_exists():
                self.finished_signal.emit(False, "Не удалось создать директорию загрузки")
                return
            
            self.log(f"Папка загрузки модов: {self.steam_handler.download_dir}", "INFO")
            self.log("Начало обработки коллекции...", "INFO")
            
            # Получение списка модов из коллекции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                collection_info = loop.run_until_complete(
                    self.steam_handler.fetch_collection_mods(self.collection_url)
                )
            except Exception as e:
                self.finished_signal.emit(False, f"Ошибка получения коллекции: {str(e)}")
                return
            finally:
                loop.close()
            
            mod_ids = collection_info.mod_ids
            total_mods = len(mod_ids)
            
            self.log(f"Найдено {total_mods} модов в коллекции", "SUCCESS")
            
            # Статистика
            processed = 0
            skipped = 0
            errors = 0
            
            # Список успешно обработанных модов
            mod_infos: List[ModInfo] = []
            
            # Список загруженных модов для последующего удаления (режим 2)
            downloaded_mods: List[str] = []
            
            # Обработка каждого мода
            for i, workshop_id in enumerate(mod_ids):
                if self._stop_requested:
                    self.log("Обработка остановлена пользователем", "WARNING")
                    break
                
                self.progress_signal.emit(i + 1, total_mods)
                
                # В режиме 2 пропускаем проверку кэша - сначала обрабатываем все моды
                # (режим 2 вызывает логику режима 1 для скачивания и обработки)
                if self.work_mode == WorkMode.TEMPORARY:
                    cached_package_id = db.get_package_id(workshop_id)
                    if cached_package_id:
                        self.log(
                            f"Мод {workshop_id} найден в кэше БД: {cached_package_id}",
                            "DEBUG" if self.verbose else "INFO"
                        )
                        mod_infos.append(ModInfo(
                            workshop_id=workshop_id,
                            package_id=cached_package_id
                        ))
                        skipped += 1
                        self.stats_signal.emit(processed, skipped, errors)
                        continue
                
                # Проверка наличия загруженного мода
                if self.steam_handler.is_mod_downloaded(workshop_id):
                    mod_path = self.steam_handler.get_mod_path(workshop_id)
                    mod_info = xml_processor.extract_package_id(mod_path, workshop_id)
                    
                    if mod_info:
                        self.log(
                            f"Мод {workshop_id} уже загружен: {mod_info.package_id}",
                            "INFO"
                        )
                        mod_infos.append(mod_info)
                        
                        # Сохраняем в БД для режима 2
                        if self.work_mode == WorkMode.TEMPORARY:
                            db.add_mod(workshop_id, mod_info.package_id, self.collection_url)
                        
                        skipped += 1
                        self.stats_signal.emit(processed, skipped, errors)
                        continue
                
                # Загрузка мода
                result = self.steam_handler.download_mod(workshop_id)
                
                if result.status == DownloadStatus.SUCCESS:
                    # Запоминаем загруженный мод для возможного удаления в режиме 2
                    downloaded_mods.append(workshop_id)
                    
                    # Извлечение packageId
                    mod_info = xml_processor.extract_package_id(
                        result.mod_path,
                        workshop_id
                    )
                    
                    if mod_info:
                        mod_infos.append(mod_info)
                        
                        # Сохранение в базу данных
                        db.add_mod(
                            workshop_id,
                            mod_info.package_id,
                            self.collection_url
                        )
                        
                        processed += 1
                        self.log(
                            f"Обработан мод {workshop_id}: {mod_info.package_id}",
                            "SUCCESS"
                        )
                    else:
                        errors += 1
                        self.log(
                            f"Не удалось извлечь packageId для мода {workshop_id}",
                            "WARNING"
                        )
                else:
                    errors += 1
                    self.log(
                        f"Ошибка загрузки мода {workshop_id}: {result.error_message}",
                        "ERROR"
                    )
                
                self.stats_signal.emit(processed, skipped, errors)
            
            # Генерация XML
            xml_generation_success = False
            result_path = ""
            
            if mod_infos and not self._stop_requested:
                self.log(f"Генерация XML файла ({len(mod_infos)} модов)...", "INFO")
                
                # Генерация XML в формате ModsConfigData (RimWorld native)
                xml_content = xml_processor.generate_mods_config_data_xml(
                    mod_infos,
                    version="1.6.4633",
                    include_workshop_ids=self.include_workshop_ids
                )
                
                success, result_path = xml_processor.save_xml(
                    xml_content,
                    self.output_path,
                    self.xml_filename
                )
                
                if success:
                    self.log(f"XML файл сохранён: {result_path}", "SUCCESS")
                    xml_generation_success = True
                else:
                    self.log(f"Ошибка сохранения XML: {result_path}", "ERROR")
            elif self._stop_requested:
                self.log("Обработка была остановлена пользователем", "WARNING")
            else:
                self.log("Не удалось обработать ни одного мода", "WARNING")
            
            # Удаление модов в режиме 2 после успешной генерации XML
            if self.work_mode == WorkMode.TEMPORARY and xml_generation_success:
                self._cleanup_downloaded_mods(downloaded_mods, processed)
            
            # Финальный сигнал
            if xml_generation_success:
                self.finished_signal.emit(
                    True,
                    f"Обработка завершена!\n"
                    f"Обработано: {processed}\n"
                    f"Пропущено (кэш): {skipped}\n"
                    f"Ошибок: {errors}\n"
                    f"Файл: {result_path}"
                )
            elif self._stop_requested:
                self.finished_signal.emit(False, "Обработка была остановлена")
            else:
                self.finished_signal.emit(False, "Не удалось обработать ни одного мода")
                
        except Exception as e:
            self.log(f"Критическая ошибка: {str(e)}", "ERROR")
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
    
    def _cleanup_downloaded_mods(self, downloaded_mods: List[str], processed_count: int) -> None:
        """
        Удаление скачанных модов после успешной обработки (режим 2).
        
        Args:
            downloaded_mods: Список workshop ID модов для удаления
            processed_count: Количество успешно обработанных модов
        """
        if not downloaded_mods:
            self.log("Нет модов для удаления", "INFO")
            return
        
        self.log("=" * 50, "INFO")
        self.log("НАЧАЛО УДАЛЕНИЯ СКАЧАННЫХ МОДОВ (Режим 2)", "INFO")
        self.log("=" * 50, "INFO")
        
        deleted_count = 0
        failed_count = 0
        
        for workshop_id in downloaded_mods:
            mod_path = self.steam_handler.get_mod_path(workshop_id)
            if mod_path and os.path.exists(mod_path):
                self.log(f"Удаление мода {workshop_id}...", "INFO")
                self.log(f"  Путь: {mod_path}", "DEBUG")
                
                try:
                    # Получаем список файлов для логирования
                    files_to_delete = []
                    for root, dirs, files in os.walk(mod_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            files_to_delete.append(os.path.relpath(full_path, mod_path))
                    
                    if files_to_delete:
                        self.log(f"  Файлы для удаления ({len(files_to_delete)}):", "DEBUG")
                        for rel_path in files_to_delete[:5]:  # Показываем первые 5
                            self.log(f"    - {rel_path}", "DEBUG")
                        if len(files_to_delete) > 5:
                            self.log(f"    ... и ещё {len(files_to_delete) - 5} файлов", "DEBUG")
                    
                    # Удаляем мод
                    if self.steam_handler.delete_mod(workshop_id):
                        self.log(f"Мод {workshop_id} успешно удалён", "SUCCESS")
                        deleted_count += 1
                    else:
                        self.log(f"Не удалось удалить мод {workshop_id}", "WARNING")
                        failed_count += 1
                        
                except Exception as e:
                    self.log(f"Ошибка при удалении мода {workshop_id}: {str(e)}", "ERROR")
                    failed_count += 1
            else:
                self.log(f"Мод {workshop_id} не найден для удаления (уже удалён?)", "DEBUG")
                deleted_count += 1  # Считаем как удалённый
        
        self.log("=" * 50, "INFO")
        self.log("УДАЛЕНИЕ МОДОВ ЗАВЕРШЕНО", "INFO")
        self.log(f"  Удалено: {deleted_count}", "SUCCESS")
        if failed_count > 0:
            self.log(f"  Не удалось удалить: {failed_count}", "WARNING")
        self.log("=" * 50, "INFO")


class MainWindow(QMainWindow):
    """
    Главное окно приложения RimWorld Mod Collector.
    Реализует тёмный неоновый интерфейс с разделением на панели.
    """
    
    def __init__(self):
        super().__init__()
        
        # Инициализация менеджера настроек
        self.settings = SettingsManager()
        
        # Рабочий поток
        self.worker: Optional[WorkerThread] = None
        
        # Настройка окна
        self.setWindowTitle("RimWorld Mod Collector")
        self.setMinimumSize(1000, 600)
        self.resize(
            self.settings.settings.window_width,
            self.settings.settings.window_height
        )
        
        # Применение стилей
        self.setStyleSheet(get_main_stylesheet())
        
        # Создание интерфейса
        self._create_ui()
        
        # Загрузка сохранённых настроек
        self._load_settings()
    
    def _create_ui(self) -> None:
        """Создание пользовательского интерфейса."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Создание сплиттера для изменения размеров панелей
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель (75%)
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Правая панель (25%)
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Установка пропорций
        splitter.setSizes([750, 250])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """Создание левой панели с настройками."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("🎮 RimWorld Mod Collector")
        title.setProperty("class", "title")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS["neon_cyan"]};
            padding: 10px;
        """)
        layout.addWidget(title)
        
        # Группа: Ссылка на коллекцию
        collection_group = QGroupBox("📦 Steam Workshop Коллекция")
        collection_layout = QVBoxLayout(collection_group)
        
        self.collection_input = QLineEdit()
        self.collection_input.setPlaceholderText(
            "Вставьте ссылку на коллекцию Steam Workshop..."
        )
        collection_layout.addWidget(self.collection_input)
        
        layout.addWidget(collection_group)
        
        # Группа: Настройки вывода
        output_group = QGroupBox("💾 Настройки сохранения")
        output_layout = QVBoxLayout(output_group)
        
        # Путь сохранения
        path_layout = QHBoxLayout()
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Путь для сохранения XML файла...")
        path_layout.addWidget(self.output_path_input)
        
        browse_btn = QPushButton("📁 Обзор")
        browse_btn.clicked.connect(self._browse_output_path)
        browse_btn.setFixedWidth(100)
        path_layout.addWidget(browse_btn)
        
        output_layout.addLayout(path_layout)
        
        # Имя файла
        filename_layout = QHBoxLayout()
        filename_label = QLabel("Имя файла:")
        filename_label.setFixedWidth(80)
        filename_layout.addWidget(filename_label)
        
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("ModList")
        filename_layout.addWidget(self.filename_input)
        
        output_layout.addLayout(filename_layout)
        
        layout.addWidget(output_group)
        
        # Группа: SteamCMD
        steamcmd_group = QGroupBox("⚙️ SteamCMD")
        steamcmd_layout = QHBoxLayout(steamcmd_group)
        
        self.steamcmd_input = QLineEdit()
        self.steamcmd_input.setPlaceholderText("Путь к steamcmd.exe...")
        steamcmd_layout.addWidget(self.steamcmd_input)
        
        steamcmd_browse_btn = QPushButton("📁 Обзор")
        steamcmd_browse_btn.clicked.connect(self._browse_steamcmd)
        steamcmd_browse_btn.setFixedWidth(100)
        steamcmd_layout.addWidget(steamcmd_browse_btn)
        
        layout.addWidget(steamcmd_group)
        
        # Группа: Режим работы
        mode_group = QGroupBox("🔄 Режим работы")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup()
        
        # Режим 1
        self.mode1_radio = QRadioButton(
            "Режим 1: Постоянный (моды сохраняются в кэше)"
        )
        self.mode1_radio.setChecked(True)
        self.mode_group.addButton(self.mode1_radio, 1)
        mode_layout.addWidget(self.mode1_radio)
        
        # Папка для постоянного хранения модов (Режим 1)
        mode1_path_layout = QHBoxLayout()
        mode1_path_label = QLabel("  Папка модов:")
        mode1_path_label.setFixedWidth(100)
        mode1_path_layout.addWidget(mode1_path_label)
        
        self.mods_path_input = QLineEdit()
        self.mods_path_input.setPlaceholderText("Папка для постоянного хранения модов...")
        mode1_path_layout.addWidget(self.mods_path_input)
        
        mods_path_browse_btn = QPushButton("📁")
        mods_path_browse_btn.clicked.connect(self._browse_mods_path)
        mods_path_browse_btn.setFixedWidth(40)
        mode1_path_layout.addWidget(mods_path_browse_btn)
        
        mode_layout.addLayout(mode1_path_layout)
        
        # Режим 2
        self.mode2_radio = QRadioButton(
            "Режим 2: Временный (моды удаляются после обработки)"
        )
        self.mode_group.addButton(self.mode2_radio, 2)
        mode_layout.addWidget(self.mode2_radio)
        
        # Временная папка для загрузки (Режим 2)
        mode2_path_layout = QHBoxLayout()
        mode2_path_label = QLabel("  Временная папка:")
        mode2_path_label.setFixedWidth(100)
        mode2_path_layout.addWidget(mode2_path_label)
        
        self.temp_path_input = QLineEdit()
        self.temp_path_input.setPlaceholderText("Временная папка для загрузки модов...")
        mode2_path_layout.addWidget(self.temp_path_input)
        
        temp_path_browse_btn = QPushButton("📁")
        temp_path_browse_btn.clicked.connect(self._browse_temp_path)
        temp_path_browse_btn.setFixedWidth(40)
        mode2_path_layout.addWidget(temp_path_browse_btn)
        
        mode_layout.addLayout(mode2_path_layout)
        
        # Подключение сигналов для обновления состояния полей
        self.mode1_radio.toggled.connect(self._update_path_fields_state)
        self.mode2_radio.toggled.connect(self._update_path_fields_state)
        
        layout.addWidget(mode_group)
        
        # Прогресс-бар
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("сейчас обрабатывается %v / %m мод")
        progress_layout.addWidget(self.progress_bar)
        
        # Статистика
        self.stats_label = QLabel("Обработано: 0 | Пропущено: 0 | Ошибок: 0")
        self.stats_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        progress_layout.addWidget(self.stats_label)
        
        layout.addLayout(progress_layout)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Запустить")
        self.start_btn.setProperty("class", "primary")
        self.start_btn.clicked.connect(self._start_processing)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_processing)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)
        
        self.open_folder_btn = QPushButton("📂 Открыть папку")
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        buttons_layout.addWidget(self.open_folder_btn)
        
        layout.addLayout(buttons_layout)
        
        # Растягивающийся элемент
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Создание правой панели с логами."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Заголовок логов
        header_layout = QHBoxLayout()
        
        logs_title = QLabel("📋 Логи")
        logs_title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS["neon_purple"]};
        """)
        header_layout.addWidget(logs_title)
        
        header_layout.addStretch()
        
        # Размер шрифта
        font_label = QLabel("Шрифт:")
        font_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(font_label)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.settings.log_font_size)
        self.font_size_spin.valueChanged.connect(self._update_log_font_size)
        self.font_size_spin.setFixedWidth(60)
        header_layout.addWidget(self.font_size_spin)
        
        layout.addLayout(header_layout)
        
        # Текстовое поле логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", self.settings.log_font_size))
        layout.addWidget(self.log_text)
        
        # Кнопки управления логами
        log_buttons_layout = QHBoxLayout()
        
        clear_logs_btn = QPushButton("🗑️ Очистить")
        clear_logs_btn.clicked.connect(self._clear_logs)
        log_buttons_layout.addWidget(clear_logs_btn)
        
        copy_logs_btn = QPushButton("📋 Копировать")
        copy_logs_btn.clicked.connect(self._copy_logs)
        log_buttons_layout.addWidget(copy_logs_btn)
        
        layout.addLayout(log_buttons_layout)
        
        # Чекбокс расширенного логирования
        self.verbose_checkbox = QCheckBox("Расширенное логирование")
        self.verbose_checkbox.setChecked(self.settings.verbose_logging)
        layout.addWidget(self.verbose_checkbox)
        
        return panel
    
    def _load_settings(self) -> None:
        """Загрузка сохранённых настроек в UI."""
        self.steamcmd_input.setText(self.settings.steamcmd_path)
        self.output_path_input.setText(self.settings.output_path)
        self.filename_input.setText(self.settings.xml_filename)
        self.collection_input.setText(self.settings.settings.last_collection_url)
        
        # Загрузка путей для загрузки модов
        self.mods_path_input.setText(self.settings.mods_download_path)
        self.temp_path_input.setText(self.settings.temp_download_path)
        
        if self.settings.work_mode == WorkMode.PERSISTENT:
            self.mode1_radio.setChecked(True)
        else:
            self.mode2_radio.setChecked(True)
        
        self.font_size_spin.setValue(self.settings.log_font_size)
        self.verbose_checkbox.setChecked(self.settings.verbose_logging)
        
        # Обновление состояния полей путей
        self._update_path_fields_state()
    
    def _save_settings(self) -> None:
        """Сохранение текущих настроек."""
        self.settings.steamcmd_path = self.steamcmd_input.text()
        self.settings.output_path = self.output_path_input.text()
        self.settings.xml_filename = self.filename_input.text() or "ModList"
        self.settings.settings.last_collection_url = self.collection_input.text()
        
        # Сохранение путей для загрузки модов
        self.settings.mods_download_path = self.mods_path_input.text()
        self.settings.temp_download_path = self.temp_path_input.text()
        
        if self.mode1_radio.isChecked():
            self.settings.work_mode = WorkMode.PERSISTENT
        else:
            self.settings.work_mode = WorkMode.TEMPORARY
        
        self.settings.log_font_size = self.font_size_spin.value()
        self.settings.verbose_logging = self.verbose_checkbox.isChecked()
        
        # Сохранение размеров окна
        self.settings.settings.window_width = self.width()
        self.settings.settings.window_height = self.height()
        
        self.settings.save_settings()
    
    def _browse_output_path(self) -> None:
        """Выбор папки для сохранения XML."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения XML",
            self.output_path_input.text()
        )
        if path:
            self.output_path_input.setText(path)
    
    def _browse_steamcmd(self) -> None:
        """Выбор файла steamcmd."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите steamcmd.exe",
            self.steamcmd_input.text(),
            "Executable (*.exe);;All Files (*)"
        )
        if path:
            self.steamcmd_input.setText(path)
    
    def _browse_mods_path(self) -> None:
        """Выбор папки для постоянного хранения модов (Режим 1)."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для хранения модов",
            self.mods_path_input.text()
        )
        if path:
            self.mods_path_input.setText(path)
    
    def _browse_temp_path(self) -> None:
        """Выбор временной папки для загрузки модов (Режим 2)."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите временную папку для загрузки",
            self.temp_path_input.text()
        )
        if path:
            self.temp_path_input.setText(path)
    
    def _update_path_fields_state(self) -> None:
        """Обновление состояния полей путей в зависимости от выбранного режима."""
        mode1_selected = self.mode1_radio.isChecked()
        
        # Режим 1: поле модов активно, временное неактивно
        self.mods_path_input.setEnabled(mode1_selected)
        self.temp_path_input.setEnabled(not mode1_selected)
        
        # Визуальное выделение активного поля
        if mode1_selected:
            self.mods_path_input.setStyleSheet("")
            self.temp_path_input.setStyleSheet(f"color: {COLORS['text_muted']};")
        else:
            self.mods_path_input.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.temp_path_input.setStyleSheet("")
    
    def _get_current_download_path(self) -> str:
        """Получить путь загрузки в зависимости от выбранного режима."""
        if self.mode1_radio.isChecked():
            return self.mods_path_input.text().strip()
        else:
            return self.temp_path_input.text().strip()
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Добавление сообщения в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = get_log_html_style(level, message, timestamp)
        
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.insertHtml(html)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def _clear_logs(self) -> None:
        """Очистка логов."""
        self.log_text.clear()
    
    def _copy_logs(self) -> None:
        """Копирование логов в буфер обмена."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        self._log("Логи скопированы в буфер обмена", "INFO")
    
    def _update_log_font_size(self, size: int) -> None:
        """Обновление размера шрифта логов."""
        font = self.log_text.font()
        font.setPointSize(size)
        self.log_text.setFont(font)
    
    def _open_output_folder(self) -> None:
        """Открытие папки с результатами."""
        path = self.output_path_input.text()
        if path and os.path.exists(path):
            os.startfile(path) if os.name == 'nt' else os.system(f'xdg-open "{path}"')
        else:
            QMessageBox.warning(
                self,
                "Папка не найдена",
                "Указанная папка не существует."
            )
    
    def _validate_inputs(self) -> tuple[bool, str]:
        """Проверка введённых данных."""
        if not self.collection_input.text().strip():
            return False, "Введите ссылку на коллекцию Steam Workshop"
        
        if not self.steamcmd_input.text().strip():
            return False, "Укажите путь к steamcmd"
        
        if not os.path.exists(self.steamcmd_input.text()):
            return False, "Файл steamcmd не найден"
        
        if not self.output_path_input.text().strip():
            return False, "Укажите путь для сохранения XML"
        
        return True, ""
    
    def _start_processing(self) -> None:
        """Запуск обработки коллекции."""
        # Проверка, не запущен ли уже процесс
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Процесс уже запущен",
                "Дождитесь завершения текущей обработки или остановите её."
            )
            return
        
        # Валидация
        valid, error = self._validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Ошибка", error)
            return
        
        # Сохранение настроек
        self._save_settings()
        
        # Определение режима работы
        work_mode = WorkMode.PERSISTENT if self.mode1_radio.isChecked() else WorkMode.TEMPORARY
        
        # Получение пути загрузки в зависимости от режима
        download_path = self._get_current_download_path()
        
        # Создание и запуск рабочего потока
        self.worker = WorkerThread(
            collection_url=self.collection_input.text().strip(),
            steamcmd_path=self.steamcmd_input.text().strip(),
            output_path=self.output_path_input.text().strip(),
            xml_filename=self.filename_input.text().strip() or "ModList",
            work_mode=work_mode,
            download_path=download_path,
            include_workshop_ids=True,
            verbose=self.verbose_checkbox.isChecked()
        )
        
        # Подключение сигналов
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_processing_finished)
        self.worker.stats_signal.connect(self._update_stats)
        
        # Обновление UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Запуск
        self.worker.start()
        self._log("Запуск обработки...", "INFO")
    
    def _stop_processing(self) -> None:
        """Остановка обработки."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._log("Запрос на остановку отправлен...", "WARNING")
    
    def _update_progress(self, current: int, total: int) -> None:
        """Обновление прогресс-бара."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current} / {total} модов")
    
    def _update_stats(self, processed: int, skipped: int, errors: int) -> None:
        """Обновление статистики."""
        self.stats_label.setText(
            f"Обработано: {processed} | Пропущено: {skipped} | Ошибок: {errors}"
        )
    
    def _on_processing_finished(self, success: bool, message: str) -> None:
        """Обработка завершения работы."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self._log("Обработка успешно завершена!", "SUCCESS")
            QMessageBox.information(self, "Готово", message)
        else:
            self._log(f"Обработка завершена с ошибкой: {message}", "ERROR")
            QMessageBox.warning(self, "Ошибка", message)
    
    def closeEvent(self, event) -> None:
        """Обработка закрытия окна."""
        # Остановка рабочего потока
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        
        # Сохранение настроек
        self._save_settings()
        
        event.accept()


def main():
    """Точка входа в приложение."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Установка иконки приложения (если есть)
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
