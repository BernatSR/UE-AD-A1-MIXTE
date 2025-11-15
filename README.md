# UE-AD-A1-MIXTE

Pour la première partie ne vous souciez pas des fichiers Docker, cela sera abordé par la suite en séance 4.

pour chacun un README pour décrire l'architecture, l'organisation du projet, le déploiement, etc.
Schéma de base:

<img width="1386" height="1233" alt="image" src="https://github.com/user-attachments/assets/f8efd098-a484-4672-a245-f3491baef81f" />

Schéma après modification:




Sécurisation des points d'entrées avec la vérification du rôle de l'user comme dans le service booking, movie et user.
Cas de test Insomnia:


Note: le service user a été modifié pour passer de la vérificaion de l'admin via le header à une vérification par une route.


Organisation du projet:

Bernat a codé + testé le service movie et user et a également mise en place la dockerisation du TP. 
Johanne a codé + testé les autres services, fait la documentation globale.

Par exemple un point d’entrée dans Booking permettant de récupérer les réservations et le détail du film réservé (d’où les flèches de booking vers Movie).

Si vous avez besoin, vous pouvez ajouter des flèches entre les services.

fournir fichier de test insomnia

revoir docker-compose et un autre qui met à jour la liste des films programmés pour cette date




--------------------------------------------------------------------------------------------------------

Il ne s'agit pas d'un oral très formel, pas besoin de slides donc.
Vous allez uniquement me présenter votre TP MIXTE dockerisé et utilisant
MongoDB.

Déroulé de l'oral:
- 1 minute : me présenter votre architecture, un peu à l'image de la
figure de base que j'ai donnée pour le TP Mixte avec les interactions
entre services
- 4/5 minutes : démo à travers Insomnia (ou équivalent) avec un scénario
logique d'utilisation des API pour un utilisateur puis un administrateur
(vous ne pourrez pas tout montrer donc montrez moi les routes complexes
qui font appel à plusieurs services !)
- 5 minutes : questions et réponses dans le code (chaque membre du
groupe devra me décrire une route complexe que je choisirai utilisant
d'autres API)

A cette séance il faudra aussi me rendre les codes sur Moodle :
- 1 repo Git (ou une branche mais c'est moins pratique) pour REST et un
pour MIXTE
- pour chacun un README pour décrire l'architecture, l'organisation du
projet, le déploiement, etc.
- les deux versions sont dockerisées et utilisent MongoDB (si il y a un
moyen de choisir entre la version simple et la version Docker c'est
encore mieux)
