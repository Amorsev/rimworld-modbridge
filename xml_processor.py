"""
Модуль для обработки XML файлов модов RimWorld.
Извлекает packageId из About.xml и генерирует XML для RimPy.
"""

import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModInfo:
    """Информация о моде, извлечённая из About.xml."""
    workshop_id: str
    package_id: str
    name: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None


class XmlParseError(Exception):
    """Исключение для ошибок парсинга XML."""
    pass


class XmlProcessor:
    """
    Класс для обработки XML файлов модов RimWorld.
    Извлекает информацию из About.xml и генерирует XML для RimPy.
    """
    
    # Возможные пути к файлу About.xml (с учётом регистра)
    ABOUT_XML_PATHS = [
        "About/About.xml",
        "about/About.xml",
        "About/about.xml",
        "about/about.xml",
        "About.xml",
        "about.xml"
    ]
    
    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Инициализация процессора XML.
        
        Args:
            log_callback: Функция обратного вызова для логирования (message, level).
        """
        self.log_callback = log_callback
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """
        Логирование сообщения.
        
        Args:
            message: Текст сообщения.
            level: Уровень логирования.
        """
        if self.log_callback:
            self.log_callback(message, level)
    
    def find_about_xml(self, mod_path: str) -> Optional[str]:
        """
        Найти файл About.xml в папке мода.
        
        Args:
            mod_path: Путь к папке мода.
            
        Returns:
            Полный путь к About.xml или None если не найден.
        """
        for relative_path in self.ABOUT_XML_PATHS:
            full_path = os.path.join(mod_path, relative_path)
            if os.path.exists(full_path):
                return full_path
        
        # Поиск без учёта регистра (для Linux/Mac)
        for root, dirs, files in os.walk(mod_path):
            for file in files:
                if file.lower() == "about.xml":
                    parent_dir = os.path.basename(root).lower()
                    if parent_dir == "about" or root == mod_path:
                        return os.path.join(root, file)
        
        return None
    
    def extract_package_id(self, mod_path: str, workshop_id: str) -> Optional[ModInfo]:
        """
        Извлечь packageId из About.xml мода.
        
        Args:
            mod_path: Путь к папке мода.
            workshop_id: ID мода в Steam Workshop.
            
        Returns:
            ModInfo с информацией о моде или None при ошибке.
        """
        about_xml_path = self.find_about_xml(mod_path)
        
        if not about_xml_path:
            self._log(
                f"Файл About.xml не найден для мода {workshop_id}", 
                "WARNING"
            )
            return None
        
        try:
            # Чтение и парсинг XML
            tree = ET.parse(about_xml_path)
            root = tree.getroot()
            
            # Поиск packageId (без учёта регистра тега)
            package_id = None
            name = None
            author = None
            description = None
            
            for elem in root:
                tag_lower = elem.tag.lower()
                
                if tag_lower == "packageid":
                    package_id = elem.text
                elif tag_lower == "name":
                    name = elem.text
                elif tag_lower == "author":
                    author = elem.text
                elif tag_lower == "description":
                    description = elem.text
            
            if not package_id:
                self._log(
                    f"Тег packageId не найден в About.xml мода {workshop_id}", 
                    "WARNING"
                )
                return None
            
            # Приведение packageId к нижнему регистру
            package_id_lower = package_id.strip().lower()
            
            self._log(
                f"Извлечён packageId для мода {workshop_id}: {package_id_lower}", 
                "DEBUG"
            )
            
            return ModInfo(
                workshop_id=workshop_id,
                package_id=package_id_lower,
                name=name,
                author=author,
                description=description
            )
            
        except ET.ParseError as e:
            self._log(
                f"Ошибка парсинга XML для мода {workshop_id}: {str(e)}", 
                "ERROR"
            )
            return None
        except Exception as e:
            self._log(
                f"Неожиданная ошибка при обработке мода {workshop_id}: {str(e)}", 
                "ERROR"
            )
            return None
    
    def generate_rimpy_xml(
        self, 
        mod_infos: List[ModInfo],
        list_name: str = "ModList"
    ) -> str:
        """
        Сгенерировать XML файл, совместимый с RimPy.
        
        Args:
            mod_infos: Список информации о модах.
            list_name: Название списка модов.
            
        Returns:
            Строка с XML содержимым.
        """
        # Создание корневого элемента
        root = ET.Element("ModList")
        
        # Добавление метаданных
        name_elem = ET.SubElement(root, "Name")
        name_elem.text = list_name
        
        # Добавление версии (для совместимости с RimPy)
        version_elem = ET.SubElement(root, "Version")
        version_elem.text = "1.0"
        
        # Создание списка модов
        mods_elem = ET.SubElement(root, "Mods")
        
        for mod_info in mod_infos:
            mod_elem = ET.SubElement(mods_elem, "li")
            mod_elem.text = mod_info.package_id
        
        # Форматирование XML с отступами
        xml_string = ET.tostring(root, encoding="unicode")
        
        # Добавление XML декларации и форматирование
        dom = minidom.parseString(xml_string)
        formatted_xml = dom.toprettyxml(indent="  ", encoding=None)
        
        # Удаление лишней пустой строки после декларации
        lines = formatted_xml.split('\n')
        if lines[1].strip() == '':
            lines.pop(1)
        
        return '\n'.join(lines)
    
    def generate_rimpy_xml_extended(
        self, 
        mod_infos: List[ModInfo],
        list_name: str = "ModList",
        include_workshop_ids: bool = True
    ) -> str:
        """
        Сгенерировать расширенный XML файл с дополнительной информацией.
        
        Args:
            mod_infos: Список информации о модах.
            list_name: Название списка модов.
            include_workshop_ids: Включать ли workshop ID в комментарии.
            
        Returns:
            Строка с XML содержимым.
        """
        lines = ['<?xml version="1.0" encoding="utf-8"?>']
        lines.append('<ModList>')
        lines.append(f'  <Name>{list_name}</Name>')
        lines.append('  <Version>1.0</Version>')
        lines.append('  <Mods>')
        
        for mod_info in mod_infos:
            if include_workshop_ids:
                comment = f"    <!-- Workshop ID: {mod_info.workshop_id}"
                if mod_info.name:
                    comment += f" | {mod_info.name}"
                comment += " -->"
                lines.append(comment)
            lines.append(f'    <li>{mod_info.package_id}</li>')
        
        lines.append('  </Mods>')
        lines.append('</ModList>')
        
        return '\n'.join(lines)
    
    def generate_mods_config_data_xml(
        self,
        mod_infos: List[ModInfo],
        version: str = "1.6.4633",
        include_workshop_ids: bool = True
    ) -> str:
        """
        Сгенерировать XML файл в формате ModsConfigData (RimWorld native).
        
        Формат аналогичен WitcherRimworld.xml:
        <?xml version="1.0" encoding="utf-8"?>
        <ModsConfigData>
            <version>1.6.4633</version>
            <activeMods>
                <li>packageId1</li>
                <li>packageId2</li>
            </activeMods>
            <knownExpansions>
                <li>ludeon.rimworld</li>
                ...
            </knownExpansions>
        </ModsConfigData>
        
        Args:
            mod_infos: Список информации о модах.
            version: Версия RimWorld.
            include_workshop_ids: Включать ли workshop ID в комментарии.
            
        Returns:
            Строка с XML содержимым.
        """
        lines = ['<?xml version="1.0" encoding="utf-8"?>']
        lines.append('<ModsConfigData>')
        lines.append(f'    <version>{version}</version>')
        lines.append('    <activeMods>')
        
        for mod_info in mod_infos:
            if include_workshop_ids and mod_info.workshop_id:
                comment = f"        <!-- Workshop ID: {mod_info.workshop_id}"
                if mod_info.name:
                    comment += f" | {mod_info.name}"
                comment += " -->"
                lines.append(comment)
            lines.append(f'        <li>{mod_info.package_id}</li>')
        
        lines.append('    </activeMods>')
        
        # knownExpansions - базовые DLC RimWorld
        lines.append('    <knownExpansions>')
        lines.append('        <li>ludeon.rimworld</li>')
        lines.append('        <li>ludeon.rimworld.royalty</li>')
        lines.append('        <li>ludeon.rimworld.ideology</li>')
        lines.append('        <li>ludeon.rimworld.biotech</li>')
        lines.append('        <li>ludeon.rimworld.anomaly</li>')
        lines.append('    </knownExpansions>')
        
        lines.append('</ModsConfigData>')
        
        return '\n'.join(lines)
    
    def save_xml(
        self, 
        xml_content: str, 
        output_path: str,
        filename: str
    ) -> Tuple[bool, str]:
        """
        Сохранить XML файл.
        
        Args:
            xml_content: Содержимое XML.
            output_path: Путь к директории для сохранения.
            filename: Имя файла (без расширения или с .xml).
            
        Returns:
            Кортеж (успех, полный путь к файлу или сообщение об ошибке).
        """
        try:
            # Создание директории если не существует
            os.makedirs(output_path, exist_ok=True)
            
            # Добавление расширения если отсутствует
            if not filename.lower().endswith('.xml'):
                filename += '.xml'
            
            full_path = os.path.join(output_path, filename)
            
            # Запись файла
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            self._log(f"XML файл сохранён: {full_path}", "SUCCESS")
            return True, full_path
            
        except PermissionError:
            error_msg = f"Нет прав на запись в директорию: {output_path}"
            self._log(error_msg, "ERROR")
            return False, error_msg
        except Exception as e:
            error_msg = f"Ошибка сохранения XML: {str(e)}"
            self._log(error_msg, "ERROR")
            return False, error_msg
    
    def validate_xml_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Проверить валидность XML файла.
        
        Args:
            file_path: Путь к XML файлу.
            
        Returns:
            Кортеж (валидность, сообщение).
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            if root.tag != "ModList":
                return False, "Корневой элемент должен быть 'ModList'"
            
            mods_elem = root.find("Mods")
            if mods_elem is None:
                return False, "Отсутствует элемент 'Mods'"
            
            mod_count = len(list(mods_elem))
            return True, f"XML валиден, содержит {mod_count} модов"
            
        except ET.ParseError as e:
            return False, f"Ошибка парсинга XML: {str(e)}"
        except Exception as e:
            return False, f"Ошибка проверки: {str(e)}"
    
    def parse_existing_rimpy_xml(self, file_path: str) -> List[str]:
        """
        Прочитать существующий RimPy XML и извлечь packageId.
        
        Args:
            file_path: Путь к XML файлу.
            
        Returns:
            Список packageId из файла.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            mods_elem = root.find("Mods")
            if mods_elem is None:
                return []
            
            package_ids = []
            for li in mods_elem.findall("li"):
                if li.text:
                    package_ids.append(li.text.strip().lower())
            
            return package_ids
            
        except Exception as e:
            self._log(f"Ошибка чтения XML: {str(e)}", "ERROR")
            return []


# Пример использования
if __name__ == "__main__":
    processor = XmlProcessor(
        log_callback=lambda msg, lvl: print(f"[{lvl}] {msg}")
    )
    
    # Тестовые данные
    test_mods = [
        ModInfo("123456", "author.testmod1", "Test Mod 1"),
        ModInfo("789012", "another.testmod2", "Test Mod 2"),
    ]
    
    # Генерация XML
    xml_content = processor.generate_rimpy_xml(test_mods, "TestCollection")
    print("Сгенерированный XML:")
    print(xml_content)
    
    # Расширенный XML
    xml_extended = processor.generate_rimpy_xml_extended(test_mods, "TestCollection")
    print("\nРасширенный XML:")
    print(xml_extended)
