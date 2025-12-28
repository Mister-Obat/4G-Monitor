import psutil
import json
import time
from datetime import datetime
import os

DATA_FILE = "data_usage.json"

class DataTracker:
    def __init__(self):
        self.data = self.load_data()
        self.session_start_io = self.get_io_counters()
        # Track if we were previously monitoring a valid interface
        self.last_interface_valid = self.is_interface_valid()
        
    def load_data(self):
        """Charge les données depuis le fichier JSON ou crée une structure par défaut."""
        default_data = {
            "total_limit_gb": 50.0,
            "reset_day": 1,
            "current_cycle_usage": 0.0,
            "last_save_time": time.time(),
            "offset_usage": 0.0,
            "cycle_month": datetime.now().month,
            "selected_interface": None # None = Global (Legacy behavior)
        }

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    loaded = json.load(f)
                    for k, v in default_data.items():
                        if k not in loaded:
                            loaded[k] = v
                    return loaded
            except:
                pass 
        
        return default_data

    def save_data(self):
        """Sauvegarde les données actuelles dans le fichier JSON."""
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)
            
    def is_interface_valid(self):
        """Vérifie si l'interface sélectionnée existe et est active."""
        iface = self.data.get("selected_interface")
        if not iface: return True # Global is always "valid"
        
        # On vérifie si elle est dans la liste des stats
        stats = psutil.net_if_stats()
        return iface in stats

    def get_io_counters(self):
        """Retourne les compteurs IO pour l'interface sélectionnée ou globale."""
        iface = self.data.get("selected_interface")
        if iface:
            counters = psutil.net_io_counters(pernic=True)
            if iface in counters:
                return counters[iface]
            else:
                # Interface débranchée/inexistante
                class ZeroIO:
                    bytes_sent = 0
                    bytes_recv = 0
                return ZeroIO()
        else:
            return psutil.net_io_counters()

    def _calculate_session_diff(self, current_io):
        """Calcule safely la différence entre session_start et current."""
        
        # DÉTECTION DE SAUT D'INTERFACE (BUG FIX)
        # Si on passe de "Interface Invalide" (ZeroIO) à "Valide" (Grosses valeurs),
        # alors current >> session_start (qui était 0).
        # Cela créerait un faux usage énorme.
        
        is_valid_now = self.is_interface_valid()
        
        # Si l'interface vient d'apparaitre (était invalide, est maintenant valide)
        if is_valid_now and not self.last_interface_valid:
            # ON RESET LE START pour éviter le saut
            self.session_start_io = current_io
            self.last_interface_valid = True
            return 0 # Pas de diff pour cette itération
            
        self.last_interface_valid = is_valid_now
        
        # Si l'interface est invalide, on ne compte rien
        if not is_valid_now:
            return 0

        sent_current = getattr(current_io, 'bytes_sent', 0)
        recv_current = getattr(current_io, 'bytes_recv', 0)
        
        sent_start = getattr(self.session_start_io, 'bytes_sent', 0)
        recv_start = getattr(self.session_start_io, 'bytes_recv', 0)

        sent_diff = sent_current - sent_start
        recv_diff = recv_current - recv_start
        
        # Protection contre redémarrage compteur système (si PC reboot sans que app quit, rare mais possible)
        if sent_diff < 0: sent_diff = 0
        if recv_diff < 0: recv_diff = 0
        
        return sent_diff + recv_diff

    def get_current_usage(self):
        """Calcule l'utilisation totale (stockée + session actuelle). Retourne des octets."""
        current_io = self.get_io_counters()
        session_total = self._calculate_session_diff(current_io)
        
        offset_bytes = self.data.get("offset_usage", 0) * (1024**3)
        stored_bytes = self.data.get("current_cycle_usage", 0)
        
        return stored_bytes + session_total + offset_bytes

    def update_stored_usage(self):
        """Valide la session dans le stockage permanent."""
        current_io = self.get_io_counters()
        session_total = self._calculate_session_diff(current_io)
        
        # Ajout au stock
        self.data["current_cycle_usage"] += session_total
        
        # Reset session
        self.session_start_io = current_io
        self.save_data()

    def set_config(self, limit_gb, reset_day, current_offset_gb, selected_interface=None):
        """Met à jour la config et gère le changement d'interface."""
        
        # 1. Sauvegarder l'usage courant sur l'ancienne config
        self.update_stored_usage()
        
        self.data["total_limit_gb"] = float(limit_gb)
        self.data["reset_day"] = int(reset_day)
        
        # Changement d'interface ?
        old_iface = self.data.get("selected_interface")
        if selected_interface != old_iface:
             self.data["selected_interface"] = selected_interface
             self.session_start_io = self.get_io_counters()
             self.last_interface_valid = self.is_interface_valid()

        # CORRECTION MANUELLE : DOIT ÉCRASER TOUT HISTORIQUE
        if current_offset_gb is not None:
            self.data["offset_usage"] = float(current_offset_gb)
            self.data["current_cycle_usage"] = 0.0 # Suppression totale de l'historique accumulé
            
            # Reset session start pour repartir de zéro à partir de cet instant
            self.session_start_io = self.get_io_counters()
            self.last_interface_valid = self.is_interface_valid()
            
        self.save_data()





