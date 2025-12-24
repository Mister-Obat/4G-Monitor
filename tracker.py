import psutil
import json
import time
from datetime import datetime, timedelta
import os

DATA_FILE = "data_usage.json"

class DataTracker:
    def __init__(self):
        self.data = self.load_data()
        self.session_start_io = psutil.net_io_counters()
        
    def load_data(self):
        """Charge les données depuis le fichier JSON ou crée une structure par défaut."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                pass # En cas d'erreur, on recrée par défaut
        
        # Structure par défaut
        return {
            "total_limit_gb": 50.0,      # Limite du forfait (ex: 50 Go)
            "reset_day": 1,              # Jour du mois pour la remise à zéro
            "current_cycle_usage": 0.0,  # Octets utilisés dans le cycle actuel (stocké)
            "last_save_time": time.time(),
            "offset_usage": 0.0,         # Usage manuel ajouté par l'utilisateur (en Go)
            "cycle_month": datetime.now().month # Pour détecter le changement de mois
        }

    def save_data(self):
        """Sauvegarde les données actuelles dans le fichier JSON."""
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def check_reset_date(self):
        """Vérifie si on a dépassé la date de facturation et remet à zéro si nécessaire."""
        now = datetime.now()
        current_day = now.day
        stored_month = self.data.get("cycle_month", now.month)
        reset_day = self.data["reset_day"]

        # Logique simplifiée : si nous sommes un nouveau mois ET que nous avons passé le jour de reset
        # Ou si le mois stocké est différent et qu'on est après le jour de reset
        
        # Si le mois actuel est différent du mois stocké
        if now.month != stored_month:
            # Si on est après ou le jour du reset, on reset
            if current_day >= reset_day:
                self.reset_cycle()
            # Si on est avant le jour du reset, on est encore dans le cycle du mois précédent (techniquement),
            # mais pour simplifier, on considère souvent que le cycle change au jour J.
            # Cas complexe : cycle du 15 au 15. Si on est le 2 du mois suivant, on n'a pas reset.
            # Si on est le 16 du mois suivant, on reset.
            
            # Mieux : On ne reset que si on franchit la date.
            # On va simplifier : L'utilisateur appuie sur "Reset" manuel ou on détecte le changement.
            pass
        
        # Pour l'instant, faisons confiance à la mise à jour manuelle ou au changement explicite
        # Amélioration : on stocke la date du "prochain reset".
        pass

    def reset_cycle(self):
        self.data["current_cycle_usage"] = 0.0
        self.data["offset_usage"] = 0.0
        self.data["cycle_month"] = datetime.now().month
        self.save_data()

    def get_current_usage(self):
        """Calcule l'utilisation totale (stockée + session actuelle). Retourne des octets."""
        
        # 1. Obtenir les compteurs système actuels
        current_io = psutil.net_io_counters()
        
        # 2. Calculer la différence depuis le lancement de l'app (Session)
        sent_diff = current_io.bytes_sent - self.session_start_io.bytes_sent
        recv_diff = current_io.bytes_recv - self.session_start_io.bytes_recv
        
        # Note : psutil compte depuis le démarrage du PC.
        # Si send_diff est négatif (redémarrage PC pendant que app tourne? peu probable), on ignore
        if sent_diff < 0: sent_diff = 0
        if recv_diff < 0: recv_diff = 0
        
        session_total = sent_diff + recv_diff
        
        # 3. Ajouter à l'historique stocké
        # L'astuce : on ne veut pas additionner indéfiniment la session.
        # On doit mettre à jour le stockage incrémentalement.
        # Mais pour faire simple : on retourne (Stocké + Session)
        # Et quand on ferme l'app, on ajoute Session à Stocké et on reset Session ?
        # Non, le plus robuste est :
        # Usage Total = (Offset Manuel en Go * 10^9) + Usage Enregistré + Session Actuelle
        
        offset_bytes = self.data.get("offset_usage", 0) * (1024**3)
        stored_bytes = self.data.get("current_cycle_usage", 0)
        
        return stored_bytes + session_total + offset_bytes

    def update_stored_usage(self):
        """Appelé périodiquement pour 'valider' la session dans le stockage permanent."""
        current_io = psutil.net_io_counters()
        
        sent_diff = current_io.bytes_sent - self.session_start_io.bytes_sent
        recv_diff = current_io.bytes_recv - self.session_start_io.bytes_recv
        
        if sent_diff < 0: sent_diff = 0
        if recv_diff < 0: recv_diff = 0
        
        session_total = sent_diff + recv_diff
        
        # On ajoute la session au total stocké
        self.data["current_cycle_usage"] += session_total
        
        # On réinitialise le point de référence de la session pour ne pas compter en double
        self.session_start_io = current_io
        
        self.save_data()

    def set_config(self, limit_gb, reset_day, current_offset_gb):
        self.data["total_limit_gb"] = float(limit_gb)
        self.data["reset_day"] = int(reset_day)
        # Si l'utilisateur définit manuellement l'usage actuel, on reset le compteur interne
        # et on utilise l'offset comme base.
        if current_offset_gb is not None:
            self.data["offset_usage"] = float(current_offset_gb)
            self.data["current_cycle_usage"] = 0.0 # On repart de l'offset
            # On doit aussi reset la session start pour ne pas ajouter ce qui vient de se passer
            self.session_start_io = psutil.net_io_counters()
            
        self.save_data()





