import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog, scrolledtext
import hashlib
import shutil
import urllib.request
import urllib.error
import locale
from concurrent.futures import ThreadPoolExecutor, as_completed
import minecraft_launcher_lib
import minecraft_launcher_lib.forge
import minecraft_launcher_lib.fabric

# Пытаемся импортировать Pillow для фона и pygame для музыки
try:
    from PIL import Image, ImageTk, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# --- МАГИЯ ДЛЯ EXE (Ищет файлы внутри программы) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def safe_download(url, dest):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        return False

# --- СЛОВАРИ ПЕРЕВОДОВ ---
TEXTS = {
    "ru": {
        "title": "AIZEN LAUNCHER",
        "subtitle": "«Никто не стоит на вершине с самого начала»",
        "btn_folder": "📁 ПАПКА",
        "btn_logs": "🧹 ЛОГИ",
        "btn_mods": "⚙️ МОДЫ",
        "btn_play": "▶ ВОЗВЫСИТЬСЯ",
        "lbl_username": "ИМЯ СУБЪЕКТА:",
        "lbl_version": "ЭВОЛЮЦИЯ (ВЕРСИЯ):",
        "lbl_java": "ПУТЬ К JAVA:",
        "lbl_ram": "ДУХОВНАЯ ЭНЕРГИЯ (ОЗУ МБ):",
        "status_ready": "Всё идет по плану...",
        "status_loading": "Иллюзия загружается...",
        "status_music_play": "Иллюзия звука...",
        "status_music_stop": "Тишина...",
        "msg_crash": "Крах",
        "msg_fail": "План потерпел неудачу:",
        "mods_title": "Установка Модификаций Хогёку",
        "mods_forge": " Интеграция Forge ",
        "mods_fabric": " Интеграция Fabric ",
        "mods_install": "Установить",
        "log_hidden": "Показать иллюзию",
        "log_visible": "Скрыть иллюзию",
    },
    "en": {
        "title": "AIZEN LAUNCHER",
        "subtitle": "«No one stands on the top from the very beginning»",
        "btn_folder": "📁 FOLDER",
        "btn_logs": "🧹 LOGS",
        "btn_mods": "⚙️ MODS",
        "btn_play": "▶ ASCEND",
        "lbl_username": "SUBJECT NAME:",
        "lbl_version": "EVOLUTION (VERSION):",
        "lbl_java": "JAVA PATH:",
        "lbl_ram": "SPIRITUAL ENERGY (RAM MB):",
        "status_ready": "Everything is going according to plan...",
        "status_loading": "Illusion is loading...",
        "status_music_play": "Sound illusion...",
        "status_music_stop": "Silence...",
        "msg_crash": "Crash",
        "msg_fail": "The plan failed:",
        "mods_title": "Hogyoku Mod Installer",
        "mods_forge": " Forge Integration ",
        "mods_fabric": " Fabric Integration ",
        "mods_install": "Install",
        "log_hidden": "Show Illusion",
        "log_visible": "Hide Illusion",
    }
}

