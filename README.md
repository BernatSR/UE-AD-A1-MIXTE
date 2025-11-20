# UE-AD-A1-MIXTE

Pour la première partie ne vous souciez pas des fichiers Docker, cela sera abordé par la suite en séance 4.

pour chacun un README pour décrire l'architecture, l'organisation du projet, le déploiement, etc.
Schéma de base:

<img width="1386" height="1233" alt="image" src="https://github.com/user-attachments/assets/f8efd098-a484-4672-a245-f3491baef81f" />

Schéma après modification:




Sécurisation des points d'entrées avec la vérification du rôle de l'user comme dans le service booking, movie et user.



Note: le service user a été modifié pour passer de la vérificaion de l'admin via le header à une vérification par une route.

## Commandes pour démarrer les services:

Powershell:
```bash
cd movie
python movie.py 
```

Démarrer le fichier de test test_schedule.py:
Nouveau Powershell

```bash
cd schedule
python test_schedule.py
```
## Lancement rapide avec Docker (JSON ou Mongo)

Mode fichiers JSON (pas de Mongo, utilise les .json locaux):
```bash
USE_MONGO=false docker compose up -d --build
```

Mode MongoDB (stockage dans Mongo, puis éventuellement import des JSON):
```bash
USE_MONGO=true docker compose up -d --build
```

Arrêt des services:
```bash
docker compose down
```

Variable `USE_MONGO` contrôle le backend (false = JSON, true = Mongo). Les fichiers JSON sont bind-mountés, donc toute modification locale est immédiatement visible en mode JSON.

## Cas de test:

Fichier insomnia pour tous les services sauf schedule qui a un fichier de test nommé test_schedule.py


-- Faire un scénario et choisir les routes à montrer

Organisation du projet:

Bernat a codé + testé le service movie et user et a également mise en place la dockerisation du TP. 
Johanne a codé + testé les autres services, fait la documentation globale.


