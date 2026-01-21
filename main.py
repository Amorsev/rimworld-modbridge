
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import tempfile
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import google.generativeai as genai
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "converter_config.json"

TRANSLATIONS = {
    'en': {
        'title': '🎮 RimWorld Mod Collection Converter',
        'subtitle': 'Convert Steam Workshop collections to RimPy XML format',
        'toggle_theme': '🌓 Toggle Theme',
        'log_font_size': 'Log Font Size:',
        'clear_log': '🗑️ Clear Log',
        'collection_url': '📋 Collection URL:',
        'output_file': '💾 Output File:',
        'steamcmd_path': '⚙️ SteamCMD Path:',
        'browse': '📁 Browse',
        'statistics': '📊 Conversion Statistics',
        'total_mods': 'Total Mods',
        'successful': '✅ Successful',
        'failed': '❌ Failed',
        'current': '🔄 Current',
        'start_conversion': '🚀 Start Conversion',
        'converting': '⏳ Converting...',
        'ready': 'Ready to convert',
        'conversion_log': '📝 Conversion Log',
        'language': '🌐 Language:',
        'gemini_api_key': '🔑 Gemini API Key(WIP):',
        'translate_ui': 'Translate UI',
        'translate_logs': 'Translate Logs',
        'error': 'Error',
        'success': 'Success',
        'enter_url': 'Please enter a collection URL',
        'specify_output': 'Please specify an output file',
        'conversion_complete': '🎉 Conversion complete!',
        'total': 'Total mods:',
        'file_saved': 'File saved to:',
        'conversion_failed': 'Conversion failed:',
        'cached': '📦 Cached',
    },
    'ru': {
        'title': '🎮 Конвертер коллекций модов RimWorld',
        'subtitle': 'Преобразование коллекций Steam Workshop в формат RimPy XML',
        'toggle_theme': '🌓 Сменить тему',
        'log_font_size': 'Размер шрифта логов:',
        'clear_log': '🗑️ Очистить лог',
        'collection_url': '📋 URL коллекции:',
        'output_file': '💾 Выходной файл:',
        'steamcmd_path': '⚙️ Путь SteamCMD(не менять если в path):',
        'browse': '📁 Обзор',
        'statistics': '📊 Статистика конвертации',
        'total_mods': 'Всего модов',
        'successful': '✅ Успешно',
        'failed': '❌ Провалено',
        'current': '🔄 Текущий',
        'start_conversion': '🚀 Начать конвертацию',
        'converting': '⏳ Конвертация...',
        'ready': 'Готов к конвертации',
        'conversion_log': '📝 Журнал конвертации',
        'language': '🌐 Язык:',
        'gemini_api_key': '🔑 Ключ Gemini API(функция в разработке):',
        'translate_ui': 'Перевести интерфейс',
        'translate_logs': 'Переводить логи',
        'error': 'Ошибка',
        'success': 'Успех',
        'enter_url': 'Пожалуйста, введите URL коллекции',
        'specify_output': 'Пожалуйста, укажите выходной файл',
        'conversion_complete': '🎉 Конвертация завершена!',
        'total': 'Всего модов:',
        'file_saved': 'Файл сохранен в:',
        'conversion_failed': 'Конвертация не удалась:',
        'cached': '📦 Из кэша',
    },
    'es': {
        'title': '🎮 Convertidor de Colecciones de Mods RimWorld',
        'subtitle': 'Convertir colecciones de Steam Workshop a formato RimPy XML',
        'toggle_theme': '🌓 Cambiar tema',
        'log_font_size': 'Tamaño de fuente del registro:',
        'clear_log': '🗑️ Limpiar registro',
        'collection_url': '📋 URL de colección:',
        'output_file': '💾 Archivo de salida:',
        'steamcmd_path': '⚙️ Ruta SteamCMD:',
        'browse': '📁 Examinar',
        'statistics': '📊 Estadísticas de conversión',
        'total_mods': 'Mods totales',
        'successful': '✅ Exitoso',
        'failed': '❌ Fallido',
        'current': '🔄 Actual',
        'start_conversion': '🚀 Iniciar conversión',
        'converting': '⏳ Convirtiendo...',
        'ready': 'Listo para convertir',
        'conversion_log': '📝 Registro de conversión',
        'language': '🌐 Idioma:',
        'gemini_api_key': '🔑 Clave API Gemini(WIP):',
        'translate_ui': 'Traducir UI',
        'translate_logs': 'Traducir registros',
        'error': 'Error',
        'success': 'Éxito',
        'enter_url': 'Por favor ingrese una URL de colección',
        'specify_output': 'Por favor especifique un archivo de salida',
        'conversion_complete': '🎉 ¡Conversión completada!',
        'total': 'Mods totales:',
        'file_saved': 'Archivo guardado en:',
        'conversion_failed': 'Conversión fallida:',
        'cached': '📦 En caché',
    }
}


