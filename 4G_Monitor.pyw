import customtkinter as ctk
from tracker import DataTracker
import threading
import time
import os
import sys
import ctypes
from PIL import Image, ImageTk
import socket
import psutil
import webbrowser

# Configuration de l'apparence
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# FORCER le répertoire de travail
# C'est CRUCIAL pour le démarrage auto, sinon Windows lance depuis System32
# et l'app ne trouve ni le json (donc affiche 0GB) ni l'icone.
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception as e:
    pass

# Mécanisme d'instance unique (Empêche d'ouvrir 2 fois l'app)
def get_lock(process_name):
    # On utilise un socket bloquant sur un port local spécifique
    # Si le port est déjà pris, c'est que l'app tourne déjà
    get_lock._lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind(('127.0.0.1', 12345)) # Port arbitraire
    except socket.error:
        print("Application déjà lancée.")
        sys.exit()

get_lock("4g_monitor_lock")

# ID unique pour Windows (permet d'avoir sa propre icone dans la barre des taches)
# ID unique dynamique basé sur le nom du fichier pour éviter les conflits d'icônes entre apps
script_name = os.path.splitext(os.path.basename(__file__))[0]
myappid = f'obat.{script_name}.v1' 
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialisation du tracker
        self.tracker = DataTracker()
        self.running = True

        # Configuration de la fenêtre principale
        self.title("4G Monitor")
        self.geometry("300x530") # Un peu plus haut pour le switch
        self.resizable(False, False)
        
        # État par défaut du TopMost
        self.topmost_enabled = self.tracker.data.get("topmost_enabled", True)
        self.attributes('-topmost', self.topmost_enabled)
        
        # Gestion robuste de l'icône avec délai pour s'assurer qu'elle s'applique
        self.after(200, self.set_icon)

        # Grille
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

    def set_icon(self):
        # Méthode 1: .ico classique
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(default=icon_path)
        except Exception:
            pass

        # Méthode 2: Supprimée pour éviter les conflits. 
        # L'association AppUserModelID + iconbitmap est la solution robuste.
        pass

        # Titre
        self.label_title = ctk.CTkLabel(self, text="SUIVI DATA 4G", font=("Roboto Medium", 16))
        self.label_title.grid(row=0, column=0, padx=20, pady=(20, 5))

        # Affichage principal (Usage)
        self.frame_usage = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_usage.grid(row=1, column=0, padx=20, pady=5)

        self.label_usage_val = ctk.CTkLabel(self.frame_usage, text="0.00 GB", font=("Roboto", 40, "bold"), text_color="#3B8ED0")
        self.label_usage_val.pack()
        
        self.label_usage_total = ctk.CTkLabel(self.frame_usage, text="/ 50 GB", font=("Roboto", 14), text_color="gray")
        self.label_usage_total.pack()

        # Vitesse
        self.label_speed = ctk.CTkLabel(self, text="Vitesse: 0.00 Mo/s", font=("Roboto", 12), text_color="#A0A0A0")
        self.label_speed.grid(row=2, column=0, padx=20, pady=0)

        # Barre de progression
        self.progressbar = ctk.CTkProgressBar(self, width=220, height=15)
        self.progressbar.grid(row=3, column=0, padx=20, pady=15)
        self.progressbar.set(0)

        # Infos détaillées
        self.frame_info = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_info.grid(row=4, column=0, padx=20, pady=10)
        
        self.label_remaining = ctk.CTkLabel(self.frame_info, text="Reste: -- GB", font=("Roboto", 12))
        self.label_remaining.pack()
        
        self.label_days = ctk.CTkLabel(self.frame_info, text="Reset dans: -- jours", font=("Roboto", 12))
        self.label_days.pack()
        
        # Switch TopMost
        self.switch_topmost = ctk.CTkSwitch(self, text="Toujours au-dessus", command=self.toggle_topmost)
        self.switch_topmost.grid(row=5, column=0, padx=20, pady=5)
        if self.topmost_enabled:
            self.switch_topmost.select()
        else:
            self.switch_topmost.deselect()

        # Bouton Paramètres
        self.btn_settings = ctk.CTkButton(self, text="Paramètres", command=self.open_settings, height=30)
        self.btn_settings.grid(row=6, column=0, padx=20, pady=(10, 5))

        # Bouton Donation
        self.btn_donate = ctk.CTkButton(self, text="Faire un don", command=self.open_donation, height=30, fg_color="#8E44AD", hover_color="#732d91")
        self.btn_donate.grid(row=7, column=0, padx=20, pady=(5, 20))

        # Lancer le thread de mise à jour
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Fix pour Window Manager / Restoration externe
        # Force le redessin et la taille quand la fenêtre est "Mappée"
        def on_restore(event):
            if event.widget == self:
                # On réimpose la taille fixe pour éviter le bug de la fenêtre minuscule
                self.geometry("300x530")
                self.minsize(300, 530)
                self.maxsize(300, 530) # On verrouille aussi le max
                self.update_idletasks()
                self.deiconify()
        
        self.bind("<Map>", on_restore)

    def open_donation(self):
        webbrowser.open("https://www.paypal.com/paypalme/creaprisme")
        
    def toggle_topmost(self):
        # Inverse l'état
        if self.switch_topmost.get() == 1:
            self.topmost_enabled = True
        else:
            self.topmost_enabled = False
        
        self.attributes('-topmost', self.topmost_enabled)
        
        # Sauvegarde de la préférence
        self.tracker.data["topmost_enabled"] = self.topmost_enabled
        self.tracker.save_data()

    def update_loop(self):
        # On initialise les compteurs pour le calcul de vitesse
        last_io = psutil.net_io_counters()
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            # Pour le total (DataTracker gère le cumul)
            total_bytes = self.tracker.get_current_usage()
            
            # Pour la vitesse (on regarde les compteurs bruts)
            current_io = psutil.net_io_counters()
            
            # Calcul débit
            time_diff = current_time - last_time
            if time_diff >= 1.0: # Mise à jour chaque seconde min pour stabilité
                # Calcul Download
                recv_diff = current_io.bytes_recv - last_io.bytes_recv
                speed_recv_bps = recv_diff / time_diff
                speed_recv_mbps = speed_recv_bps / (1024*1024) # Mo/s
                
                # Calcul Upload
                sent_diff = current_io.bytes_sent - last_io.bytes_sent
                speed_sent_bps = sent_diff / time_diff
                speed_sent_mbps = speed_sent_bps / (1024*1024) # Mo/s
                
                # Mise à jour références
                last_io = current_io
                last_time = current_time
                
                limit_gb = self.tracker.data["total_limit_gb"]
                limit_bytes = limit_gb * (1024**3)
                
                usage_gb = total_bytes / (1024**3)
                remaining_gb = limit_gb - usage_gb
                
                if limit_bytes > 0:
                    progress = total_bytes / limit_bytes
                else:
                    progress = 0
                if progress > 1: progress = 1
                
                # Jours restants
                now = time.localtime()
                reset_day = self.tracker.data["reset_day"]
                import calendar
                last_day_of_month = calendar.monthrange(now.tm_year, now.tm_mon)[1]
                
                if now.tm_mday < reset_day:
                    days_left = reset_day - now.tm_mday
                else:
                    days_left = (last_day_of_month - now.tm_mday) + reset_day

                self.after(0, lambda: self.update_ui(usage_gb, limit_gb, remaining_gb, progress, days_left, speed_recv_mbps, speed_sent_mbps))
                self.tracker.update_stored_usage()
            
            time.sleep(1)

    def update_ui(self, usage, limit, remaining, progress, days, speed_down, speed_up):
        self.label_usage_val.configure(text=f"{usage:.2f} GB")
        self.label_usage_total.configure(text=f"/ {limit:.0f} GB")
        self.label_remaining.configure(text=f"Reste: {remaining:.2f} GB")
        self.label_days.configure(text=f"Reset dans: {days} jours")
        
        # Affichage des deux vitesses
        self.label_speed.configure(text=f"↓ {speed_down:.2f} Mo/s   ↑ {speed_up:.2f} Mo/s")
        
        if progress > 0.9:
            self.progressbar.configure(progress_color="#C0392B")
        elif progress > 0.75:
             self.progressbar.configure(progress_color="#E67E22")
        else:
            self.progressbar.configure(progress_color="#3B8ED0")
            
        self.progressbar.set(progress)

    def get_startup_path(self):
        return os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', '4G_Monitor_Auto.vbs')

    def is_startup_enabled(self):
        return os.path.exists(self.get_startup_path())

    def toggle_startup(self):
        path = self.get_startup_path()
        if self.is_startup_enabled():
            try:
                os.remove(path)
                print("Démarrage auto désactivé")
            except Exception as e:
                print(f"Erreur suppression startup: {e}")
        else:
            try:
                # Créer un VBScript pour lancer le .pyw silencieusement
                script_dir = os.path.dirname(os.path.abspath(__file__))
                target_script = os.path.join(script_dir, "4G_Monitor.pyw")
                
                vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\n'
                vbs_content += f'WshShell.Run chr(34) & "{target_script}" & chr(34), 0\n'
                vbs_content += f'Set WshShell = Nothing'
                
                with open(path, "w") as f:
                    f.write(vbs_content)
                print("Démarrage auto activé")
            except Exception as e:
                print(f"Erreur activation startup: {e}")

    def open_settings(self):
        # On désactive temporairement le TopMost de la principale pour éviter les conflits
        self.attributes('-topmost', False)
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Réglages")
        dialog.geometry("300x500")
        
        # Fonction pour appliquer le dark mode à la barre de titre
        def apply_dark_title_bar(window):
            try:
                window.update()
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                get_parent = ctypes.windll.user32.GetParent
                hwnd = get_parent(window.winfo_id())
                rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
                value = 2 # 2 = Force Dark Mode
                value = ctypes.c_int(value)
                set_window_attribute(hwnd, rendering_policy, ctypes.byref(value), ctypes.sizeof(value))
            except:
                pass

        # On applique avec un léger délai pour laisser le temps à la fenêtre d'exister
        dialog.after(10, lambda: apply_dark_title_bar(dialog))
        
        # On force la fenêtre de réglage au premier plan
        dialog.attributes('-topmost', True)
        dialog.transient(self) # Lie la fenêtre à la principale
        dialog.grab_set() # Empêche d'interagir avec la principale tant que celle-ci est ouverte
        dialog.focus_force() # Donne le focus
        
        # Rétablir le TopMost à la fermeture (SI le switch est activé !)
        def on_dialog_close():
            # On ne remet le topmost que si l'utilisateur le veut (switch activé)
            if self.switch_topmost.get() == 1:
                self.attributes('-topmost', True)
            else:
                self.attributes('-topmost', False)
                
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        ctk.CTkLabel(dialog, text="Limite mensuelle (Go):").pack(pady=5)
        entry_limit = ctk.CTkEntry(dialog)
        entry_limit.insert(0, str(self.tracker.data["total_limit_gb"]))
        entry_limit.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Jour de remise à zéro (1-31):").pack(pady=5)
        entry_day = ctk.CTkEntry(dialog)
        entry_day.insert(0, str(self.tracker.data["reset_day"]))
        entry_day.pack(pady=5)
        
        # SÉLECTEUR D'INTERFACE RÉSEAU
        ctk.CTkLabel(dialog, text="Interface Réseau :").pack(pady=5)
        
        # Récupérer les noms des interfaces
        # On ajoute une option "Toutes" par défaut
        interfaces_list = ["Toutes (Global)"]
        try:
            stats = psutil.net_if_stats()
            # On peut filtrer celles qui sont "up" si on veut, mais mieux vaut toutes les montrer
            # pour éviter qu'une interface débranchée disparaisse de la config
            interfaces_list.extend(list(stats.keys()))
        except:
            pass
            
        combo_iface = ctk.CTkComboBox(dialog, values=interfaces_list, width=200)
        
        current_selection = self.tracker.data.get("selected_interface")
        if current_selection and current_selection in interfaces_list:
            combo_iface.set(current_selection)
        else:
            combo_iface.set("Toutes (Global)")
            
        combo_iface.pack(pady=5)
        
        # Checkbox Démarrage Auto
        self.check_var = ctk.BooleanVar(value=self.is_startup_enabled())
        check_startup = ctk.CTkCheckBox(dialog, text="Lancer au démarrage de Windows", 
                                        variable=self.check_var, command=self.toggle_startup)
        check_startup.pack(pady=15)

        ctk.CTkLabel(dialog, text="-----------------").pack(pady=5)
        ctk.CTkLabel(dialog, text="Correction manuelle (Si besoin):").pack(pady=5)
        entry_offset = ctk.CTkEntry(dialog, placeholder_text="Ex: 12.5")
        entry_offset.pack(pady=5)
        
        def save():
            try:
                lim = float(entry_limit.get())
                day = int(entry_day.get())
                off = None
                if entry_offset.get().strip():
                    off = float(entry_offset.get())
                
                # Gestion de l'interface
                selected = combo_iface.get()
                if selected == "Toutes (Global)":
                    selected = None
                
                self.tracker.set_config(lim, day, off, selected)
                on_dialog_close() # Utiliser la fermeture propre
            except ValueError:
                pass

        ctk.CTkButton(dialog, text="Sauvegarder", command=save).pack(pady=20)

    def on_closing(self):
        self.running = False
        self.tracker.update_stored_usage()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
