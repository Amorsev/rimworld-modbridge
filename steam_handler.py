"""
Модуль для работы со Steam Workshop и steamcmd.
Загрузка модов, парсинг коллекций и управление процессами.
Вдохновлён example/main.py с совместимостью с main.py.
"""

import os
import re
import subprocess
import shutil
import tempfile
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import time


# RimWorld App ID в Steam
RIMWORLD_APP_ID = "294100"

# Таймауты
DEFAULT_DOWNLOAD_TIMEOUT = 300  # 5 минут


class DownloadStatus(Enum):
    """Статус загрузки мода."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"
    TIMEOUT = "timeout"


@dataclass
class DownloadResult:
    """Результат загрузки мода."""
    workshop_id: str
    status: DownloadStatus
    mod_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class CollectionInfo:
    """Информация о коллекции Steam Workshop."""
    collection_id: str
    title: Optional[str] = None
    mod_ids: List[str] = None
    
    def __post_init__(self):
        if self.mod_ids is None:
            self.mod_ids = []


class SteamCmdError(Exception):
    """Исключение для ошибок steamcmd."""
    pass


class CollectionParseError(Exception):
    """Исключение для ошибок парсинга коллекции."""
    pass


class SteamHandler:
    """
    Класс для работы со Steam Workshop.
    Управляет загрузкой модов через steamcmd и парсингом коллекций.
    """
    
    def __init__(
        self,
        steamcmd_path: str,
        download_dir: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Инициализация обработчика Steam.
        
        Args:
            steamcmd_path: Путь к исполняемому файлу steamcmd.
            download_dir: Директория для загрузки модов.
            log_callback: Функция обратного вызова для логирования (message, level).
        """
        self.steamcmd_path = steamcmd_path
        self._custom_download_dir = download_dir
        self.log_callback = log_callback
        self._stop_flag = None
        self._current_process = None
        
        # Путь к папке workshop (по умолчанию - Steam content)
        self._workshop_path = Path.home() / "Steam/steamapps/workshop/content/294100"
    
    @property
    def download_dir(self) -> str:
        """Получить директорию загрузки модов."""
        if self._custom_download_dir:
            return self._custom_download_dir
        return str(self._workshop_path)
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """
        Логирование сообщения.
        
        Args:
            message: Текст сообщения.
            level: Уровень логирования (INFO, WARNING, ERROR, DEBUG, SUCCESS).
        """
        if self.log_callback:
            self.log_callback(message, level)
    
    def validate_steamcmd(self) -> Tuple[bool, str]:
        """
        Проверить существование и доступность steamcmd.
        
        Returns:
            Кортеж (успех, сообщение).
        """
        if not self.steamcmd_path:
            return False, "Путь к steamcmd не указан"
        
        if not os.path.exists(self.steamcmd_path):
            return False, f"Файл steamcmd не найден: {self.steamcmd_path}"
        
        if not os.path.isfile(self.steamcmd_path):
            return False, f"Указанный путь не является файлом: {self.steamcmd_path}"
        
        # Проверка расширения для Windows
        if os.name == 'nt' and not self.steamcmd_path.lower().endswith('.exe'):
            return False, "Для Windows требуется файл steamcmd.exe"
        
        return True, "steamcmd найден и доступен"
    
    @staticmethod
    def validate_collection_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить корректность ссылки на Steam коллекцию.
        
        Args:
            url: URL коллекции Steam Workshop.
            
        Returns:
            Кортеж (валидность, ID коллекции или None).
        """
        # Паттерны для различных форматов URL
        patterns = [
            r'steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)',
            r'steamcommunity\.com/workshop/filedetails/\?id=(\d+)',
            r'^(\d+)$'  # Просто числовой ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return True, match.group(1)
        
        return False, None
    
    async def fetch_collection_mods(
        self,
        collection_url: str,
        timeout: int = 30
    ) -> CollectionInfo:
        """
        Получить список модов из коллекции Steam Workshop.
        
        Args:
            collection_url: URL коллекции.
            timeout: Таймаут запроса в секундах.
            
        Returns:
            CollectionInfo с информацией о коллекции.
            
        Raises:
            CollectionParseError: При ошибке парсинга.
        """
        import asyncio
        import aiohttp
        
        is_valid, collection_id = self.validate_collection_url(collection_url)
        if not is_valid:
            raise CollectionParseError(f"Некорректный URL коллекции: {collection_url}")
        
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
        
        self._log(f"Загрузка информации о коллекции {collection_id}...", "INFO")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status != 200:
                        raise CollectionParseError(f"Ошибка HTTP {response.status}")
                    
                    html = await response.text()
                    
                    # Извлечение названия коллекции
                    title_match = re.search(
                        r'<div class="workshopItemTitle">([^<]+)</div>', 
                        html
                    )
                    title = title_match.group(1) if title_match else None
                    
                    # Извлечение ID модов из коллекции
                    mod_pattern = r'sharedfiles/filedetails/\?id=(\d+)'
                    mod_ids = list(set(re.findall(mod_pattern, html)))
                    
                    # Исключаем ID самой коллекции
                    mod_ids = [mid for mid in mod_ids if mid != collection_id]
                    
                    if not mod_ids:
                        raise CollectionParseError("Не удалось найти моды в коллекции")
                    
                    self._log(f"Найдено {len(mod_ids)} модов", "SUCCESS")
                    
                    return CollectionInfo(
                        collection_id=collection_id,
                        title=title,
                        mod_ids=mod_ids
                    )
                    
        except asyncio.TimeoutError:
            raise CollectionParseError(f"Таймаут загрузки коллекции (>{timeout} сек)")
        except aiohttp.ClientError as e:
            raise CollectionParseError(f"Ошибка сети: {str(e)}")
    
    def ensure_download_dir_exists(self) -> bool:
        """
        Создать директорию загрузки если она не существует.
        
        Returns:
            True если директория существует или была создана.
        """
        try:
            os.makedirs(self.download_dir, exist_ok=True)
            return True
        except Exception as e:
            self._log(f"Ошибка создания директории загрузки: {str(e)}", "ERROR")
            return False
    
    def set_stop_flag(self, stop_flag: Optional[Callable[[], bool]] = None):
        """
        Установить функцию проверки остановки.
        
        Args:
            stop_flag: Функция возвращающая True если нужно остановиться.
        """
        self._stop_flag = stop_flag
    
    def stop(self) -> None:
        """Остановить текущий процесс загрузки."""
        if self._current_process:
            try:
                self._current_process.terminate()
                self._log("Процесс steamcmd остановлен", "INFO")
            except Exception as e:
                self._log(f"Ошибка остановки процесса: {str(e)}", "WARNING")
    
    def create_temp_workshop_dir(self) -> str:
        """
        Создать временную директорию для загрузки модов.
        
        Returns:
            Путь к временной директории.
        """
        temp_dir = tempfile.mkdtemp(prefix="rimworld_workshop_")
        self._log(f"Создана временная директория: {temp_dir}", "DEBUG")
        return temp_dir
    
    def get_mod_path(self, workshop_id: str) -> str:
        """
        Получить путь к папке мода.
        
        Args:
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            Путь к папке мода.
        """
        # Стандартная структура: download_dir/steamapps/workshop/content/294100/{id}
        return os.path.join(
            self.download_dir, "steamapps", "workshop", "content", 
            RIMWORLD_APP_ID, workshop_id
        )
    
    def download_mod(self, workshop_id: str) -> DownloadResult:
        """
        Загрузить мод через steamcmd.
        
        Args:
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            DownloadResult с результатом загрузки.
        """
        if self._stop_flag and self._stop_flag():
            return DownloadResult(
                workshop_id=workshop_id,
                status=DownloadStatus.SKIPPED,
                error_message="Загрузка остановлена пользователем"
            )
        
        mod_path = self.get_mod_path(workshop_id)
        
        cmd = [
            self.steamcmd_path,
            '+force_install_dir', self.download_dir,
            '+login', 'anonymous',
            '+workshop_download_item', RIMWORLD_APP_ID, workshop_id,
            '+quit'
        ]
        
        # Windows: скрыть консольное окно
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        else:
            startupinfo = None
        
        try:
            self._log(f"Загрузка мода {workshop_id}...", "INFO")
            
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Ожидание завершения с проверкой остановки
            while True:
                if self._stop_flag and self._stop_flag():
                    self._current_process.terminate()
                    try:
                        self._current_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._current_process.kill()
                    self._log(f"Загрузка остановлена для мода {workshop_id}", "WARNING")
                    return DownloadResult(
                        workshop_id=workshop_id,
                        status=DownloadStatus.SKIPPED,
                        error_message="Загрузка остановлена"
                    )
                
                retcode = self._current_process.poll()
                if retcode is not None:
                    stdout, stderr = self._current_process.communicate()
                    self._current_process = None
                    
                    # Логируем вывод для отладки
                    if stdout:
                        self._log(f"steamcmd stdout: {stdout[:500]}", "DEBUG")
                    if stderr:
                        self._log(f"steamcmd stderr: {stderr[:500]}", "DEBUG")
                    
                    if retcode == 0:
                        # Проверяем что мод загружен
                        if os.path.exists(mod_path) and os.listdir(mod_path):
                            self._log(f"Мод {workshop_id} загружен: {mod_path}", "SUCCESS")
                            return DownloadResult(
                                workshop_id=workshop_id,
                                status=DownloadStatus.SUCCESS,
                                mod_path=mod_path
                            )
                        
                        # Пробуем найти в альтернативных директориях
                        alt_paths = self._find_mod_in_alternate_locations(workshop_id)
                        if alt_paths:
                            found_path = alt_paths[0]
                            self._log(f"Мод найден в альтернативном месте: {found_path}", "INFO")
                            return DownloadResult(
                                workshop_id=workshop_id,
                                status=DownloadStatus.SUCCESS,
                                mod_path=found_path
                            )
                        
                        self._log(f"Папка мода не найдена: {mod_path}", "WARNING")
                        self._log(f"Проверено: {mod_path}, альтернативы: {alt_paths}", "DEBUG")
                        return DownloadResult(
                            workshop_id=workshop_id,
                            status=DownloadStatus.FAILED,
                            error_message=f"Папка мода не создана: {mod_path}"
                        )
                    else:
                        self._log(f"Ошибка загрузки (код {retcode}): {workshop_id}", "ERROR")
                        return DownloadResult(
                            workshop_id=workshop_id,
                            status=DownloadStatus.FAILED,
                            error_message=f"steamcmd завершился с кодом {retcode}"
                        )
                
                time.sleep(0.1)
                
        except Exception as e:
            self._current_process = None
            self._log(f"Ошибка загрузки {workshop_id}: {str(e)}", "ERROR")
            return DownloadResult(
                workshop_id=workshop_id,
                status=DownloadStatus.FAILED,
                error_message=str(e)
            )
    
    def download_mod_with_steamcmd(
        self,
        mod_id: str,
        workshop_dir: str
    ) -> bool:
        """
        Загрузить мод через steamcmd (alternative method).
        
        Args:
            mod_id: ID мода в Steam Workshop.
            workshop_dir: Директория для загрузки.
            
        Returns:
            True если загрузка успешна.
        """
        cmd = [
            self.steamcmd_path,
            '+force_install_dir', str(workshop_dir),
            '+login', 'anonymous',
            '+workshop_download_item', RIMWORLD_APP_ID, mod_id,
            '+quit'
        ]
        
        # Windows: скрыть консольное окно
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        else:
            startupinfo = None
        
        try:
            self._log(f"Загрузка мода {mod_id}...", "INFO")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            while True:
                if self._stop_flag and self._stop_flag():
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self._log(f"Загрузка остановлена для мода {mod_id}", "WARNING")
                    return False
                
                retcode = process.poll()
                if retcode is not None:
                    if retcode == 0:
                        self._log(f"Загрузка успешна: {mod_id}", "SUCCESS")
                        return True
                    else:
                        self._log(f"Загрузка неудачна (код {retcode}): {mod_id}", "ERROR")
                        return False
                
                time.sleep(0.1)
                
        except Exception as e:
            self._log(f"Ошибка загрузки {mod_id}: {str(e)}", "ERROR")
            return False
    
    def _find_mod_in_alternate_locations(self, workshop_id: str) -> List[str]:
        """
        Поиск мода в альтернативных директориях.
        Steamcmd может создавать разные структуры папок.
        
        Args:
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            Список найденных путей к моду.
        """
        found_paths = []
        
        # Стандартная структура
        standard_path = os.path.join(
            self.download_dir, "steamapps", "workshop", "content", 
            RIMWORLD_APP_ID, workshop_id
        )
        if os.path.exists(standard_path) and os.listdir(standard_path):
            found_paths.append(standard_path)
        
        # downloads структура (где steamcmd реально создаёт файлы)
        downloads_path = os.path.join(
            self.download_dir, "steamapps", "workshop", "downloads",
            RIMWORLD_APP_ID, workshop_id
        )
        if os.path.exists(downloads_path) and os.listdir(downloads_path):
            found_paths.append(downloads_path)
        
        # Временная структура без steamapps
        temp_path1 = os.path.join(
            self.download_dir, "workshop", "content", 
            RIMWORLD_APP_ID, workshop_id
        )
        if os.path.exists(temp_path1) and os.listdir(temp_path1) and temp_path1 not in found_paths:
            found_paths.append(temp_path1)
        
        temp_path2 = os.path.join(
            self.download_dir, "workshop", "downloads",
            RIMWORLD_APP_ID, workshop_id
        )
        if os.path.exists(temp_path2) and os.listdir(temp_path2) and temp_path2 not in found_paths:
            found_paths.append(temp_path2)
        
        # Просто папка с ID в download_dir
        simple_path = os.path.join(self.download_dir, workshop_id)
        if os.path.exists(simple_path) and os.listdir(simple_path) and simple_path not in found_paths:
            found_paths.append(simple_path)
        
        if found_paths:
            self._log(f"Мод {workshop_id} найден в: {found_paths}", "DEBUG")
        
        return found_paths
    
    def is_mod_downloaded(self, workshop_id: str) -> bool:
        """
        Проверить, загружен ли мод.
        
        Args:
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            True если папка мода существует и не пуста.
        """
        mod_path = self.get_mod_path(workshop_id)
        return os.path.exists(mod_path) and os.listdir(mod_path)
    
    def delete_mod(self, workshop_id: str) -> bool:
        """
        Удалить загруженный мод.
        
        Args:
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            True если удаление успешно.
        """
        mod_path = self.get_mod_path(workshop_id)
        
        if not os.path.exists(mod_path):
            self._log(f"Папка мода не найдена: {mod_path}", "WARNING")
            return True  # Считаем успехом если папки нет
        
        try:
            shutil.rmtree(mod_path)
            self._log(f"Мод {workshop_id} удалён", "DEBUG")
            return True
        except Exception as e:
            self._log(f"Ошибка удаления мода {workshop_id}: {str(e)}", "ERROR")
            return False
    
    def extract_package_id(self, mod_path: str, workshop_id: str) -> Optional[str]:
        """
        Извлечь packageId из About.xml файла мода.
        
        Args:
            mod_path: Путь к папке мода.
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            packageId мода или None.
        """
        # Отладочная информация
        self._log(f"extract_package_id: mod_path={mod_path}", "DEBUG")
        self._log(f"Поиск About.xml в: {mod_path}", "DEBUG")
        
        if os.path.exists(mod_path):
            contents = os.listdir(mod_path)
            self._log(f"Содержимое папки мода: {contents}", "DEBUG")
        else:
            self._log(f"ПАПКА МОДА НЕ СУЩЕСТВУЕТ: {mod_path}", "DEBUG")
            return None
        
        # Возможные пути к About.xml (стандартные)
        about_paths = [
            os.path.join(mod_path, "About", "About.xml"),
            os.path.join(mod_path, "about", "About.xml"),
            os.path.join(mod_path, "About", "about.xml"),
            os.path.join(mod_path, "about", "about.xml"),
            os.path.join(mod_path, "About.xml"),
            os.path.join(mod_path, "about.xml"),
        ]
        
        about_xml = None
        for path in about_paths:
            if os.path.exists(path):
                about_xml = path
                self._log(f"About.xml найден по стандартному пути: {about_xml}", "DEBUG")
                break
        
        # Если не найден по стандартным путям - рекурсивный поиск по всей папке
        if not about_xml:
            self._log(f"About.xml не найден по стандартным путям, выполняем рекурсивный поиск...", "DEBUG")
            
            found_count = 0
            for root, dirs, files in os.walk(mod_path):
                for file in files:
                    if file.lower() == "about.xml":
                        found_count += 1
                        about_xml = os.path.join(root, file)
                        self._log(f"About.xml #{found_count} найден: {about_xml}", "DEBUG")
                        
                        # Проверяем что это правильный About.xml (в папке About/)
                        rel_path = os.path.relpath(about_xml, mod_path)
                        rel_path_lower = rel_path.lower()
                        
                        # About.xml должен быть в папке About/ или в корне
                        if rel_path_lower.startswith("about") or "\\" not in rel_path and "/" not in rel_path:
                            self._log(f"Используем About.xml: {about_xml}", "DEBUG")
                            break
                if about_xml:
                    break
        
        if not about_xml:
            self._log(f"About.xml не найден для {workshop_id}", "WARNING")
            return None
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(about_xml)
            root = tree.getroot()
            
            # Поиск тега packageId (без учёта регистра)
            for elem in root:
                if elem.tag.lower() == 'packageid' and elem.text:
                    package_id = elem.text.strip().lower()
                    self._log(f"packageId найден: {package_id}", "DEBUG")
                    return package_id
            
            self._log(f"Тег packageId не найден в XML для {workshop_id}", "WARNING")
            return None
            
        except Exception as e:
            self._log(f"Ошибка парсинга About.xml: {str(e)}", "ERROR")
            return None
    
    def get_downloaded_mods_list(self, workshop_dir: str) -> List[str]:
        """
        Получить список загруженных модов из директории.
        
        Args:
            workshop_dir: Путь к директории workshop.
            
        Returns:
            Список ID загруженных модов.
        """
        mods = []
        content_path = Path(workshop_dir) / "steamapps/workshop/content/294100"
        
        if not content_path.exists():
            return mods
        
        for mod_id in os.listdir(content_path):
            mod_path = content_path / mod_id
            if mod_path.is_dir() and os.listdir(mod_path):
                mods.append(mod_id)
        
        return mods
    
    def cleanup_temp_dir(self, workshop_dir: str) -> None:
        """
        Удалить временную директорию.
        
        Args:
            workshop_dir: Путь к директории для удаления.
        """
        try:
            if os.path.exists(workshop_dir):
                shutil.rmtree(workshop_dir)
                self._log(f"Удалена временная директория: {workshop_dir}", "DEBUG")
        except Exception as e:
            self._log(f"Ошибка удаления временной директории: {str(e)}", "WARNING")