class ConversionStats:
    """Track conversion statistics"""
    def __init__(self):
        self.total_mods = 0
        self.successful = 0
        self.failed = 0
        self.cached = 0
        self.current = 0
    
    def reset(self):
        self.total_mods = 0
        self.successful = 0
        self.failed = 0
        self.cached = 0
        self.current = 0


class GeminiTranslator:
    """Handle translations using Gemini API"""
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.model = None
        if api_key:
            self.configure(api_key)
    
    def configure(self, api_key):
        """Configure Gemini API"""
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"Failed to configure Gemini: {e}")
            return False
    
    def translate(self, text, target_language):
        """Translate text to target language"""
        if not self.model or not text.strip():
            return text
        
        try:
            prompt = f"Translate the following text to {target_language}. Only return the translation, nothing else:\n\n{text}"
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return text


class SteamCollectionToRimPy:
    def __init__(self, steamcmd_path="steamcmd"):
        self.steamcmd_path = steamcmd_path
        self.workshop_path = Path.home() / "Steam/steamapps/workshop/content/294100"
        self.temp_workshop_path = None
        self.stats = ConversionStats()
        self.cache_file = "mod_cache.json"
        self.mod_cache = self.load_cache()

    def load_cache(self):
        """Load cache from file. Create empty if not exists or corrupted"""
        if not os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                print(f"✅ Created new cache file: {self.cache_file}")
            except Exception as e:
                print(f"❌ Failed to create cache file: {e}")
                return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ Cache file corrupted: {e}. Recreating...")
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception as write_err:
                print(f"❌ Failed to recreate cache: {write_err}")
            return {}
        except Exception as e:
            print(f"❌ Failed to read cache: {e}")
            return {}

    def save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.mod_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def get_package_id_cached(self, mod_id):
        """Get packageId from cache"""
        return self.mod_cache.get(mod_id)

    def cache_package_id(self, mod_id, package_id):
        """Cache packageId"""
        self.mod_cache[mod_id] = package_id
        self.save_cache()

    def get_collection_mods(self, collection_url, log_callback=None):
        """Extract mod IDs from Steam Workshop collection URL"""
        def log(msg, tag="normal"):
            if log_callback:
                log_callback(msg, tag)
        
        log(f"🔍 Fetching collection from Steam...", "info")
        log(f"   URL: {collection_url}", "info")
        
        collection_match = re.search(r'id=(\d+)', collection_url)
        if not collection_match:
            raise ValueError("Invalid collection URL - no ID found")
        
        collection_id = collection_match.group(1)
        log(f"   Collection ID: {collection_id}", "info")
        
        api_url = f"https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/"
        
        try:
            log(f"   Trying Steam API...", "info")
            data = {
                'collectioncount': 1,
                'publishedfileids[0]': collection_id
            }
            
            response = requests.post(api_url, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            log(f"   API Response received", "info")
            
            if 'response' in result and 'collectiondetails' in result['response']:
                collection_details = result['response']['collectiondetails'][0]
                
                result_code = collection_details.get('result', 0)
                if result_code != 1:
                    log(f"   ⚠️ API returned error code: {result_code}", "warning")
                    raise Exception(f"API error code: {result_code}")
                
                if 'children' in collection_details:
                    all_children = collection_details['children']
                    log(f"   Found {len(all_children)} total items in collection", "info")
                    
                    mod_ids = []
                    for child in all_children:
                        filetype = child.get('filetype', 0)
                        child_id = str(child['publishedfileid'])
                        
                        if filetype == 0:
                            mod_ids.append(child_id)
                    
                    log(f"✅ Found {len(mod_ids)} mods via Steam API", "success")
                    return mod_ids
        
        except Exception as e:
            log(f"⚠️ Steam API failed: {str(e)}", "warning")
            log(f"   Falling back to web scraping...", "info")
        
        try:
            log(f"   Fetching webpage...", "info")
            response = requests.get(collection_url, timeout=15)
            response.raise_for_status()
            
            log(f"   Parsing HTML...", "info")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            mod_ids = []
            seen_ids = set([collection_id])
            
            collection_children = soup.find('div', id='sharedfiles_children')
            
            if collection_children:
                items = collection_children.find_all('div', class_='collectionItem')
                
                for item in items:
                    link = item.find('a', href=re.compile(r'steamcommunity\.com/sharedfiles/filedetails/\?id=\d+'))
                    if link:
                        mod_match = re.search(r'id=(\d+)', link['href'])
                        if mod_match:
                            mod_id = mod_match.group(1)
                            if mod_id not in seen_ids:
                                mod_ids.append(mod_id)
                                seen_ids.add(mod_id)
            else:
                collection_items_area = soup.find('div', class_='collectionChildren')
                if collection_items_area:
                    items = collection_items_area.find_all('div', class_='collectionItem')
                    
                    for item in items:
                        link = item.find('a', href=re.compile(r'sharedfiles/filedetails/\?id=\d+'))
                        if link:
                            mod_match = re.search(r'id=(\d+)', link['href'])
                            if mod_match:
                                mod_id = mod_match.group(1)
                                if mod_id not in seen_ids:
                                    mod_ids.append(mod_id)
                                    seen_ids.add(mod_id)
            
            log(f"✅ Found {len(mod_ids)} mods via web scraping", "success")
            
            if len(mod_ids) == 0:
                log(f"❌ ERROR: No mods found!", "error")
            
            return mod_ids
            
        except Exception as e:
            log(f"❌ Web scraping failed: {str(e)}", "error")
            raise

    def get_mod_info(self, mod_id):
        """Get mod information from Steam Workshop"""
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_elem = soup.find('div', class_='workshopItemTitle')
            mod_name = title_elem.text.strip() if title_elem else f"Unknown Mod {mod_id}"
            
            return {
                'id': mod_id,
                'name': mod_name,
                'packageId': f'steam.{mod_id}'.lower()
            }
        except Exception:
            return {
                'id': mod_id,
                'name': f"Mod {mod_id}",
                'packageId': f'steam.{mod_id}'.lower()
            }

    def download_mod_with_steamcmd(self, mod_id, workshop_dir, log_callback=None, stop_flag=None):
        """Download a mod using SteamCMD silently (no console window)"""
        cmd = [
            self.steamcmd_path,
            '+force_install_dir', str(workshop_dir),
            '+login', 'anonymous',
            '+workshop_download_item', '294100', mod_id,
            '+quit'
        ]
        
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        else:
            startupinfo = None

        try:
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
                if stop_flag and stop_flag():
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    if log_callback:
                        log_callback(f"   🛑 Download stopped for mod {mod_id}", "warning")
                    return False
                
                retcode = process.poll()
                if retcode is not None:
                    if retcode == 0:
                        if log_callback:
                            log_callback(f"   ✅ Download: SUCCESSFUL", "success")
                        return True
                    else:
                        if log_callback:
                            log_callback(f"   ❌ Download: FAILED (code {retcode})", "error")
                        return False
                
                time.sleep(0.1)
                
        except Exception as e:
            if log_callback:
                log_callback(f"   ❌ Download: FAILED ({str(e)})", "error")
            return False

    def extract_package_id(self, mod_id, workshop_dir):
        """Extract packageId from About.xml file"""
        mod_path = Path(workshop_dir) / "steamapps/workshop/content/294100" / mod_id
        about_xml = mod_path / "About/About.xml"
        
        if not about_xml.exists():
            return f"steam.{mod_id}".lower()
        
        try:
            tree = ET.parse(about_xml)
            root = tree.getroot()
            package_id_elem = root.find('packageId')
            
            if package_id_elem is not None and package_id_elem.text:
                return package_id_elem.text.strip().lower()
            
            return f"steam.{mod_id}".lower()
        except Exception:
            return f"steam.{mod_id}".lower()

    def create_rimpy_xml(self, mods, output_file):
        """Create RimPy-compatible XML file"""
        root = ET.Element('ModsConfigData')
        version = ET.SubElement(root, 'version')
        version.text = '1.5'
        
        active_mods = ET.SubElement(root, 'activeMods')
        core = ET.SubElement(active_mods, 'li')
        core.text = 'ludeon.rimworld'
        
        for mod in mods:
            li = ET.SubElement(active_mods, 'li')
            li.text = mod['packageId']
        
        known_expansions = ET.SubElement(root, 'knownExpansions')
        expansions = ['ludeon.rimworld.royalty', 'ludeon.rimworld.ideology', 
                     'ludeon.rimworld.biotech', 'ludeon.rimworld.anomaly']
        for exp in expansions:
            li = ET.SubElement(known_expansions, 'li')
            li.text = exp
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

    def convert_collection(self, collection_url, output_file, log_callback=None, progress_callback=None, stats_callback=None):
        """Main conversion method"""
        def log(msg, tag="normal"):
            if log_callback:
                log_callback(msg, tag)
        
        self.stats.reset()
        
        mod_ids = self.get_collection_mods(collection_url, log_callback)
        self.stats.total_mods = len(mod_ids)
        
        if stats_callback:
            stats_callback(self.stats)
        
        self.temp_workshop_path = tempfile.mkdtemp(prefix="rimworld_workshop_")
        log(f"\n📁 Using temporary directory...", "normal")
        
        try:
            mods = []
            for i, mod_id in enumerate(mod_ids, 1):
                self.stats.current = i
                
                if progress_callback:
                    progress_callback(i / self.stats.total_mods, f"Processing mod {i}/{self.stats.total_mods}")
                
                if stats_callback:
                    stats_callback(self.stats)
                
                log(f"\n{'─'*60}", "separator")
                log(f"[{i}/{self.stats.total_mods}] 🔄 Processing Mod ID: {mod_id}", "header")
                log(f"{'─'*60}", "separator")
                
                cached_package_id = self.get_package_id_cached(mod_id)
                if cached_package_id:
                    mod_info = self.get_mod_info(mod_id)
                    mod_info['packageId'] = cached_package_id
                    mods.append(mod_info)
                    log(f"   📦 Cached: {cached_package_id}", "success")
                    self.stats.cached += 1
                    self.stats.successful += 1
                    continue

                mod_info = self.get_mod_info(mod_id)
                log(f"   📝 Mod Name: {mod_info['name']}", "info")

                success = self.download_mod_with_steamcmd(mod_id, self.temp_workshop_path, log_callback)
                
                if success:
                    package_id = self.extract_package_id(mod_id, self.temp_workshop_path)
                    mod_info['packageId'] = package_id
                    self.cache_package_id(mod_id, package_id)
                    log(f"   🔖 Package ID: {package_id}", "package")
                    self.stats.successful += 1
                else:
                    package_id = f"steam.{mod_id}".lower()
                    mod_info['packageId'] = package_id
                    log(f"   🔖 Package ID: {package_id} (fallback)", "warning")
                    self.stats.failed += 1
                
                mods.append(mod_info)
            
            self.create_rimpy_xml(mods, output_file)
            log(f"\n{'='*60}", "separator")
            log(f"✅ SUCCESS! XML file created", "success")
            log(f"📊 Total mods processed: {len(mods)}", "info")
            log(f"✅ Downloaded: {self.stats.successful - self.stats.cached}", "success")
            log(f"📦 Cached: {self.stats.cached}", "success")
            log(f"❌ Failed: {self.stats.failed}", "error")
            log(f"📄 File saved: {output_file}", "info")
            log(f"{'='*60}", "separator")
            
            return mods
            
        finally:
            if self.temp_workshop_path and os.path.exists(self.temp_workshop_path):
                log(f"\n🧹 Cleaning up temporary files...", "normal")
                shutil.rmtree(self.temp_workshop_path)


class ModernConverterGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("RimWorld Mod Collection Converter")
        self.root.geometry("1200x800")

        self.offset_x = 0
        self.offset_y = 0
        self.settings = self.load_settings()
        self.log_font_size = self.settings.get('log_font_size', 11)
        self.current_language = self.settings.get('language', 'en')
        self.translate_logs_enabled = self.settings.get('translate_logs', False)
        self.stats = ConversionStats()
        
        gemini_key = self.settings.get('gemini_api_key', '')
        self.translator = GeminiTranslator(gemini_key if gemini_key else None)

        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.setup_ui()
        self.apply_saved_settings()
        self.update_ui_language()

    def t(self, key):
        """Get translation for key"""
        return TRANSLATIONS.get(self.current_language, TRANSLATIONS['en']).get(key, key)
        
    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def on_move(self, event):
        x = self.root.winfo_x() + event.x - self.offset_x
        y = self.root.winfo_y() + event.y - self.offset_y
        self.root.geometry(f"+{x}+{y}")
        
    def load_settings(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}
    
    def save_settings(self):
        settings = {
            'url': self.url_entry.get(),
            'output': self.output_entry.get(),
            'steamcmd': self.steamcmd_entry.get(),
            'log_font_size': self.log_font_size,
            'theme': ctk.get_appearance_mode(),
            'language': self.current_language,
            'gemini_api_key': self.gemini_entry.get(),
            'translate_logs': self.translate_logs_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def apply_saved_settings(self):
        if 'url' in self.settings and self.settings['url']:
            self.url_entry.insert(0, self.settings['url'])
        if 'output' in self.settings and self.settings['output']:
            self.output_entry.delete(0, 'end')
            self.output_entry.insert(0, self.settings['output'])
        if 'steamcmd' in self.settings and self.settings['steamcmd']:
            self.steamcmd_entry.delete(0, 'end')
            self.steamcmd_entry.insert(0, self.settings['steamcmd'])
        if 'theme' in self.settings:
            ctk.set_appearance_mode(self.settings['theme'])
        if 'gemini_api_key' in self.settings and self.settings['gemini_api_key']:
            self.gemini_entry.insert(0, self.settings['gemini_api_key'])
        
    def setup_ui(self):
        left_panel = ctk.CTkFrame(self.root, corner_radius=0)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(7, weight=1)
        
        header_frame = ctk.CTkFrame(left_panel, fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        header_frame.bind('<Button-1>', self.start_move)
        header_frame.bind('<B1-Motion>', self.on_move)
        
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=self.t('title'),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(20, 5))
        self.title_label.bind('<Button-1>', self.start_move)
        self.title_label.bind('<B1-Motion>', self.on_move)
        
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=self.t('subtitle'),
            font=ctk.CTkFont(size=13),
            text_color=("gray70", "gray50")
        )
        self.subtitle_label.pack(pady=(0, 20))
        self.subtitle_label.bind('<Button-1>', self.start_move)
        self.subtitle_label.bind('<B1-Motion>', self.on_move)
        
        controls_frame = ctk.CTkFrame(left_panel, corner_radius=10)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.theme_btn = ctk.CTkButton(
            controls_frame,
            text=self.t('toggle_theme'),
            command=self.toggle_theme,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.theme_btn.pack(side="left", padx=5, pady=10)
        
        self.font_label = ctk.CTkLabel(controls_frame, text=self.t('log_font_size'), font=ctk.CTkFont(size=11))
        self.font_label.pack(side="left", padx=(15, 5), pady=10)
        
        font_minus = ctk.CTkButton(
            controls_frame,
            text="−",
            command=lambda: self.change_font_size(-1),
            width=30,
            height=30,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        font_minus.pack(side="left", padx=2, pady=10)
        
        self.font_size_label = ctk.CTkLabel(
            controls_frame,
            text=str(self.log_font_size),
            font=ctk.CTkFont(size=11, weight="bold"),
            width=30
        )
        self.font_size_label.pack(side="left", padx=5, pady=10)
        
        font_plus = ctk.CTkButton(
            controls_frame,
            text="+",
            command=lambda: self.change_font_size(1),
            width=30,
            height=30,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        font_plus.pack(side="left", padx=2, pady=10)
        
        self.clear_log_btn = ctk.CTkButton(
            controls_frame,
            text=self.t('clear_log'),
            command=self.clear_log,
            width=100,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.clear_log_btn.pack(side="left", padx=(15, 5), pady=10)
        
        lang_frame = ctk.CTkFrame(left_panel, corner_radius=10)
        lang_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        lang_frame.grid_columnconfigure(1, weight=1)
        
        lang_label = ctk.CTkLabel(lang_frame, text=self.t('language'), font=ctk.CTkFont(size=12, weight="bold"))
        lang_label.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        self.language_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["English", "Русский", "Español"],
            command=self.change_language,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.language_menu.grid(row=0, column=1, sticky="w", padx=(10, 20), pady=(15, 10))
        self.language_menu.set({"en": "English", "ru": "Русский", "es": "Españол"}[self.current_language])
        
        gemini_label = ctk.CTkLabel(lang_frame, text=self.t('gemini_api_key'), font=ctk.CTkFont(size=12, weight="bold"))
        gemini_label.grid(row=1, column=0, sticky="w", padx=20, pady=(10, 15))
        
        self.gemini_entry = ctk.CTkEntry(
            lang_frame,
            placeholder_text="Enter Gemini API key for translation...",
            height=35,
            font=ctk.CTkFont(size=11)
        )
        self.gemini_entry.grid(row=1, column=1, sticky="ew", padx=(10, 10), pady=(10, 10))
        
        self.translate_logs_var = ctk.BooleanVar(value=self.translate_logs_enabled)
        self.translate_logs_check = ctk.CTkCheckBox(
            lang_frame,
            text=self.t('translate_logs'),
            variable=self.translate_logs_var,
            font=ctk.CTkFont(size=11)
        )
        self.translate_logs_check.grid(row=1, column=2, sticky="w", padx=(10, 20), pady=(10, 10))
        
        input_frame = ctk.CTkFrame(left_panel, corner_radius=10)
        input_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        input_frame.grid_columnconfigure(1, weight=1)
        
        self.url_label = ctk.CTkLabel(input_frame, text=self.t('collection_url'), font=ctk.CTkFont(size=14, weight="bold"))
        self.url_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        self.url_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="https://steamcommunity.com/sharedfiles/filedetails/?id=...",
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        self.url_entry.bind('<Control-v>', lambda e: self.paste_to_entry(self.url_entry))
        self.url_entry.bind('<Control-V>', lambda e: self.paste_to_entry(self.url_entry))
        
        self.output_label = ctk.CTkLabel(input_frame, text=self.t('output_file'), font=ctk.CTkFont(size=14, weight="bold"))
        self.output_label.grid(row=2, column=0, sticky="w", padx=20, pady=(10, 10))
        
        output_container = ctk.CTkFrame(input_frame, fg_color="transparent")
        output_container.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        output_container.grid_columnconfigure(0, weight=1)
        
        self.output_entry = ctk.CTkEntry(output_container, placeholder_text="ModList.xml", height=40, font=ctk.CTkFont(size=12))
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.output_entry.insert(0, "ModList.xml")
        self.output_entry.bind('<Control-v>', lambda e: self.paste_to_entry(self.output_entry))
        self.output_entry.bind('<Control-V>', lambda e: self.paste_to_entry(self.output_entry))
        
        self.browse_btn = ctk.CTkButton(
            output_container,
            text=self.t('browse'),
            command=self.browse_output_file,
            width=120,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.browse_btn.grid(row=0, column=1)
        
        self.steamcmd_label = ctk.CTkLabel(input_frame, text=self.t('steamcmd_path'), font=ctk.CTkFont(size=14, weight="bold"))
        self.steamcmd_label.grid(row=4, column=0, sticky="w", padx=20, pady=(10, 10))
        
        steamcmd_container = ctk.CTkFrame(input_frame, fg_color="transparent")
        steamcmd_container.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        steamcmd_container.grid_columnconfigure(0, weight=1)
        
        self.steamcmd_entry = ctk.CTkEntry(steamcmd_container, placeholder_text="steamcmd", height=40, font=ctk.CTkFont(size=12))
        self.steamcmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.steamcmd_entry.insert(0, "steamcmd")
        self.steamcmd_entry.bind('<Control-v>', lambda e: self.paste_to_entry(self.steamcmd_entry))
        self.steamcmd_entry.bind('<Control-V>', lambda e: self.paste_to_entry(self.steamcmd_entry))
        
        self.steamcmd_browse_btn = ctk.CTkButton(
            steamcmd_container,
            text=self.t('browse'),
            command=self.browse_steamcmd,
            width=120,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.steamcmd_browse_btn.grid(row=0, column=1)
        
        stats_frame = ctk.CTkFrame(left_panel, corner_radius=10)
        stats_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        self.stats_title = ctk.CTkLabel(stats_frame, text=self.t('statistics'), font=ctk.CTkFont(size=14, weight="bold"))
        self.stats_title.pack(pady=(15, 10))
        
        stats_container = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_container.pack(fill="x", padx=20, pady=(0, 15))
        
        total_frame = ctk.CTkFrame(stats_container, corner_radius=8)
        total_frame.pack(side="left", expand=True, fill="x", padx=5)
        
        self.total_mods_label = ctk.CTkLabel(total_frame, text=self.t('total_mods'), font=ctk.CTkFont(size=11))
        self.total_mods_label.pack(pady=(10, 2))
        self.total_label = ctk.CTkLabel(
            total_frame,
            text="0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#3498db", "#5dade2")
        )
        self.total_label.pack(pady=(0, 10))
        
        success_frame = ctk.CTkFrame(stats_container, corner_radius=8)
        success_frame.pack(side="left", expand=True, fill="x", padx=5)
        
        self.successful_label_text = ctk.CTkLabel(success_frame, text=self.t('successful'), font=ctk.CTkFont(size=11))
        self.successful_label_text.pack(pady=(10, 2))
        self.success_label = ctk.CTkLabel(
            success_frame,
            text="0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#52be80", "#7dcea0")
        )
        self.success_label.pack(pady=(0, 10))
        
        failed_frame = ctk.CTkFrame(stats_container, corner_radius=8)
        failed_frame.pack(side="left", expand=True, fill="x", padx=5)
        
        self.failed_label_text = ctk.CTkLabel(failed_frame, text=self.t('failed'), font=ctk.CTkFont(size=11))
        self.failed_label_text.pack(pady=(10, 2))
        self.failed_label = ctk.CTkLabel(
            failed_frame,
            text="0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#e74c3c", "#ec7063")
        )
        self.failed_label.pack(pady=(0, 10))
        
        current_frame = ctk.CTkFrame(stats_container, corner_radius=8)
        current_frame.pack(side="left", expand=True, fill="x", padx=5)
        
        self.current_label_text = ctk.CTkLabel(current_frame, text=self.t('current'), font=ctk.CTkFont(size=11))
        self.current_label_text.pack(pady=(10, 2))
        self.current_label = ctk.CTkLabel(
            current_frame,
            text="0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#f39c12", "#f8c471")
        )
        self.current_label.pack(pady=(0, 10))
        
        self.convert_btn = ctk.CTkButton(
            left_panel,
            text=self.t('start_conversion'),
            command=self.start_conversion,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("#1f538d", "#14375e"),
            hover_color=("#1a4570", "#0f2944")
        )
        self.convert_btn.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        progress_frame = ctk.CTkFrame(left_panel, corner_radius=10)
        progress_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.progress_label = ctk.CTkLabel(progress_frame, text=self.t('ready'), font=ctk.CTkFont(size=13))
        self.progress_label.pack(pady=(15, 5))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=20)
        self.progress_bar.pack(fill="x", padx=20, pady=(5, 10))
        self.progress_bar.set(0)
        
        self.progress_percent = ctk.CTkLabel(progress_frame, text="0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.progress_percent.pack(pady=(0, 15))
        
        log_panel = ctk.CTkFrame(self.root, corner_radius=10)
        log_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)
        
        self.log_header = ctk.CTkLabel(log_panel, text=self.t('conversion_log'), font=ctk.CTkFont(size=14, weight="bold"))
        self.log_header.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))                                                                                     
        self.log_text = ctk.CTkTextbox(
            log_panel,
            font=ctk.CTkFont(family="Consolas", size=self.log_font_size),
            wrap="word"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        self.log_text._textbox.tag_config("header", foreground="#5DADE2")
        self.log_text._textbox.tag_config("success", foreground="#52BE80")
        self.log_text._textbox.tag_config("error", foreground="#E74C3C")
        self.log_text._textbox.tag_config("warning", foreground="#F39C12")
        self.log_text._textbox.tag_config("info", foreground="#85C1E9")
        self.log_text._textbox.tag_config("package", foreground="#BB8FCE")
        self.log_text._textbox.tag_config("separator", foreground="#566573")
    def change_language(self, choice):
        """Change UI language"""
        lang_map = {"English": "en", "Русский": "ru", "Español": "es"}
        self.current_language = lang_map.get(choice, "en")
        self.save_settings()
        self.update_ui_language()

    def update_ui_language(self):
        """Update all UI text to current language"""
        self.title_label.configure(text=self.t('title'))
        self.subtitle_label.configure(text=self.t('subtitle'))
        self.theme_btn.configure(text=self.t('toggle_theme'))
        self.font_label.configure(text=self.t('log_font_size'))
        self.clear_log_btn.configure(text=self.t('clear_log'))
        self.url_label.configure(text=self.t('collection_url'))
        self.output_label.configure(text=self.t('output_file'))
        self.steamcmd_label.configure(text=self.t('steamcmd_path'))
        self.browse_btn.configure(text=self.t('browse'))
        self.steamcmd_browse_btn.configure(text=self.t('browse'))
        self.stats_title.configure(text=self.t('statistics'))
        self.total_mods_label.configure(text=self.t('total_mods'))
        self.successful_label_text.configure(text=self.t('successful'))
        self.failed_label_text.configure(text=self.t('failed'))
        self.current_label_text.configure(text=self.t('current'))
        self.convert_btn.configure(text=self.t('start_conversion'))
        self.progress_label.configure(text=self.t('ready'))
        self.log_header.configure(text=self.t('conversion_log'))
        self.translate_logs_check.configure(text=self.t('translate_logs'))

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_theme = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new_theme)
        self.save_settings()

    def change_font_size(self, delta):
        self.log_font_size = max(8, min(20, self.log_font_size + delta))
        self.font_size_label.configure(text=str(self.log_font_size))
        self.log_text.configure(font=ctk.CTkFont(family="Consolas", size=self.log_font_size))
        self.save_settings()

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="Save XML File",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filename:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, filename)
            self.save_settings()

    def browse_steamcmd(self):
        filename = filedialog.askopenfilename(
            title="Select SteamCMD executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.steamcmd_entry.delete(0, "end")
            self.steamcmd_entry.insert(0, filename)
            self.save_settings()

    def paste_to_entry(self, entry):
        try:
            clipboard_content = self.root.clipboard_get()
            try:
                entry.delete("sel.first", "sel.last")
            except:
                pass
            entry.insert("insert", clipboard_content)
            return "break"
        except:
            pass
        return "break"

    def log_message(self, message, tag="normal"):
        if self.translate_logs_var.get() and self.current_language != 'en':
            api_key = self.gemini_entry.get().strip()
            if api_key and self.translator.api_key != api_key:
                self.translator.configure(api_key)
                self.save_settings()
            
            if self.translator.model:
                lang_names = {'ru': 'Russian', 'es': 'Spanish'}
                target_lang = lang_names.get(self.current_language, 'English')
                message = self.translator.translate(message, target_lang)
        
        current_pos = self.log_text.index("end-1c")
        self.log_text.insert("end", message + "\n")
        
        if tag != "normal":
            line_start = current_pos
            line_end = self.log_text.index("end-1c")
            self.log_text._textbox.tag_add(tag, line_start, line_end)
        
        self.log_text.see("end")

    def update_progress(self, value, text):
        self.progress_bar.set(value)
        self.progress_label.configure(text=text)
        self.progress_percent.configure(text=f"{int(value * 100)}%")

    def update_stats(self, stats):
        self.total_label.configure(text=str(stats.total_mods))
        self.success_label.configure(text=str(stats.successful))
        self.failed_label.configure(text=str(stats.failed))
        self.current_label.configure(text=str(stats.current))

    def start_conversion(self):
        url = self.url_entry.get().strip()
        output_file = self.output_entry.get().strip()
        steamcmd_path = self.steamcmd_entry.get().strip()
        
        if not url:
            messagebox.showerror(self.t('error'), self.t('enter_url'))
            return
        
        if not output_file:
            messagebox.showerror(self.t('error'), self.t('specify_output'))
            return
        
        output_path = Path(output_file)
        if not output_path.parent.exists():
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror(self.t('error'), f"Cannot create directory: {e}")
                return
        
        self.save_settings()
        self.log_text.delete("1.0", "end")
        self.progress_bar.set(0)
        self.update_progress(0, self.t('converting'))
        
        self.stats.reset()
        self.update_stats(self.stats)
        
        self.convert_btn.configure(state="disabled", text=self.t('converting'))
        
        def run_conversion():
            try:
                converter = SteamCollectionToRimPy(steamcmd_path=steamcmd_path)
                mods = converter.convert_collection(
                    url, 
                    output_file, 
                    self.log_message,
                    lambda v, t: self.root.after(0, lambda: self.update_progress(v, t)),
                    lambda s: self.root.after(0, lambda: self.update_stats(s))
                )
                
                self.root.after(0, lambda: self.conversion_complete(True, converter.stats, output_file))
            except Exception as e:
                error_message = str(e)
                self.root.after(0, lambda err=error_message: self.conversion_complete(False, self.stats, err))
        
        thread = threading.Thread(target=run_conversion, daemon=True)
        thread.start()


    def conversion_complete(self, success, stats, message):
        self.convert_btn.configure(state="normal", text=self.t('start_conversion'))
        
        if success:
            self.update_progress(1.0, f"✅ {stats.total_mods}")
            messagebox.showinfo(
                self.t('success'),
                f"{self.t('conversion_complete')}\n\n"
                f"{self.t('total')} {stats.total_mods}\n"
                f"✅ {self.t('successful')} {stats.successful - stats.cached}\n"
                f"📦 {self.t('cached')} {stats.cached}\n"
                f"❌ {self.t('failed')} {stats.failed}\n\n"
                f"{self.t('file_saved')}\n{message}"
            )
        else:
            self.update_progress(0, "❌")
            messagebox.showerror(self.t('error'), f"{self.t('conversion_failed')}\n{message}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ModernConverterGUI()
    app.run()
