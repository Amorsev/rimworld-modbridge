"""
Модуль базы данных для хранения информации о модах.
Использует SQLite для локального хранения связи workshop_id -> package_id.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ModRecord:
    """Запись о моде в базе данных."""
    workshop_id: str
    package_id: str
    processed_date: str
    collection_url: Optional[str] = None


class ModDatabase:
    """
    Класс для работы с базой данных модов.
    Хранит связь между workshop ID и package ID для предотвращения
    повторной загрузки и обработки модов.
    """
    
    def __init__(self, db_path: str = "mods_cache.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """Создание таблиц базы данных, если они не существуют."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица для хранения информации о модах
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mods (
                    workshop_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    processed_date TEXT NOT NULL,
                    collection_url TEXT
                )
            """)
            
            # Индекс для быстрого поиска по package_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_package_id 
                ON mods(package_id)
            """)
            
            conn.commit()
    
    def get_package_id(self, workshop_id: str) -> Optional[str]:
        """
        Получить package_id по workshop_id.
        
        Args:
            workshop_id: Числовой ID мода в Steam Workshop.
            
        Returns:
            package_id если мод найден в базе, иначе None.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT package_id FROM mods WHERE workshop_id = ?",
                (workshop_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def add_mod(self, workshop_id: str, package_id: str, 
                collection_url: Optional[str] = None) -> None:
        """
        Добавить или обновить запись о моде.
        
        Args:
            workshop_id: Числовой ID мода в Steam Workshop.
            package_id: Идентификатор пакета из About.xml.
            collection_url: URL коллекции, из которой был получен мод.
        """
        processed_date = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO mods 
                (workshop_id, package_id, processed_date, collection_url)
                VALUES (?, ?, ?, ?)
            """, (workshop_id, package_id, processed_date, collection_url))
            conn.commit()
    
    def mod_exists(self, workshop_id: str) -> bool:
        """
        Проверить, существует ли мод в базе данных.
        
        Args:
            workshop_id: Числовой ID мода в Steam Workshop.
            
        Returns:
            True если мод найден, иначе False.
        """
        return self.get_package_id(workshop_id) is not None
    
    def get_all_mods(self) -> List[ModRecord]:
        """
        Получить все записи о модах из базы данных.
        
        Returns:
            Список всех записей ModRecord.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT workshop_id, package_id, processed_date, collection_url FROM mods"
            )
            results = cursor.fetchall()
            return [
                ModRecord(
                    workshop_id=row[0],
                    package_id=row[1],
                    processed_date=row[2],
                    collection_url=row[3]
                )
                for row in results
            ]
    
    def get_mods_by_workshop_ids(self, workshop_ids: List[str]) -> dict:
        """
        Получить package_id для списка workshop_id.
        
        Args:
            workshop_ids: Список workshop ID для поиска.
            
        Returns:
            Словарь {workshop_id: package_id} для найденных модов.
        """
        if not workshop_ids:
            return {}
        
        placeholders = ",".join("?" * len(workshop_ids))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT workshop_id, package_id FROM mods WHERE workshop_id IN ({placeholders})",
                workshop_ids
            )
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
    
    def delete_mod(self, workshop_id: str) -> bool:
        """
        Удалить запись о моде из базы данных.
        
        Args:
            workshop_id: Числовой ID мода в Steam Workshop.
            
        Returns:
            True если запись была удалена, False если не найдена.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM mods WHERE workshop_id = ?",
                (workshop_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_database(self) -> int:
        """
        Очистить всю базу данных.
        
        Returns:
            Количество удалённых записей.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM mods")
            count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM mods")
            conn.commit()
            return count
    
    def get_stats(self) -> dict:
        """
        Получить статистику базы данных.
        
        Returns:
            Словарь со статистикой (количество модов, дата последнего обновления и т.д.)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Общее количество модов
            cursor.execute("SELECT COUNT(*) FROM mods")
            total_count = cursor.fetchone()[0]
            
            # Дата последнего добавления
            cursor.execute(
                "SELECT MAX(processed_date) FROM mods"
            )
            last_update = cursor.fetchone()[0]
            
            return {
                "total_mods": total_count,
                "last_update": last_update,
                "database_path": self.db_path
            }


# Пример использования
if __name__ == "__main__":
    db = ModDatabase()
    
    # Добавление тестового мода
    db.add_mod("123456789", "author.modname", "https://steamcommunity.com/...")
    
    # Проверка существования
    print(f"Мод существует: {db.mod_exists('123456789')}")
    
    # Получение package_id
    print(f"Package ID: {db.get_package_id('123456789')}")
    
    # Статистика
    print(f"Статистика: {db.get_stats()}")
