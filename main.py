import subprocess
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime
import win32con, win32gui
import win32com.client
import time
import psutil
import pyautogui
import configparser
import os, sys
import shutil
import winreg

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for Nuitka """
    try:
        if getattr(sys, 'frozen', False):
            # Nuitka sets the `sys.frozen` attribute when the application is frozen
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

_config_path = None
_config_cache = None
_debug_mode = None

def get_config_path():
    """ Get config.ini path in Documents/ValoSwitcher, creating default if needed """
    global _config_path
    if _config_path:
        return _config_path

    documents = os.path.join(os.path.expandvars('%USERPROFILE%'), 'Documents', 'ValoSwitcher')
    os.makedirs(documents, exist_ok=True)
    _config_path = os.path.join(documents, 'config.ini')

    # Create default config if it doesn't exist
    if not os.path.exists(_config_path):
        create_default_config(_config_path)

    return _config_path

def load_config():
    """Load config from disk and cache it."""
    global _config_cache, _debug_mode
    _config_cache = configparser.RawConfigParser()
    _config_cache.read(get_config_path())
    _debug_mode = _config_cache.get('SETTINGS', 'DEBUG', fallback='false').lower() == 'true'
    return _config_cache

def get_config():
    """Get cached config, loading from disk if needed."""
    if _config_cache is None:
        return load_config()
    return _config_cache

def save_config(config=None):
    """Write config to disk and update cache."""
    global _config_cache
    if config:
        _config_cache = config
    if _config_cache:
        with open(get_config_path(), 'w') as f:
            _config_cache.write(f)

def get_setting(key, fallback='false'):
    """Read a setting from cached config."""
    return get_config().get('SETTINGS', key, fallback=fallback).lower() == 'true'

def debug_log(msg):
    """Print only if debug is enabled."""
    if _debug_mode:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')

def create_default_config(config_path):
    """ Create a default config.ini file """
    default_config = configparser.RawConfigParser()
    default_config['SETTINGS'] = {
        'RIOTCLIENT_PATH': r'C:\Riot Games\Riot Client\RiotClientServices.exe',
        'DECEIVE_PATH': r'%USERPROFILE%\Downloads\Deceive.exe',
        'DECEIVE_ENABLED': 'false',
        'DEBUG': 'false',
        'NOTIFICATIONS': 'true'
    }

    with open(config_path, 'w') as config_file:
        default_config.write(config_file)

    print(f'Created default config at: {config_path}')

class RiotAutoLogin:
    template_path = resource_path("assets/input.png")
    def __init__(self, user, pwd):
        self.username = user
        self.password = pwd
        self.config = self._load_config()
        self.RIOTCLIENT_PATH = self.config['SETTINGS']['RIOTCLIENT_PATH']
    
    def _load_config(self):
        return get_config()
    
    def _wait_for_window(self, window_title):
        while True:
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] {window_title} found')
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return hwnd
            time.sleep(1)

    def _check_for_input(self):
        location = pyautogui.locateOnScreen(self.template_path, confidence=0.8)
        if location is not None: return True
        return False

    def _send_login_keys(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Launching Riot Client')
        try:
            process = subprocess.Popen(self.RIOTCLIENT_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True)  # Ensures the output is returned as a string)
            stdout, stderr = process.communicate()
            if stdout:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Riot Client started')
            if stderr:
                print("Error:\n", stderr)
        except FileNotFoundError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED (FileNotFoundError): This is due to an incorrect Riot Client path in your config. Check it and try again.")
            return False

        self._wait_for_window("Riot Client")
        shell = win32com.client.Dispatch("WScript.Shell")

        while True:
            if self._check_for_input():
                shell.SendKeys(self.username)
                shell.SendKeys("{TAB}")
                shell.SendKeys(self.password)
                shell.SendKeys("{ENTER}")
                break
        print(f'[{datetime.now().strftime("%H:%M:%S")}] SUCCESS: Logged in')
        return True

def is_process_running(process_name):
    """Check if there's any running process that matches the given name."""
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
            if process_name.lower() in pinfo['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    return False

class RiotSessionManager:
    """Manages Riot Client session backup and restore for account switching"""

    def __init__(self):
        # Use Documents/ValoSwitcher/sessions folder
        documents = os.path.join(os.path.expandvars('%USERPROFILE%'), 'Documents', 'ValoSwitcher')
        self.sessions_base_dir = os.path.join(documents, 'sessions')
        self.local_app_data = os.environ.get('LOCALAPPDATA', '')

        # Files to backup/restore (only session-specific files)
        self.session_files = [
            {
                'name': 'RiotGamesPrivateSettings.yaml',
                'source': os.path.join(self.local_app_data, 'Riot Games', 'Riot Client', 'Data', 'RiotGamesPrivateSettings.yaml'),
                'is_dir': False
            },
            {
                'name': 'Sessions',
                'source': os.path.join(self.local_app_data, 'Riot Games', 'Riot Client', 'Data', 'Sessions'),
                'is_dir': True
            }
        ]

        # Create sessions directory if it doesn't exist
        os.makedirs(self.sessions_base_dir, exist_ok=True)

    def kill_riot_processes(self):
        """Kill all Riot Client processes in parallel before session swap"""
        debug_log('Killing Riot Client processes...')
        processes = [
            'RiotClientUx.exe',
            'RiotClientServices.exe',
            'RiotClientCrashHandler.exe',
            'LeagueClient.exe',
            'Valorant.exe',
            'VALORANT-Win64-Shipping.exe',
            'vgc.exe',
        ]
        try:
            # Kill all processes in parallel
            kill_tasks = []
            for proc in processes:
                task = subprocess.Popen(['taskkill', '/F', '/IM', proc, '/T'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                kill_tasks.append(task)

            # Wait for all kill commands to finish
            for task in kill_tasks:
                task.wait()

            # Smart wait - check if processes are actually dead instead of blind sleep
            for _ in range(10):  # Max 2 seconds (10 x 0.2s)
                if not any(is_process_running(p) for p in ['RiotClientServices', 'RiotClientUx']):
                    break
                time.sleep(0.2)

            debug_log('Riot processes terminated')
        except Exception as e:
            debug_log(f'Error killing processes: {e}')

    def save_session(self, account_name):
        """Backup current Riot session to account-specific folder"""
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Saving session for {account_name}...')

        # Create account session directory
        account_session_dir = os.path.join(self.sessions_base_dir, account_name.replace(':', '_'))
        os.makedirs(account_session_dir, exist_ok=True)

        success = True
        for file_info in self.session_files:
            source_path = file_info['source']
            dest_path = os.path.join(account_session_dir, file_info['name'])

            try:
                if file_info['is_dir']:
                    # Backup directory
                    if os.path.exists(source_path):
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(source_path, dest_path)
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backed up {file_info["name"]} directory')
                    else:
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Source directory not found: {file_info["name"]}')
                else:
                    # Backup file
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backed up {file_info["name"]}')
                    else:
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Source file not found: {file_info["name"]}')
            except Exception as e:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Error backing up {file_info["name"]}: {e}')
                success = False

        if success:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Session saved successfully for {account_name}')
        return success

    def restore_session(self, account_name):
        """Restore session from account-specific folder to Riot Client"""
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Restoring session for {account_name}...')

        # Kill Riot processes first
        self.kill_riot_processes()

        account_session_dir = os.path.join(self.sessions_base_dir, account_name.replace(':', '_'))

        if not os.path.exists(account_session_dir):
            print(f'[{datetime.now().strftime("%H:%M:%S")}] No saved session found for {account_name}')
            return False

        success = True
        for file_info in self.session_files:
            source_path = os.path.join(account_session_dir, file_info['name'])
            dest_path = file_info['source']

            try:
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if file_info['is_dir']:
                    # Restore directory
                    if os.path.exists(source_path):
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(source_path, dest_path)
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Restored {file_info["name"]} directory')
                    else:
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backup directory not found: {file_info["name"]}')
                        # Remove existing if backup doesn't exist
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                else:
                    # Restore file
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Restored {file_info["name"]}')
                    else:
                        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backup file not found: {file_info["name"]}')
                        # Remove existing if backup doesn't exist
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
            except Exception as e:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Error restoring {file_info["name"]}: {e}')
                success = False

        if success:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Session restored successfully for {account_name}')
        return success

    def has_session(self, account_name):
        """Check if a saved session exists for the account"""
        account_session_dir = os.path.join(self.sessions_base_dir, account_name.replace(':', '_'))
        if not os.path.exists(account_session_dir):
            return False

        # Check if essential files exist
        private_settings = os.path.join(account_session_dir, 'RiotGamesPrivateSettings.yaml')
        sessions_dir = os.path.join(account_session_dir, 'Sessions')

        return os.path.exists(private_settings) or os.path.exists(sessions_dir)

    def delete_session(self, account_name):
        """Delete saved session for an account"""
        account_session_dir = os.path.join(self.sessions_base_dir, account_name.replace(':', '_'))
        if os.path.exists(account_session_dir):
            try:
                shutil.rmtree(account_session_dir)
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Deleted session for {account_name}')
                return True
            except Exception as e:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Error deleting session: {e}')
                return False
        return False

## UI ##
import cloudscraper
import requests, urllib
import concurrent.futures
from datetime import datetime
from io import BytesIO
from dataclasses import dataclass
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEventLoop, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QPalette, QColor, QPixmap, QBrush, QPainter, QAction, QKeySequence, QCursor
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy, QDialog, QLineEdit, QPushButton, QWidget, QSystemTrayIcon, QMenu
from qfluentwidgets import (setTheme, Theme, CardWidget, BodyLabel, SplashScreen, LineEdit, PushButton, ToolButton, FluentIcon, StrongBodyLabel, BodyLabel, PopupTeachingTip, TeachingTipTailPosition, FlyoutViewBase, ImageLabel, CheckBox)
from qframelesswindow import FramelessWindow

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.collections
import numpy as np
from scipy.interpolate import CubicSpline
from matplotlib.colors import LinearSegmentedColormap, Normalize
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

def create_level_tag(image_url, level):
    tmp_image = BytesIO(requests.get(image_url).content)
    tmp_image.seek(0)
    img = PIL.Image.open(tmp_image)
    draw = PIL.ImageDraw.Draw(img)
    font = PIL.ImageFont.load_default()

    # Get text size
    left, top, right, bottom = font.getbbox(level)
    text_width = right - left
    text_height = bottom - top
    
    image_width, image_height = img.size
    position = ((image_width - text_width) // 2, (image_height - text_height) // 2)
    
    # Draw text
    draw.text(position, level, (255, 255, 255), font=font)
    
    # Image to BytesIO
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    
    # BytesIO to QPixmap
    qpixmap = QPixmap()
    qpixmap.loadFromData(output.getvalue())
    return qpixmap

@dataclass
class AccountStats:
    banner : str = "https://titles.trackercdn.com/valorant-api/playercards/d1c85a2e-450d-f7e0-6ee3-469295cf1951/displayicon.png"
    account_level: int = 0
    account_level_tag_image:str = "https://media.valorant-api.com/levelborders/ebc736cd-4b6a-137b-e2b0-1486e31312c9/levelnumberappearance.png"
    shard: str = "eu"
    current_rank: str = "Unranked"
    current_rank_image: str = "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/0.png"
    peak_rank: str = "Unranked"
    peak_rank_image: str = "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/0.png"
    current_season_time_played : str = "0"
    kda_ratios: list = None

class MatchesGraph(QWidget):
    def __init__(self, data):
        super().__init__()
        self.kd_ratios = data
        self.setGeometry(30, 30, 30, 30)

        layout = QVBoxLayout(self)

        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.figure.patch.set_alpha(0)

        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background:transparent;")
        layout.addWidget(self.canvas)

        self.plot_chart()

    def plot_chart(self):
        # Original data points
        y = np.array(self.kd_ratios)
        x = np.array(range(len(self.kd_ratios)))

        # Cubic Spline Interpolation
        cs = CubicSpline(x, y)

        # Generate smooth points
        x_smooth = np.linspace(x.min(), x.max(), 2000)
        y_smooth = cs(x_smooth)

        ax = self.figure.add_subplot(111)
        ax.patch.set_alpha(0)

        # Create custom colormap for gradient
        colors = ["#0d0b37", "#0d0b37"] # "#05a2b2", #862F3B
        n_bins = 256
        cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)

        # Plot the line with gradient color
        points = np.array([x_smooth, y_smooth]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        norm = Normalize(0.25, 1.75)
        
        lc = matplotlib.collections.LineCollection(segments, cmap=cmap, norm=norm)
        lc.set_array(y_smooth)
        lc.set_linewidth(1)
        line = ax.add_collection(lc)

        ax.fill_between(x_smooth, y_smooth, color="#0d0b37", alpha=0.3)
        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(min(y.min() * 0.9, 0), max(y.max() * 1.1, 1.1))

        # Remove x and y axis labels
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)

        # Remove the frame
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        ax.grid(False)

        # Improve layout
        self.figure.tight_layout()
        self.canvas.draw()

class Image(QLabel):
    def __init__(self, image_url, parent=None):
        super().__init__(parent)
        self.setPixmap(self.load_pixmap_from_url(image_url))

    def load_pixmap_from_url(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image
        else:
            return QPixmap()

    def scaledToHeight(self, height):
        self.setPixmap(self.pixmap().scaledToHeight(height, Qt.TransformationMode.SmoothTransformation))

    def setBorderRadius(self, radius):
        pass


class CredentialLoader(QThread):
    credentials_loaded = pyqtSignal(list)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        config = configparser.RawConfigParser()
        config.read(self.file_path)
        credentials = []

        # Get last used account
        last_used = config.get('SETTINGS', 'LAST_USED', fallback=None)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_credential = {
                executor.submit(self.fetch_account, section, config[section]): (section, config[section])
                for section in config.sections() if 'riot_username' in config[section]
            }
            for future in concurrent.futures.as_completed(future_to_credential):
                section, data = future_to_credential[future]
                riot_username = data['riot_username']
                pwd = data['password']
                in_game_name, in_game_tag = data['name'].split(":")
                nickname = data.get('nickname', '')
                is_last_used = (section == last_used)
                try:
                    rank_data = future.result()
                except Exception as e:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] Failed to retrieve rank data for {section}: {e}')
                    rank_data = None
                credentials.append((riot_username, pwd, (in_game_name, in_game_tag), section, rank_data, nickname, is_last_used))

        self.credentials_loaded.emit(credentials)

    def fetch_account(self, section, data):
        in_game_name, in_game_tag = data['name'].split(":")

        # Try tracker.gg first, fall back to Henrik API
        try:
            return self.fetch_account_tracker(in_game_name, in_game_tag)
        except Exception as e:
            debug_log(f"Tracker.gg failed for {in_game_name}#{in_game_tag}: {e}, trying Henrik API...")
            try:
                return self.fetch_account_henrik(in_game_name, in_game_tag)
            except Exception as e2:
                debug_log(f"Henrik API also failed for {in_game_name}#{in_game_tag}: {e2}")
                raise

    def fetch_account_tracker(self, in_game_name, in_game_tag):
        """Fetch account data from tracker.gg"""
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': f'https://tracker.gg/valorant/profile/riot/{urllib.parse.quote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}/overview',
                'Origin': 'https://tracker.gg',
            }
        endpoint = scraper.get(
            f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}?source=web",
            headers=headers
        )
        endpoint.raise_for_status()
        data = endpoint.json()
        segments = data['data']['segments']
        if segments[0]['attributes']["playlist"] != "competitive":
            segment = next(filter(lambda s: s.get('attributes', {}).get('playlist') == "competitive", segments), False)
            if not segment:
                debug_log("No competitive data found, fetching in different endpoint")
                params = {
                    'playlist': 'competitive',
                    'source': 'web',
                }
                comp_segments = requests.get(
                    f'https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}/segments/playlist',
                    params=params,
                    headers=headers,
                )
                debug_log(f"Comp segments status: {comp_segments.status_code}")
                segment = comp_segments.json()['data'][0]
        else:
            segment = segments[0]

        kda_ratios = self.fetch_rank_matches_kda_ratios(in_game_name, in_game_tag)

        return AccountStats(
            banner=data['data']['platformInfo']['avatarUrl'],
            account_level=data['data']['metadata']['accountLevel'],
            account_level_tag_image=self.get_level_number_appearance(data['data']['metadata']['accountLevel']),
            shard=data['data']['metadata']['activeShard'],
            current_season_time_played=segments[0]['stats']['timePlayed']['displayValue'],
            current_rank=segment['stats']['rank']['metadata']['tierName'],
            current_rank_image=segment['stats']['rank']['metadata']['iconUrl'],
            peak_rank=segment['stats']['peakRank']['metadata']['tierName'],
            peak_rank_image=segment['stats']['peakRank']['metadata']['iconUrl'],
            kda_ratios=kda_ratios
        )

    def fetch_account_henrik(self, in_game_name, in_game_tag):
        """Fetch account data from Henrik's Valorant API (fallback)"""
        base_url = "https://api.henrikdev.xyz/valorant"

        # Fetch account info (card, level, region)
        account_resp = requests.get(f"{base_url}/v2/account/{urllib.parse.quote(in_game_name)}/{urllib.parse.quote(in_game_tag)}")
        account_resp.raise_for_status()
        account_data = account_resp.json()['data']

        region = account_data.get('region', 'eu')
        account_level = account_data.get('account_level', 0)
        card = account_data.get('card', {})
        banner = card.get('wide', card.get('large', card.get('small', '')))

        # Fetch MMR/rank data
        current_rank = "Unranked"
        current_rank_image = "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/0.png"
        peak_rank = "Unranked"
        peak_rank_image = current_rank_image
        time_played = "0"

        try:
            mmr_resp = requests.get(f"{base_url}/v2/mmr/{region}/{urllib.parse.quote(in_game_name)}/{urllib.parse.quote(in_game_tag)}")
            mmr_resp.raise_for_status()
            mmr_data = mmr_resp.json()['data']

            current_data = mmr_data.get('current_data', {})
            if current_data.get('currenttierpatched'):
                current_rank = current_data['currenttierpatched']
            if current_data.get('images', {}).get('small'):
                current_rank_image = current_data['images']['small']

            highest = mmr_data.get('highest_rank', {})
            if highest.get('patched_tier'):
                peak_rank = highest['patched_tier']
            if highest.get('tier'):
                peak_tier = highest['tier']
                peak_rank_image = f"https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/{peak_tier}/smallicon.png"
        except Exception as e:
            debug_log(f"Henrik MMR fetch failed: {e}")

        # Fetch match history for KDA
        kda_ratios = []
        try:
            matches_resp = requests.get(f"{base_url}/v3/matches/{region}/{urllib.parse.quote(in_game_name)}/{urllib.parse.quote(in_game_tag)}?filter=competitive")
            matches_resp.raise_for_status()
            matches_data = matches_resp.json()['data']
            for match in matches_data:
                players = match.get('players', {}).get('all_players', [])
                for player in players:
                    if player.get('name', '').lower() == in_game_name.lower() and player.get('tag', '').lower() == in_game_tag.lower():
                        stats = player.get('stats', {})
                        kills = stats.get('kills', 0)
                        deaths = stats.get('deaths', 1)
                        if deaths > 0:
                            kda_ratios.append(round(kills / deaths, 2))
                        break
        except Exception as e:
            debug_log(f"Henrik matches fetch failed: {e}")

        return AccountStats(
            banner=banner,
            account_level=account_level,
            account_level_tag_image=self.get_level_number_appearance(account_level),
            shard=region,
            current_season_time_played=time_played,
            current_rank=current_rank,
            current_rank_image=current_rank_image,
            peak_rank=peak_rank,
            peak_rank_image=peak_rank_image,
            kda_ratios=kda_ratios if kda_ratios else None
        )

    def fetch_rank_matches_kda_ratios(self, name, tag):
        in_game_name, in_game_tag = name, tag

        # Use cloudscraper to bypass Cloudflare protection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': f'https://tracker.gg/valorant/profile/riot/{urllib.parse.quote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}/overview',
                'Origin': 'https://tracker.gg',
            }
        endpoint = scraper.get(
            f"https://api.tracker.gg/api/v2/valorant/standard/matches/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}?type=competitive&season=&agent=all&map=all",
            headers=headers
        )
        endpoint.raise_for_status()
        data = endpoint.json()
        kd_ratios = []
        for match in data['data']['matches']:
            for segment in match['segments']:
                if 'kdRatio' in segment['stats']:
                    kd_ratios.append(segment['stats']['kdRatio']['value'])
        return kd_ratios
    
    def get_level_number_appearance(self, account_level):
        closest_index = None
        closest_url = None
        level_borders_id = ('ebc736cd-4b6a-137b-e2b0-1486e31312c9', '5156a90d-4d65-58d0-f6a8-48a0c003878a', '9c4afb15-40d7-3557-062a-4bb198cb9958', 'e6238102-425c-a647-6685-e6af7f8982d9', '49413ac2-4ed5-6953-5791-db838ccb58f3', 'e05371e3-4ec4-a53e-168a-c49346a75c19', '7e7feff1-44c2-301e-767d-d9b2b1cd9051', '53d4ed03-4b29-5913-aeda-80a41afcef3a', '6f610ab6-4a21-63fd-ac19-4a9204bc2721', '547ac9dd-495d-f11d-d921-3fbd14604ae0', 'bd1082ab-462c-3fb8-e049-28a9750acf0f', '37a36996-41f3-6e26-c00b-46bf7c037482', '5d0d6c6c-4f0a-dc65-e506-b786cc27dbe1', '3635b061-4bf9-b937-55fe-44a4dd0ed3dc', 'ae5eda0d-476b-a159-959c-df93374f4a69', '3d90bc3a-4626-71d6-a17c-93ae14d05fb0', '674bbd9e-4a4f-208a-75fa-1d9dd7d7008f', 'd84cf377-4c21-1cdf-0260-4e8ebd9825f5', '6c1fb61e-46e5-2908-5048-d4866cb64c3d', 'af1852a5-4e66-02a6-2ae3-ab8c885efb80', 'cbd1914e-43f8-7ae5-38c4-228bcbe58756', 'c8a4abff-4ace-f0a3-c9f3-db936791a697', '086dd1ab-4889-793a-4b33-0a99e311fa25', '08ab72f1-4fce-ddb5-5fd5-22abd3bc9d49', '6694d7f7-4ab9-8545-5921-35a9ea8cec24') 

        try:
            for i in range(len(level_borders_id)):
                starting_level = i * 20 + 1
                if starting_level <= account_level:
                    closest_index = i
                else:
                    break
        except Exception:
            closest_index = 0
        if closest_index is not None and closest_index < len(level_borders_id):
            closest_border_id = level_borders_id[closest_index]
            closest_url = f"https://media.valorant-api.com/levelborders/{closest_border_id}/levelnumberappearance.png"

        return closest_url

