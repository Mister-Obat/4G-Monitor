# 4G Monitor

Une application simple en Python (CustomTkinter) pour surveiller la consommation de données (Data Usage) sur Windows. 

## Fonctionnalités

- **Suivi en temps réel** : Affiche la consommation totale et le débit instantané (Upload/Download).
- **Interface Moderne** : Basée sur `customtkinter` avec un thème sombre.
- **Persistance** : Sauvegarde la consommation dans un fichier `data_usage.json`.
- **Alertes visuelles** : La barre de progression change de couleur selon le pourcentage utilisé (Bleu > Orange > Rouge).
- **Mode Compact/Overlay** : Option "Toujours au-dessus" pour garder l'info visible.
- **Démarrage Auto** : Option pour lancer l'application au démarrage de Windows.
- **Réglages** : Configuration de la limite mensuelle et du jour de remise à zéro.

## Installation et Lancement

1. Assurez-vous d'avoir Python installé.
2. Installez les dépendances :
   ```bash
   pip install customtkinter psutil pillow
   ```
3. Lancez l'application :
   - via `4G_Monitor.pyw` (double-clic)
   - ou via `Debug.bat` pour voir les logs en cas de problème.

## Note Technique

L'application surveille l'utilisation **globale** de la bande passante de la machine via `psutil`. Elle est idéale pour les PC connectés uniquement via une connexion 4G/5G limités (partage de connexion, clé 4G, routeur 4G). Si vous utilisez plusieurs interfaces simultanément (Ethernet + Wifi), tout sera comptabilisé.