class AizenCraftLauncher(tk.Tk):
    def __init__(self):
        super().__init__()

        # Определяем язык системы (если русский - ставим ru, иначе en)
        sys_lang = locale.getdefaultlocale()[0]
        self.lang = "ru" if sys_lang and sys_lang.startswith("ru") else "en"

        self.title("Kyoka Suigetsu Launcher — Ultimate Hybrid Edition")
        self.geometry("900x550")
        self.minsize(800, 500) 
        self.resizable(True, True) 
        self.configure(bg="#0b0b0f")
        
        self.last_width = 900
        self.last_height = 550
        
        self.minecraft_dir = os.path.join(os.getcwd(), ".minecraft")
        self.mods_dir = os.path.join(self.minecraft_dir, "mods")
        if not os.path.exists(self.minecraft_dir): os.makedirs(self.minecraft_dir)
        if not os.path.exists(self.mods_dir): os.makedirs(self.mods_dir)
            
        self.config_file = os.path.join(os.getcwd(), "aizen_config.json")

        # Инициализация музыки
        self.music_playing = False
        self.music_files = []
        self.current_track_index = 0
        if HAS_PYGAME:
            try:
                pygame.mixer.init()
                music_dir = resource_path("music")
                if os.path.exists(music_dir):
                    for f in os.listdir(music_dir):
                        if f.endswith(('.mp3', '.ogg')):
                            self.music_files.append(os.path.join(music_dir, f))
            except Exception as e:
                pass

        self.saved_config = self.load_config()
        
        # ФОН
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#0b0b0f")
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1) 
        
        bg_path = None
        if os.path.exists(resource_path("bg.jpg")): bg_path = resource_path("bg.jpg")
        elif os.path.exists(resource_path("bg.png")): bg_path = resource_path("bg.png")
        
        self.original_bg = None
        if HAS_PIL and bg_path:
            try:
                self.original_bg = Image.open(bg_path)
            except Exception: pass
        else:
            self.canvas.create_rectangle(0, 0, 2000, 2000, fill="#0b0b0f", outline="")

        # СТИЛИ
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Control.TFrame", background="#121218")
        self.style.configure("Text.TLabel", background="#121218", foreground="#dcd7fa", font=("Segoe UI", 10, "bold"))
        self.style.configure("Title.TLabel", background="#121218", foreground="#c084fc", font=("Impact", 22))
        self.style.configure("Subtitle.TLabel", background="#121218", foreground="#94a3b8", font=("Segoe UI", 8))
        self.style.configure("BigButton.TButton", background="#581c87", foreground="white", font=("Segoe UI", 13, "bold"))
        self.style.map("BigButton.TButton", background=[("active", "#6b21a8")])
        self.style.configure("Purple.Horizontal.TProgressbar", troughcolor="#09090b", borderColor="#121218", background="#a855f7")
        self.style.configure("Small.TButton", background="#1e1b4b", foreground="#c084fc", font=("Segoe UI", 9, "bold"))
        self.style.map("Small.TButton", background=[("active", "#312e81")])
        self.style.configure("TEntry", fieldbackground="#1e1b4b", foreground="white")
        self.style.configure("TCombobox", fieldbackground="#1e1b4b", foreground="white")

        self.build_ui()
        self.bind("<Configure>", self.on_resize)
        threading.Thread(target=self.load_all_versions, daemon=True).start()

    def tr(self, key):
        """Возвращает текст на текущем языке"""
        return TEXTS[self.lang].get(key, key)

    def build_ui(self):
        self.side_panel = ttk.Frame(self, style="Control.TFrame")
        self.side_panel.place(x=520, y=20, width=360, height=510)
        self.side_panel.pack_propagate(False)

        # Заголовок
        ttk.Label(self.side_panel, text=self.tr("title"), style="Title.TLabel").pack(pady=(12, 0))
        ttk.Label(self.side_panel, text=self.tr("subtitle"), style="Subtitle.TLabel").pack(pady=(0, 5))

        # Кнопки утилит
        folder_frame = ttk.Frame(self.side_panel, style="Control.TFrame")
        folder_frame.pack(pady=(5, 5))
        ttk.Button(folder_frame, text=self.tr("btn_folder"), style="Small.TButton", command=self.open_game_folder).pack(side="left", padx=2)
        ttk.Button(folder_frame, text=self.tr("btn_logs"), style="Small.TButton", command=self.clear_logs).pack(side="left", padx=2)
        ttk.Button(folder_frame, text=self.tr("btn_mods"), style="Small.TButton", command=self.open_mod_installer).pack(side="left", padx=2)
        
        # Кнопка смены языка
        lang_btn = ttk.Button(folder_frame, text=f"[{self.lang.upper()}]", width=4, style="Small.TButton", command=self.switch_language)
        lang_btn.pack(side="left", padx=2)

        # Кнопки музыки
        music_frame = ttk.Frame(self.side_panel, style="Control.TFrame")
        music_frame.pack(pady=(0, 10))
        ttk.Button(music_frame, text="⏮", style="Small.TButton", command=self.prev_track).pack(side="left", padx=2)
        ttk.Button(music_frame, text="▶/⏸", style="Small.TButton", command=self.toggle_music).pack(side="left", padx=2)
        ttk.Button(music_frame, text="⏭", style="Small.TButton", command=self.next_track).pack(side="left", padx=2)

        ttk.Label(self.side_panel, text=self.tr("lbl_username"), style="Text.TLabel").pack(anchor="w", padx=25)
        self.username_entry = ttk.Entry(self.side_panel, font=("Segoe UI", 11), width=28)
        self.username_entry.pack(pady=(2, 10))
        self.username_entry.insert(0, self.saved_config.get("username", "AizenSousuke"))

        ttk.Label(self.side_panel, text=self.tr("lbl_version"), style="Text.TLabel").pack(anchor="w", padx=25)
        self.version_select = ttk.Combobox(self.side_panel, font=("Segoe UI", 11), state="readonly", width=26)
        self.version_select.pack(pady=(2, 10))
        self.version_select.set(self.tr("status_loading"))

        ttk.Label(self.side_panel, text=self.tr("lbl_java"), style="Text.TLabel").pack(anchor="w", padx=25)
        java_frame = ttk.Frame(self.side_panel, style="Control.TFrame")
        java_frame.pack(fill="x", padx=25, pady=(2, 10))
        self.java_entry = ttk.Entry(java_frame, font=("Segoe UI", 9), width=23)
        self.java_entry.pack(side="left", fill="x", expand=True)
        self.java_entry.insert(0, self.saved_config.get("java_path", "java"))
        ttk.Button(java_frame, text="...", width=3, style="Small.TButton", command=self.pick_java).pack(side="right", padx=(5,0))

        default_ram = self.saved_config.get("ram_mb", 1024)
        ttk.Label(self.side_panel, text=self.tr("lbl_ram"), style="Text.TLabel").pack(anchor="w", padx=25)
        self.ram_label = ttk.Label(self.side_panel, text=f"{default_ram} MB", style="Text.TLabel")
        self.ram_label.pack(anchor="w", padx=25)
        self.ram_scale = ttk.Scale(self.side_panel, from_=512, to=8192, command=self.update_ram_text)
        self.ram_scale.set(default_ram)
        self.ram_scale.pack(fill="x", padx=25, pady=2)

        self.progress = ttk.Progressbar(self.side_panel, style="Purple.Horizontal.TProgressbar", mode="determinate", length=310)
        self.progress.pack(pady=(10, 5))
        self.status_label = tk.Label(self.side_panel, text=self.tr("status_ready"), bg="#121218", fg="#c084fc", font=("Segoe UI", 9))
        self.status_label.pack(pady=5)

        self.launch_btn = ttk.Button(self.side_panel, text=self.tr("btn_play"), style="BigButton.TButton", command=self.start_launch_thread)
        self.launch_btn.pack(side="bottom", fill="x", padx=25, pady=15)

        # ЛОГИ
        self.log = scrolledtext.ScrolledText(self, bg="#070709", fg="#a855f7", font=("Consolas", 9), state="disabled", highlightthickness=0)
        self.log.place(x=20, y=300, width=480, height=230) 
        
        self.log_btn = ttk.Button(self, text=self.tr("log_visible"), style="Small.TButton", command=self.toggle_log)
        self.log_btn.place(x=20, y=268)
        self.log_visible = True

        self.log_msg("«С самого начала никто не стоял на небесах. Ни ты, ни я, и даже не Бог».")
        self.log_msg("— Сосуке Айзен.")
        self.log_msg("--------------------------------------------------")

    def switch_language(self):
        self.lang = "en" if self.lang == "ru" else "ru"
        # Пересобираем интерфейс
        for widget in self.winfo_children():
            widget.destroy()
        
        # Пересоздаем Canvas для фона
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#0b0b0f")
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1) 
        if HAS_PIL and self.original_bg:
            self.on_resize(type('Event', (object,), {'widget': self, 'width': self.last_width, 'height': self.last_height}))
        else:
            self.canvas.create_rectangle(0, 0, 2000, 2000, fill="#0b0b0f", outline="")
            
        self.build_ui()
        self.on_resize(type('Event', (object,), {'widget': self, 'width': self.last_width, 'height': self.last_height}))

    def on_resize(self, event):
        if event.widget == self and (self.last_width != event.width or self.last_height != event.height):
            self.last_width = event.width
            self.last_height = event.height
            
            if HAS_PIL and self.original_bg:
                try:
                    img = self.original_bg.resize((event.width, event.height), Image.Resampling.BILINEAR)
                    img = ImageEnhance.Brightness(img).enhance(0.25)
                    self.bg_photo = ImageTk.PhotoImage(img)
                    self.canvas.delete("bg")
                    self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="bg")
                except Exception: pass

            panel_x = event.width - 380
            if panel_x > 300:
                self.side_panel.place(x=panel_x, y=20, width=360, height=event.height - 40)
            
            log_w = event.width - 420
            log_h = event.height - 320
            if log_w > 100 and log_h > 100:
                self.log.place(x=20, y=event.height - 250, width=log_w, height=log_h)
                self.log_btn.place(x=20, y=event.height - 282)

    def play_current_track(self):
        if not self.music_files or not HAS_PYGAME: return
        try:
            track = self.music_files[self.current_track_index]
            pygame.mixer.music.load(track)
            pygame.mixer.music.play(-1)
            self.music_playing = True
            self.log_msg(f"🎵 Playing: {os.path.basename(track)}")
            self.status_label.configure(text=self.tr("status_music_play"))
        except Exception as e:
            self.log_msg(f"Music error: {e}")

    def toggle_music(self):
        if not HAS_PYGAME:
            messagebox.showerror("Error", "pygame is not installed!")
            return
        if not self.music_files:
            messagebox.showinfo("Music", "No music files found!")
            return

        if self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False
            self.log_msg("🎵 Music stopped.")
            self.status_label.configure(text=self.tr("status_music_stop"))
        else:
            self.play_current_track()

    def next_track(self):
        if not self.music_files or not HAS_PYGAME: return
        self.current_track_index = (self.current_track_index + 1) % len(self.music_files)
        if self.music_playing: self.play_current_track()

    def prev_track(self):
        if not self.music_files or not HAS_PYGAME: return
        self.current_track_index = (self.current_track_index - 1) % len(self.music_files)
        if self.music_playing: self.play_current_track()

    def toggle_log(self):
        if self.log_visible: 
            self.log.place_forget()
            self.log_btn.config(text=self.tr("log_hidden"))
        else: 
            self.log.place(x=20, y=self.last_height - 250, width=self.last_width - 420, height=self.last_height - 320)
            self.log_btn.config(text=self.tr("log_visible"))
        self.log_visible = not self.log_visible

    def pick_java(self):
        p = filedialog.askopenfilename(filetypes=[("Java executable", "java.exe"), ("All files", "*.*")])
        if p: self.java_entry.delete(0, "end"); self.java_entry.insert(0, p)

    def update_ram_text(self, val): self.ram_label.configure(text=f"{int(float(val))} MB")

    def offline_uuid(self, name):
        d = bytearray(hashlib.md5(("AizenPlayer:"+name).encode()).digest())
        d[6] = (d[6] & 0x0f) | 0x30; d[8] = (d[8] & 0x3f) | 0x80
        return ''.join(f"{b:02x}" for b in d)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f: return json.load(f)
            except Exception: pass
        return {}

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"username": self.username_entry.get().strip(), "ram_mb": int(float(self.ram_scale.get())), "java_path": self.java_entry.get().strip(), "version": self.version_select.get()}, f, ensure_ascii=False, indent=4)
        except Exception: pass

    def open_game_folder(self):
        try: os.startfile(self.minecraft_dir)
        except Exception as e: messagebox.showerror("Error", str(e))

    def clear_logs(self):
        for folder in [os.path.join(self.minecraft_dir, "logs"), os.path.join(self.minecraft_dir, "crash-reports")]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    try:
                        p = os.path.join(folder, f)
                        shutil.rmtree(p) if os.path.isdir(p) else os.unlink(p)
                    except Exception: pass
        messagebox.showinfo("Kyoka Suigetsu", "Logs cleared.")

    def log_msg(self, msg):
        def _():
            self.log.configure(state="normal")
            self.log.insert("end", "[Aizen] " + msg + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(0, _)

    def load_all_versions(self):
        try:
            local_versions = []
            try:
                installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                local_versions = [v['id'] for v in installed]
            except Exception: pass

            online_versions = []
            try:
                full_list = minecraft_launcher_lib.utils.get_version_list()
                online_versions = [v['id'] for v in full_list if v['type'] == 'release']
            except Exception:
                online_versions = ["1.20.1", "1.16.5", "1.12.2"]

            final_versions = list(local_versions)
            for v in online_versions:
                if v not in final_versions: final_versions.append(v)

            self.after(0, lambda: self.update_version_box(final_versions))
        except Exception as e:
            self.after(0, lambda: self.update_version_box(["1.16.5", "1.12.2"]))

    def update_version_box(self, versions):
        self.version_select.configure(values=versions)
        saved_ver = self.saved_config.get("version")
        if saved_ver and saved_ver in versions: self.version_select.set(saved_ver)
        elif versions: self.version_select.set(versions[0])
        self.status_label.configure(text=self.tr("status_ready"), fg="#c084fc")

    def check_single_asset(self, item):
        expected_hash, path = item
        if not os.path.exists(path): return path
        h = hashlib.sha1()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
            if h.hexdigest() != expected_hash.lower(): return path
        except Exception: return path
        return None

    def fast_download_assets(self, ver_id):
        base_ver = ver_id.split("-")[0] if "forge" in ver_id else ver_id
        version_json_path = os.path.join(self.minecraft_dir, "versions", base_ver, f"{base_ver}.json")
        if not os.path.exists(version_json_path): return

        try:
            with open(version_json_path, "r", encoding="utf-8") as f: ver_data = json.load(f)
        except Exception: return

        asset_index_info = ver_data.get("assetIndex")
        if not asset_index_info: return

        index_path = os.path.join(self.minecraft_dir, "assets", "indexes", f"{asset_index_info['id']}.json")
        if not os.path.exists(index_path): safe_download(asset_index_info["url"], index_path)

        with open(index_path, "r", encoding="utf-8") as f: index_data = json.load(f)

        objects = index_data.get("objects", {})
        total_assets = len(objects)
        items_to_check = [(obj["hash"], os.path.join(self.minecraft_dir, "assets", "objects", obj["hash"][:2], obj["hash"])) for obj in objects.values()]

        bad_files = []
        done = 0
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(self.check_single_asset, item) for item in items_to_check]
            for future in as_completed(futures):
                res = future.result()
                if res: bad_files.append(res)
                done += 1

        if not bad_files: return

        def download_obj(path):
            h = os.path.basename(path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            safe_download(f"https://resources.download.minecraft.net/{h[:2]}/{h}", path)

        with ThreadPoolExecutor(max_workers=24) as executor:
            futures = [executor.submit(download_obj, p) for p in bad_files]
            for _ in as_completed(futures): pass

    def set_status(self, text): self.after(0, lambda: self.status_label.configure(text=text, fg="#c084fc"))
    def set_progress(self, val): self.after(0, lambda: self.progress.configure(value=val))
    def set_max(self, val): self.after(0, lambda: self.progress.configure(maximum=val))

    def start_launch_thread(self):
        if self.music_playing and HAS_PYGAME:
            pygame.mixer.music.stop()
            self.music_playing = False
            
        self.save_config()
        self.launch_btn.configure(state="disabled")
        threading.Thread(target=self.launch_game, daemon=True).start()

    def launch_game(self):
        user, ver, ram_mb, java_path = self.username_entry.get().strip(), self.version_select.get(), int(float(self.ram_scale.get())), self.java_entry.get().strip()
        if not user or ver == self.tr("status_loading"): 
            self.after(0, lambda: self.launch_btn.configure(state="normal"))
            return

        callback = {"setStatus": self.set_status, "setProgress": self.set_progress, "setMax": self.set_max}

        try:
            self.fast_download_assets(ver)
            
            if "forge" not in ver.lower() and "optifine" not in ver.lower() and "fabric" not in ver.lower():
                try:
                    minecraft_launcher_lib.install.install_minecraft_version(ver, self.minecraft_dir, callback=callback)
                except Exception as e:
                    if "SSL" in str(e) or "java-runtime" in str(e): 
                        self.log_msg("Provider block/SSL error. Continuing launch...")
                    else: raise e
            
            jvm_args = [f"-Xmx{ram_mb}M", "-Xms512M", "-XX:+UseG1GC"]
            
            optifine_jar = None
            if "forge" not in ver.lower() and "optifine" not in ver.lower() and "fabric" not in ver.lower():
                for f in os.listdir(self.mods_dir):
                    if f.lower().startswith("optifine") and f.endswith(".jar"):
                        optifine_jar = os.path.join(self.mods_dir, f)
                        break

            options = {"username": user, "uuid": self.offline_uuid(user), "token": "0", "executablePath": java_path, "jvmArguments": jvm_args}
            cmd = minecraft_launcher_lib.command.get_minecraft_command(ver, self.minecraft_dir, options)

            if optifine_jar:
                lw_url = "https://maven.minecraftforge.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar"
                asm_url = "https://repo1.maven.org/maven2/org/ow2/asm/asm-all/5.2/asm-all-5.2.jar"
                lw_path, asm_path = os.path.join(self.minecraft_dir, "launchwrapper-1.12.jar"), os.path.join(self.minecraft_dir, "asm-all-5.2.jar")
                
                if not os.path.exists(lw_path): safe_download(lw_url, lw_path)
                if not os.path.exists(asm_path): safe_download(asm_url, asm_path)

                try:
                    cp_index = cmd.index("-cp") + 1
                    cmd[cp_index] = cmd[cp_index] + os.pathsep + optifine_jar + os.pathsep + lw_path + os.pathsep + asm_path
                except ValueError: pass

                if "net.minecraft.client.main.Main" in cmd:
                    main_idx = cmd.index("net.minecraft.client.main.Main")
                    cmd[main_idx] = "net.minecraft.launchwrapper.Launch"
                    cmd.insert(main_idx + 1, "--tweakClass")
                    cmd.insert(main_idx + 2, "optifine.OptiFineTweaker")

            self.after(0, self.withdraw)
            proc = subprocess.Popen(cmd, cwd=self.minecraft_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            for line in proc.stdout: self.log_msg(line.rstrip())
            proc.wait()
            
        except Exception as e:
            self.log_msg(f"Error: {e}")
            messagebox.showerror(self.tr("msg_crash"), f"{self.tr('msg_fail')}\n{str(e)}")
        finally:
            self.after(0, self.deiconify)
            self.after(0, lambda: self.launch_btn.configure(state="normal"))
            self.after(0, lambda: self.progress.configure(value=0))
            self.set_status(self.tr("status_ready"))
            self.load_all_versions()

    def open_mod_installer(self):
        InstallerWindow(self, self.lang, self.tr)

class InstallerWindow(tk.Toplevel):
    def __init__(self, master, lang, tr):
        super().__init__(master)
        self.master = master
        self.lang = lang
        self.tr = tr
        self.title(tr("mods_title"))
        self.geometry("450x400")
        self.configure(bg="#121218")
        self.resizable(False, False)
        self.grab_set()

        self.style = ttk.Style()
        self.style.configure("Inst.TLabel", background="#121218", foreground="#dcd7fa", font=("Segoe UI", 10))
        self.style.configure("InstTitle.TLabel", background="#121218", foreground="#c084fc", font=("Impact", 18))
        self.style.configure("Inst.TButton", background="#581c87", foreground="white", font=("Segoe UI", 10, "bold"))
        self.style.map("Inst.TButton", background=[("active", "#6b21a8")])

        ttk.Label(self, text="HOGYOKU INSTALLER", style="InstTitle.TLabel").pack(pady=(15, 10))
        
        frame_forge = tk.LabelFrame(self, text=tr("mods_forge"), bg="#121218", fg="#c084fc", bd=2, relief="groove")
        frame_forge.pack(fill="x", padx=20, pady=5)
        self.forge_combo = ttk.Combobox(frame_forge, state="readonly", width=40)
        self.forge_combo.pack(padx=10, pady=5)
        ttk.Button(frame_forge, text=f"{tr('mods_install')} Forge", style="Inst.TButton", command=self.install_forge).pack(pady=5)

        frame_fabric = tk.LabelFrame(self, text=tr("mods_fabric"), bg="#121218", fg="#c084fc", bd=2, relief="groove")
        frame_fabric.pack(fill="x", padx=20, pady=5)
        ttk.Button(frame_fabric, text=f"{tr('mods_install')} Fabric", style="Inst.TButton", command=self.install_fabric).pack(pady=5)

        self.status_lbl = ttk.Label(self, text="", style="Inst.TLabel")
        self.status_lbl.pack(pady=5)
        self.load_forge_versions()

    def load_forge_versions(self):
        mc_ver = self.master.version_select.get().split("-")[0]
        def _fetch():
            try:
                forge_versions = minecraft_launcher_lib.forge.list_forge_versions()
                filtered = [v for v in forge_versions if v.startswith(mc_ver + "-")]
                filtered.reverse()
                self.after(0, lambda: self.forge_combo.configure(values=filtered))
                if filtered: self.after(0, lambda: self.forge_combo.set(filtered[0]))
            except Exception: pass
        threading.Thread(target=_fetch, daemon=True).start()

    def install_forge(self):
        forge_ver = self.forge_combo.get()
        if not forge_ver: return
        self.status_lbl.config(text="Installing Forge...")
        def _install():
            try:
                callback = {"setStatus": lambda t: self.after(0, lambda: self.status_lbl.config(text=t))}
                minecraft_launcher_lib.forge.install_forge_version(forge_ver, self.master.minecraft_dir, callback=callback)
                self.after(0, lambda: messagebox.showinfo("Success", "Forge installed!"))
                self.master.load_all_versions()
                self.destroy()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        threading.Thread(target=_install, daemon=True).start()

    def install_fabric(self):
        mc_ver = self.master.version_select.get().split("-")[0]
        self.status_lbl.config(text="Installing Fabric...")
        def _install():
            try:
                minecraft_launcher_lib.fabric.install_fabric(mc_ver, self.master.minecraft_dir)
                self.after(0, lambda: messagebox.showinfo("Success", "Fabric installed!"))
                self.master.load_all_versions()
                self.destroy()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        threading.Thread(target=_install, daemon=True).start()

if __name__ == "__main__":
    app = AizenCraftLauncher()
    app.mainloop()