class AccountDetailsView(FlyoutViewBase):
    def __init__(self, rank_data=None, parent=None):
        super().__init__(parent)
        self.rank_data = rank_data
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setSpacing(10)
        self.infoLayout = QVBoxLayout()

        topInfoLayout = QHBoxLayout()
        self.accoutLevelLayout = QVBoxLayout()
        self.accoutLevelLayout.setSpacing(0)
        altitle = BodyLabel("Level")
        altitle.setStyleSheet("font-size: 12px;")
        self.accoutLevelLayout.addWidget(altitle, 0, Qt.AlignmentFlag.AlignHCenter)
        self.accoutLevelLayout.addWidget(StrongBodyLabel(str(self.rank_data.account_level)), 0, Qt.AlignmentFlag.AlignHCenter) 
        self.timePlayedLayout = QVBoxLayout()
        self.timePlayedLayout.setSpacing(0)
        tptitle = BodyLabel("Time Played")
        tptitle.setStyleSheet("font-size: 12px;")
        self.timePlayedLayout.addWidget(tptitle, 0, Qt.AlignmentFlag.AlignHCenter)
        self.timePlayedLayout.addWidget(StrongBodyLabel(self.rank_data.current_season_time_played),0, Qt.AlignmentFlag.AlignHCenter)
        topInfoLayout.addLayout(self.accoutLevelLayout)
        topInfoLayout.addLayout(self.timePlayedLayout)

        bottomInfoLayout = QHBoxLayout()
        currentRankLayout = QVBoxLayout()
        currentRankLayout.setSpacing(0)
        crtitle = BodyLabel("Current Rank")
        crtitle.setStyleSheet("font-size: 12px;")
        rank_image = Image(self.rank_data.current_rank_image)
        rank_image.scaledToHeight(15)
        rankTitleLayout = QHBoxLayout()
        rankTitleLayout.setSpacing(2)
        rankTitleLayout.addWidget(crtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        rankTitleLayout.addWidget(rank_image)
        currentRankLayout.addLayout(rankTitleLayout)
        currentRankLayout.addWidget(StrongBodyLabel(self.rank_data.current_rank), 0, Qt.AlignmentFlag.AlignHCenter)

        peakRankLayout = QVBoxLayout()
        peakRankLayout.setSpacing(0)
        prtitle = BodyLabel("Peak Rank")
        prtitle.setStyleSheet("font-size: 12px;")
        peak_image = Image(self.rank_data.peak_rank_image)
        peak_image.scaledToHeight(15)
        peakTitleLayout = QHBoxLayout()
        peakTitleLayout.setSpacing(2)
        peakTitleLayout.addWidget(prtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        peakTitleLayout.addWidget(peak_image)
        peakRankLayout.addLayout(peakTitleLayout)
        peakRankLayout.addWidget(StrongBodyLabel(self.rank_data.peak_rank), 0, Qt.AlignmentFlag.AlignHCenter)

        bottomInfoLayout.addLayout(currentRankLayout)
        bottomInfoLayout.addLayout(peakRankLayout)

        self.infoLayout.addLayout(topInfoLayout)
        self.infoLayout.addLayout(bottomInfoLayout)
        self.hBoxLayout.addLayout(self.infoLayout)

        bannerLayout = QHBoxLayout()
        banner_image = self.load_pixmap_from_url(self.rank_data.banner)
        level_tag = create_level_tag(self.rank_data.account_level_tag_image, str(self.rank_data.account_level))  # Adjust height as needed

        combined_pixmap = QPixmap(banner_image.size())
        combined_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(combined_pixmap)

        painter.drawPixmap(0, 0, banner_image)
        x = (banner_image.width() - level_tag.width()) // 2
        y = banner_image.height() - level_tag.height() - 2
        painter.drawPixmap(x, y, level_tag)
        painter.end()

        banner_label = ImageLabel()
        banner_label.setPixmap(combined_pixmap)
        banner_label.setBorderRadius(8, 8, 8, 8)
        self.hBoxLayout.addWidget(banner_label)

        # Add KDA chart
        if self.rank_data.kda_ratios:
            kda_chart = MatchesGraph(self.rank_data.kda_ratios)
            kda_chart.setFixedHeight(50)
            kda_chart.setFixedWidth(200)
            self.infoLayout.addWidget(kda_chart)

    def load_pixmap_from_url(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image
        else:
            # Handle failed download or return a default image
            return QPixmap()

    def paintEvent(self, e):
        pass


class CredentialCard(CardWidget):
    """Widget for displaying credentials."""
    # Signal emitted when the remove button is clicked
    removed = pyqtSignal(str)

    def __init__(self, username, password, in_game: tuple, section, rank_data, nickname="", is_last_used=False, parent=None):
        super().__init__(parent)
        self.section = section  # Store the section name
        self.username = username
        self.password = password
        self.in_game = in_game
        self.rank_data = rank_data
        self.nickname = nickname
        self.is_last_used = is_last_used
        self.session_manager = RiotSessionManager()
        self.use_deceive = False  # Track Deceive state per account

        to_display = (self.username, "") if not self.in_game else self.in_game
        if self.rank_data:
            current_rank_image = Image(self.rank_data.current_rank_image)
            current_rank_image.scaledToHeight(40)
        else:
            current_rank_image = QLabel("", self)
            current_rank_image.setFixedSize(40, 40)
        self.setup_ui(current_rank_image, to_display)
        # Enable context menu (right-click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Left-click shows details (only if rank data available)
        if self.rank_data:
            self.clicked.connect(self._on_left_click)
        self._ignore_click = False

    def download_background_image(self, image_url):
        response = requests.get(image_url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image

    def setup_details_tooltip(self):
        print("Showing details")
        PopupTeachingTip.make(
            target=self,
            view=AccountDetailsView(self.rank_data, self), # CustomFlyoutView(), # AccountDetailsView(self.rank_data, self),
            tailPosition=TeachingTipTailPosition.RIGHT,
            duration=-1,
            parent=self
        )

    def setup_ui(self, current_rank, title):
        """Initializes the UI components."""
        self.currentRank = current_rank

        # Create separate labels for in-game name and tag
        self.inGameNameLabel = QLabel(title[0], self)
        self.inGameNameLabel.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.inGameTagLabel = QLabel(f"#{title[1]}", self)
        self.inGameTagLabel.setStyleSheet("color: gray;")

        # Nickname label (optional)
        self.nicknameLabel = QLabel(f'"{self.nickname}"' if self.nickname else "", self)
        self.nicknameLabel.setStyleSheet("color: #4CAF50; font-size: 12px; font-style: italic;")

        # Last used indicator
        self.lastUsedLabel = QLabel("●", self)
        self.lastUsedLabel.setStyleSheet("color: #2196F3; font-size: 11px; font-weight: bold;")
        
        self.launchButton = PushButton('Launch', self)
        self.launchButton.setFixedWidth(75)
        self.deceiveCheckbox = CheckBox("", self)
        self.deceiveCheckbox.setFixedWidth(22)
        self.deceiveCheckbox.setToolTip("Launch with Deceive (appear offline)")
        self.deceiveCheckbox.stateChanged.connect(self.toggle_deceive)
        self.removeButton = ToolButton(FluentIcon.DELETE, self)
        self.removeButton.setFixedWidth(34)

        # Layouts
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(20, 11, 8, 8)
        self.hBoxLayout.setSpacing(8)
        nameTagLayout = QVBoxLayout()
        nameTagLayout.setContentsMargins(0, 0, 0, 0)
        nameTagLayout.setSpacing(0)
        rankLayout = QHBoxLayout()
        rankLayout.setSpacing(2)

        # Styling and Alignment
        self.setFixedHeight(83)

        rankLayout.addWidget(self.currentRank)

        # Name row with blue dot at end
        nameRow = QHBoxLayout()
        nameRow.setSpacing(4)
        nameRow.addWidget(self.inGameNameLabel)
        self.lastUsedLabel.setFixedWidth(10)
        self.lastUsedLabel.setVisible(self.is_last_used)
        nameRow.addWidget(self.lastUsedLabel)
        nameRow.addStretch(1)

        nameTagLayout.addLayout(nameRow)
        nameTagLayout.addWidget(self.inGameTagLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        if self.nickname:
            nameTagLayout.addWidget(self.nicknameLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        nameTagLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.hBoxLayout.addLayout(rankLayout)
        self.hBoxLayout.addLayout(nameTagLayout)
        self.hBoxLayout.addStretch(1)

        # Checkbox + Launch + Delete tightly grouped
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(2)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self.deceiveCheckbox)
        buttonLayout.addWidget(self.launchButton)
        buttonLayout.addWidget(self.removeButton)
        self.hBoxLayout.addLayout(buttonLayout)

        self.launchButton.clicked.connect(self.switch_account)
        self.removeButton.clicked.connect(self.remove_card)

    def _on_left_click(self):
        if not self._ignore_click:
            self.setup_details_tooltip()

    def mousePressEvent(self, event):
        # Block details popup when right-clicking
        from PyQt6.QtCore import Qt as QtCore
        self._ignore_click = (event.button() == QtCore.MouseButton.RightButton)
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        """Show right-click context menu."""
        menu = QMenu()

        full_name = f"{self.in_game[0]}#{self.in_game[1]}"
        copy_full_action = QAction(f"Copy ({full_name})", self)
        copy_full_action.triggered.connect(lambda: self.copy_to_clipboard(full_name))
        menu.addAction(copy_full_action)

        menu.exec(QCursor.pos())

    def copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Copied to clipboard: {text}')

    def set_last_used(self, is_last_used):
        """Update the last used indicator."""
        self.is_last_used = is_last_used
        self.is_last_used = is_last_used
        self.lastUsedLabel.setVisible(is_last_used)

    def toggle_deceive(self, state):
        """Toggle Deceive usage for this account."""
        self.use_deceive = state == 2  # Qt.CheckState.Checked
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Deceive {"enabled" if self.use_deceive else "disabled"} for {self.section}')

    def switch_account(self):
        """Switch to this account using session if available, otherwise use password login."""
        # Mark this account as last used
        self.save_last_used()

        # Check if we have a saved session
        if self.session_manager.has_session(self.section):
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Using session-based login for {self.section}')
            # Restore session and launch Riot Client
            if self.session_manager.restore_session(self.section):
                self._launch_riot_client()
            else:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Session restore failed, falling back to password login')
                self._password_login()
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] No session found, using password login')
            self._password_login()

    def save_last_used(self):
        """Save this account as the last used one."""
        config = get_config()
        if not config.has_section('SETTINGS'):
            config.add_section('SETTINGS')
        config.set('SETTINGS', 'LAST_USED', self.section)
        save_config()
        debug_log(f'Marked {self.section} as last used')

        # Update UI indicators for all cards
        if self.parent():
            self.parent().update_last_used_indicators(self.section)

    def _launch_riot_client(self):
        """Launch Riot Client with or without Deceive."""
        config = get_config()

        if self.use_deceive:
            # Launch with Deceive
            deceive_path = config['SETTINGS'].get('DECEIVE_PATH', '')
            deceive_path = os.path.expandvars(deceive_path)

            # Auto-download Deceive if not found
            if not deceive_path or not os.path.exists(deceive_path):
                deceive_path = os.path.join(os.path.expandvars('%USERPROFILE%'), 'Downloads', 'Deceive.exe')
                debug_log(f"Deceive not found, downloading to {deceive_path}...")
                try:
                    resp = requests.get('https://github.com/molenzwiebel/Deceive/releases/download/v1.16.0/Deceive.exe', stream=True)
                    resp.raise_for_status()
                    with open(deceive_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    debug_log("Deceive downloaded successfully")
                    # Update config with the path
                    cfg = get_config()
                    cfg['SETTINGS']['DECEIVE_PATH'] = r'%USERPROFILE%\Downloads\Deceive.exe'
                    save_config(cfg)
                except Exception as e:
                    debug_log(f"Failed to download Deceive: {e}")
                    self._launch_normal()
                    return

            try:
                subprocess.Popen([deceive_path, 'valorant'])
                debug_log('Riot Client launched with Deceive')
            except Exception as e:
                debug_log(f'Error launching Deceive: {e}')
                self._launch_normal()
        else:
            self._launch_normal()

    def _launch_normal(self):
        """Launch Riot Client normally."""
        riot_client_path = get_config()['SETTINGS']['RIOTCLIENT_PATH']
        try:
            subprocess.Popen([riot_client_path, '--launch-product=valorant', '--launch-patchline=live'])
            debug_log('Riot Client launched')
        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Error launching Riot Client: {e}')

    def _password_login(self):
        """Original password-based login method with auto-capture."""
        login = RiotAutoLogin(self.username, self.password)
        if is_process_running('RiotClientServices.exe'):
            success = login._send_login_keys()
            if success:
                # Auto-capture session after successful password login
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Waiting for Riot Client to fully load before capturing session...')
                time.sleep(3)  # Wait for Riot Client to stabilize
                self.auto_capture_session()
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Riot Client failed to start.')

    def auto_capture_session(self):
        """Automatically capture session after password login."""
        debug_log(f'Auto-capturing session for {self.section}...')
        if self.session_manager.save_session(self.section):
            debug_log(f'Session auto-captured! Next login will be instant.')
        else:
            debug_log(f'Auto-capture failed')

    def remove_card(self):
        """Emits the removed signal, deletes session, and hides the card."""
        # Delete saved session if it exists
        self.session_manager.delete_session(self.section)
        self.removed.emit(self.section)  # Emit the section name
        self.hide()

class AddAccountDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Account")

        layout = QVBoxLayout(self)
        hBoxLayout = QHBoxLayout()  # No parent needed here
        ingameLayout = QHBoxLayout()

        self.in_game_name = LineEdit(self)
        self.in_game_name.setPlaceholderText("In-game Name (auto-detect if empty)")
        ingameLayout.addWidget(self.in_game_name)
        self.in_game_tag = LineEdit(self)
        self.in_game_tag.setPlaceholderText("Tag (auto-detect if empty)")
        ingameLayout.addWidget(self.in_game_tag)

        detect_button = PushButton("Detect", self)
        detect_button.setFixedWidth(70)
        detect_button.clicked.connect(self.detect_game_name)
        ingameLayout.addWidget(detect_button)

        layout.addLayout(ingameLayout)

        self.nickname_input = LineEdit(self)
        self.nickname_input.setPlaceholderText("Nickname (optional, e.g., 'Main', 'Smurf', 'Alt')")
        layout.addWidget(self.nickname_input)

        self.username_input = LineEdit(self)
        self.username_input.setPlaceholderText("Riot Username (email - leave empty to auto-detect)")
        layout.addWidget(self.username_input)

        self.password_input = LineEdit(self)
        self.password_input.setPlaceholderText("Riot Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        add_button = PushButton("Add", self)
        add_button.clicked.connect(self.accept)
        hBoxLayout.addWidget(add_button)

        cancel_button = PushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        hBoxLayout.addWidget(cancel_button)

        layout.addLayout(hBoxLayout)  # Add the horizontal box layout to the main vertical layout

    def detect_game_name(self):
        """Auto-detect game name and tag from running Riot Client."""
        game_name, game_tag = App.auto_detect_game_name_tag()
        if game_name and game_tag:
            self.in_game_name.setText(game_name)
            self.in_game_tag.setText(game_tag)
        else:
            self.in_game_name.setPlaceholderText("Not detected - is Riot Client running?")

class App(FramelessWindow):
    """Main Application Window."""
    rank_data_fetched = pyqtSignal(tuple)
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)
        self.setWindowIcon(QIcon(resource_path('assets/iconVS.png')))
        self.cards = []
        self.thread = None

        # Setup system tray
        self.setup_system_tray()

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))
        self.splashScreen.show()

        self.credentialLoader = CredentialLoader(get_config_path())
        self.credentialLoader.credentials_loaded.connect(self.on_credentials_loaded)
        self.credentialLoader.start()
        self.rank_data_fetched.connect(self.add_new_card)

    def check_autostart(self):
        """Check if auto-start is enabled in Windows registry."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "ValoSwitcher")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Error checking auto-start: {e}')
            return False

    def enable_autostart(self):
        """Enable auto-start with Windows."""
        try:
            # Get the path to the executable
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                exe_path = sys.executable
            else:
                # Running as script - use pythonw to avoid console
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

            # Add to registry
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "ValoSwitcher", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Auto-start enabled')
            return True
        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Error enabling auto-start: {e}')
            return False

    def disable_autostart(self):
        """Disable auto-start with Windows."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "ValoSwitcher")
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Auto-start disabled')
            except FileNotFoundError:
                pass  # Already not in startup
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Error disabling auto-start: {e}')
            return False

    def toggle_autostart(self):
        """Toggle auto-start and update tray menu."""
        if self.check_autostart():
            if self.disable_autostart():
                self.notify("ValoSwitcher", "Auto-start disabled", 2000)
        else:
            if self.enable_autostart():
                self.notify("ValoSwitcher", "Auto-start enabled", 2000)
        # Update tray menu to reflect new state
        self.update_tray_menu()

    def setup_system_tray(self):
        """Setup system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path('assets/iconVS.png')))
        self.tray_icon.setToolTip('ValoSwitcher')

        # Create tray menu
        self.tray_menu = QMenu()

        # Show/Hide action
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.toggle_visibility)
        self.tray_menu.addAction(show_action)

        self.tray_menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def update_tray_menu(self):
        """Update tray menu with quick account access after cards are loaded."""
        # Clear old menu and rebuild
        self.tray_menu.clear()

        # Show/Hide action
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.toggle_visibility)
        self.tray_menu.addAction(show_action)

        # Add separator before accounts
        if self.cards:
            self.tray_menu.addSeparator()
            accounts_label = QAction("Quick Switch", self)
            accounts_label.setEnabled(False)
            self.tray_menu.addAction(accounts_label)

            # Add each account with keyboard shortcut
            for i, card in enumerate(self.cards[:9]):  # Limit to 9 accounts (Ctrl+1 to Ctrl+9)
                account_name = f"{card.in_game[0]}#{card.in_game[1]}"
                action = QAction(f"{i+1}. {account_name}", self)
                action.triggered.connect(lambda checked, c=card: c.switch_account())
                self.tray_menu.addAction(action)

        self.tray_menu.addSeparator()

        # Auto-start toggle
        autostart_action = QAction("Start with Windows", self)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(self.check_autostart())
        autostart_action.triggered.connect(self.toggle_autostart)
        self.tray_menu.addAction(autostart_action)

        self.tray_menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        self.tray_menu.addAction(quit_action)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for quick account switching."""
        for i, card in enumerate(self.cards[:9]):  # Ctrl+1 to Ctrl+9
            shortcut = QAction(self)
            shortcut.setShortcut(QKeySequence(f"Ctrl+{i+1}"))
            shortcut.triggered.connect(lambda checked, c=card: c.switch_account())
            self.addAction(shortcut)

    def tray_icon_activated(self, reason):
        """Handle tray icon activation (clicks)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            self.toggle_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:  # Double click
            self.toggle_visibility()

    def toggle_visibility(self):
        """Toggle window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        """Override close event to minimize to tray instead of closing."""
        event.ignore()
        self.hide()
        if not hasattr(self, '_tray_message_shown'):
            self.notify("ValoSwitcher", "Minimized to tray. Right-click to quit.", 2000)
            self._tray_message_shown = True

    def quit_application(self):
        """Properly quit the application."""
        if hasattr(self, 'account_monitor'):
            self.account_monitor.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def start_account_monitor(self):
        """Start background monitoring for Riot Client logins."""
        self.account_monitor = QTimer(self)
        self.account_monitor.timeout.connect(self.check_for_new_login)
        self.account_monitor.start(5000)  # Start with 5s idle check
        self._last_detected_account = None
        self._riot_was_running = False
        self.session_manager = RiotSessionManager()
        debug_log('Account monitor started - watching for Riot Client logins')

    def notify(self, title, message, duration=3000):
        """Show tray notification if notifications are enabled."""
        if get_setting('NOTIFICATIONS', 'true'):
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)

    def check_for_new_login(self):
        """Check if a new account has logged into Riot Client and auto-save it."""
        riot_running = is_process_running("RiotClientServices")

        if not riot_running:
            # Riot not running - slow poll, reset state
            if self._riot_was_running:
                debug_log('Riot Client closed - switching to slow polling')
                self._last_detected_account = None
            self._riot_was_running = False
            self.account_monitor.setInterval(5000)  # 5s when idle
            return

        # Riot Client is running - fast poll
        if not self._riot_was_running:
            debug_log('Riot Client detected - switching to fast polling')
            self.account_monitor.setInterval(2000)  # 2s when Riot is running
        self._riot_was_running = True

        game_name, game_tag = self.auto_detect_game_name_tag()

        if not game_name or not game_tag:
            return  # Riot running but not logged in yet (login screen)

        current_account = f"{game_name}:{game_tag}"

        # Skip if we already detected this account this session
        if current_account == self._last_detected_account:
            return

        self._last_detected_account = current_account
        debug_log(f'Detected login: {game_name}#{game_tag}')

        # Check if this account already exists in config
        config = get_config()

        existing_section = None
        for section in config.sections():
            if section == 'SETTINGS':
                continue
            if config[section].get('name', '') == current_account:
                existing_section = section
                break

        if existing_section:
            # Account exists - just update the session
            debug_log(f'Updating session for {game_name}#{game_tag}')
            self.session_manager.save_session(existing_section)
            self.notify("ValoSwitcher", f"Session updated for {game_name}#{game_tag}")
        else:
            # New account - auto-detect username, save config, capture session, add card
            debug_log(f'New account detected! Auto-saving {game_name}#{game_tag}')

            username = self.auto_detect_riot_username() or "auto@detected.com"

            # Save to config (no password needed for session-based switching)
            self.save_to_config(current_account, username, "")

            # Re-read config to get the new section
            config = load_config()
            new_section = None
            for section in config.sections():
                if section == 'SETTINGS':
                    continue
                if config[section].get('name', '') == current_account:
                    new_section = section
                    break

            # Capture the session
            if new_section:
                self.session_manager.save_session(new_section)

            # Add card to UI
            self.fetch_rank_and_add_new_card(current_account, username, "")

            self.notify("ValoSwitcher", f"New account saved: {game_name}#{game_tag}", 4000)

    def update_last_used_indicators(self, last_used_section):
        """Update last used indicators for all cards."""
        for card in self.cards:
            card.set_last_used(card.section == last_used_section)

    @pyqtSlot(list)
    def on_credentials_loaded(self, credentials):
        for credential in credentials:
            riot_username, pwd, in_game, section, rank_data, nickname, is_last_used = credential
            card = CredentialCard(riot_username, pwd, in_game, section, rank_data, nickname, is_last_used, self)
            card.removed.connect(self.remove_from_config)
            self.cards.append(card)

        self.createSubInterface()
        self.splashScreen.finish()
        self.showMainSubInterface()

        # Setup tray menu and keyboard shortcuts after cards are loaded
        self.update_tray_menu()
        self.setup_keyboard_shortcuts()

        # Start background account monitor
        self.start_account_monitor()

        # Check if should start minimized
        if '--minimized' in sys.argv or (self.check_autostart() and len(sys.argv) == 1):
            self.hide()
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Started minimized to tray')

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(500, loop.quit)
        loop.exec()

    def showMainSubInterface(self):
        self.setup_ui()  # Set layout and properties
        self.setup_ui_components()  # Add components/widgets

    def add_fixed_spacer(self, layout, size):
        """Add a fixed spacer to the given layout."""
        spacer = QSpacerItem(size, size, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addSpacerItem(spacer)

    def setup_ui(self):
        """Initializes the main UI layout and properties."""
        setTheme(Theme.DARK)
        self.resize(400, 600)
        self.setWindowTitle('ValoSwitcher')
        self.setWindowIcon(QIcon(resource_path('assets/titleVS.png')))
        self.layout = QVBoxLayout(self)

    def setup_ui_components(self):
        """Initializes and adds the UI components/widgets."""
        self.layout.addSpacing(20)
        self.layout.addWidget(self.create_image_label())
        self.add_fixed_spacer(self.layout, 20)  # Add spacer
        for card in self.cards:
            self.layout.addWidget(card)
        self.spacer = self.layout.addStretch(1)  # Update this line
        self.layout.addWidget(self.create_add_button())
        self.layout.addSpacing(20)

    def add_account(self):
        """Kill Riot, clear local session files (without signing out), and relaunch to login screen."""
        session_mgr = RiotSessionManager()

        # Save current session first if someone is logged in
        game_name, game_tag = self.auto_detect_game_name_tag()
        if game_name and game_tag:
            account_key = f"{game_name}:{game_tag}"
            session_mgr.save_session(account_key)
            debug_log(f"Saved current session for {account_key} before adding new account")

        # Kill Riot processes
        session_mgr.kill_riot_processes()

        # Delete local session files so Riot opens to login screen
        # This does NOT sign out server-side - saved sessions stay valid
        for file_info in session_mgr.session_files:
            source_path = file_info['source']
            try:
                if file_info['is_dir'] and os.path.exists(source_path):
                    shutil.rmtree(source_path)
                    debug_log(f"Cleared {file_info['name']} directory")
                elif os.path.exists(source_path):
                    os.remove(source_path)
                    debug_log(f"Cleared {file_info['name']}")
            except Exception as e:
                debug_log(f"Error clearing {file_info['name']}: {e}")

        # Launch Riot Client - will show login screen
        riot_client_path = get_config()['SETTINGS']['RIOTCLIENT_PATH']
        try:
            subprocess.Popen([riot_client_path, '--launch-product=valorant', '--launch-patchline=live'])
            self.notify("Log into your account - it will be detected automatically")
        except Exception as e:
            debug_log(f"Error launching Riot Client: {e}")

    def auto_detect_riot_username(self):
        """Try to auto-detect Riot username from system."""
        try:
            # Try to read from RiotGamesPrivateSettings.yaml
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            settings_path = os.path.join(local_app_data, 'Riot Games', 'Riot Client', 'Data', 'RiotGamesPrivateSettings.yaml')

            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for email pattern in the YAML file
                    import re
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, content)
                    if emails:
                        return emails[0]  # Return first email found
        except Exception as e:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Could not auto-detect Riot username: {e}')

        return None

    @staticmethod
    def auto_detect_game_name_tag():
        """Auto-detect in-game name and tag from Riot Client local API via lockfile."""
        try:
            import base64
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # First check if Riot Client is actually running
            if not is_process_running("RiotClientServices"):
                return None, None

            local_app_data = os.environ.get('LOCALAPPDATA', '')
            lockfile_path = os.path.join(local_app_data, 'Riot Games', 'Riot Client', 'Config', 'lockfile')

            if not os.path.exists(lockfile_path):
                return None, None

            with open(lockfile_path, 'r') as f:
                lockfile_data = f.read().strip().split(':')

            if len(lockfile_data) < 5:
                return None, None

            # Lockfile format: name:pid:port:password:protocol
            port = lockfile_data[2]
            password = lockfile_data[3]
            protocol = lockfile_data[4]

            # Query the local API for player alias
            auth = base64.b64encode(f'riot:{password}'.encode()).decode()
            headers = {'Authorization': f'Basic {auth}'}

            # Try chat session endpoint first (gives game_name and game_tag)
            try:
                response = requests.get(
                    f'{protocol}://127.0.0.1:{port}/chat/v1/session',
                    headers=headers,
                    verify=False,
                    timeout=3
                )

                if response.status_code == 200:
                    data = response.json()
                    game_name = data.get('game_name', '')
                    game_tag = data.get('game_tag', '')
                    if game_name and game_tag:
                        debug_log(f'Auto-detected: {game_name}#{game_tag}')
                        return game_name, game_tag
            except requests.exceptions.ConnectionError:
                pass  # Riot Client still starting up

            # Fallback: try aliases endpoint
            try:
                response = requests.get(
                    f'{protocol}://127.0.0.1:{port}/player-account/aliases/v1/current-player',
                    headers=headers,
                    verify=False,
                    timeout=3
                )

                if response.status_code == 200:
                    data = response.json()
                    game_name = data.get('game_name', '')
                    tag_line = data.get('tag_line', '')
                    if game_name and tag_line:
                        debug_log(f'Auto-detected: {game_name}#{tag_line}')
                        return game_name, tag_line
            except requests.exceptions.ConnectionError:
                pass  # Riot Client still starting up

        except Exception as e:
            debug_log(f'Auto-detect error: {e}')

        return None, None

    def save_to_config(self, name, username, password, nickname=""):
        config = get_config()

        # Count only ACCOUNT sections, not SETTINGS
        account_count = sum(1 for s in config.sections() if s.startswith('ACCOUNT'))
        section_name = f"ACCOUNT{account_count}"

        config[section_name] = {
            'name': name,
            'riot_username': username,
            'password': password
        }

        if nickname:
            config[section_name]['nickname'] = nickname

        save_config()

    def fetch_rank_and_add_new_card(self, name, username, password, nickname=""):
        in_game_name, in_game_tag = name.split(":")
        section_name = f"ACCOUNT{len(self.cards)}"  # New section name

        def fetch_rank():
            try:
                rank_data = self.credentialLoader.fetch_account(section_name, {
                    'name': name,
                    'riot_username': username,
                    'password': password,
                    'nickname': nickname
                })
            except Exception as e:
                debug_log(f'Failed to retrieve rank data for {section_name}: {e}')
                rank_data = None
            self.rank_data_fetched.emit((username, password, (in_game_name, in_game_tag), section_name, rank_data, nickname))

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(fetch_rank)

    @pyqtSlot(tuple)
    def add_new_card(self, credential):
        username, password, in_game, section_name, rank_data, nickname = credential
        new_card = CredentialCard(username, password, in_game, section_name, rank_data, nickname, False, self)
        new_card.removed.connect(self.remove_from_config)
        self.cards.append(new_card)
        self.layout.insertWidget(self.layout.count() - 3, new_card)

        # Update tray menu and shortcuts when new account is added
        self.update_tray_menu()
        self.setup_keyboard_shortcuts()

    def create_image_label(self):
        """Creates and returns an image label."""
        pixmap = QIcon(resource_path("assets/titleVS.png")).pixmap(200, 200)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return image_label

    def create_credential_card(self, icon, username, password, content):
        """Creates and returns a credential card."""
        return CredentialCard(icon, username, password, content, self)

    def create_add_button(self):
        """Creates and returns a generate account button."""
        self.add_account_btn = PushButton('Add Account', self, FluentIcon.ADD)
        self.add_account_btn.clicked.connect(self.add_account)
        return self.add_account_btn

    def remove_from_config(self, section):
        """Remove an account from the config.ini file."""
        config = get_config()

        if config.has_section(section):
            config.remove_section(section)
            save_config()
        # Also remove the card from the UI and the list of cards
        for card in self.cards:
            if card.section == section:
                self.layout.removeWidget(card)
                card.deleteLater()
                self.cards.remove(card)
                break

        # Update tray menu and shortcuts after removal
        self.update_tray_menu()
        self.setup_keyboard_shortcuts()

if __name__ == '__main__':
    # Open a console window if debug is enabled (works even with --windowed exe)
    import ctypes
    load_config()  # Load config early to check debug setting
    if _debug_mode:
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open('CONOUT$', 'w')
        sys.stderr = open('CONOUT$', 'w')
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Debug console opened')

    os.environ["QT_LOGGING_RULES"] = "*.warning=false;*.critical=false"
    app = QApplication(sys.argv)

    # Styling
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    pixmap = QPixmap(resource_path("assets/bg.png"))
    painter = QPainter(pixmap)
    overlay = QColor(0, 0, 0, 150)
    painter.fillRect(pixmap.rect(), overlay)
    painter.end()
    brush = QBrush(pixmap)
    palette.setBrush(QPalette.ColorRole.Window, brush)
    app.setPalette(palette)

    window = App()
    window.show()
    app.exec()
