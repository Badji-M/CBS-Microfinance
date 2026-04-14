# 📋 Présentation Détaillée de la Plateforme de Microfinance

## **INTRODUCTION**

Bonjour à tous et bienvenue. Je vais vous présenter aujourd'hui **la Plateforme de Microfinance**, une solution digitale complète et innovante destinée à la gestion et au suivi des portefeuilles de crédit dans le secteur de la microfinance.

Cette plateforme a été conçue pour résoudre un problème majeur dans les institutions de microfinance : la gestion inefficace des données clients, le suivi complexe des prêts, et surtout, l'incapacité à identifier rapidement les clients à risque. Avec notre solution, vous avez une visibilité complète sur votre activité, en temps réel.

Notre plateforme offre trois principales valeurs ajoutées :
1. **Une gestion centralisée** de tous les clients et tous les prêts
2. **Un scoring intelligent** basé sur l'intelligence artificielle pour évaluer le risque de crédit
3. **Un suivi détaillé** de chaque remboursement et de chaque échéance

---

## **INFRASTRUCTURE TECHNIQUE : DOCKER ET LES SERVICES**

Avant de plonger dans les fonctionnalités métier, parlons un moment de la plomberie technique. Car vous vous demandez peut-être : comment cette plateforme fonctionne-t-elle réellement ? Quels sont les éléments qui la font tourner ?

### **Qu'est-ce que Docker ?**

Docker est une technologie de **conteneurisation**. Pensez à Docker comme un ensemble de boîtes hermétiques. Chaque boîte contient tout ce qui est nécessaire pour faire fonctionner une application : le code, les bibliothèques, les dépendances.

Pourquoi c'est important ? Parce que cela signifie que :
- ✅ L'application fonctionne exactement pareil sur votre ordinateur, sur celui de votre collègue, ou sur un serveur dans le cloud.
- ✅ Il n'y a pas de problèmes du type "ça marche chez moi mais pas chez vous".
- ✅ Vous pouvez facilement déployer, mettre à jour, ou redémarrer l'application.

### **Les 5 Services qui Font Tourner la Plateforme**

Notre plateforme est composée de **5 services Docker** qui travaillent ensemble en harmonie. Voici chacun d'eux :

#### **1. Service Web (Django + Gunicorn)**

**Rôle** : C'est le cœur de l'application. C'est ici que se trouve tout le code métier.

**Technologie** :
- **Django 4.2.7** : C'est un framework web Python très populaire pour construire des applications web robustes.
- **Gunicorn 21.2.0** : C'est un serveur d'application qui exécute le code Django et le rend accessible via HTTP.

**Qu'est-ce qui se passe ici ?**
- Quand vous cliquez sur un bouton dans l'interface, la requête arrive à ce service.
- Le service web traite la demande : "Ok, tu veux voir la liste des clients ? Je vais chercher les données dans la base de données."
- Il retourne le résultat en HTML/JSON à votre navigateur.
- C'est également ici que se trouve le modèle de scoring ML qui évalue les clients.

**Ressources** : 
- Port 8000 (Communication interne avec Nginx)

---

#### **2. Base de Données (PostgreSQL 15-Alpine)**

**Rôle** : C'est le cœur de la mémoire. Toutes les données sont stockées ici.

**Technologie** :
- **PostgreSQL 15** : Une base de données relationnelle très puissante et fiable.
- **Alpine** : Une version légère du système d'exploitation Linux (20x plus petit qu'une version standard).

**Qu'est-ce qui se passe ici ?**
- Tous les clients sont stockés ici : nom, revenu, emploi, etc.
- Tous les prêts sont stockés : montant, durée, taux, statut.
- Toutes les échéances sont stockés : dates de paiement, montants.
- Toutes les transactions et les paiements sont enregistrées.

**Robustesse** :
Si le service web crashe, la base de données continue de tourner et vos données sont sauvegardées. Si le service web redémarre, les données sont toujours là, intactes.

**Ressources** :
- Port 5432 (Communication interne uniquement)
- Stockage persistant : même si le conteneur s'arrête, les données restent sur le disque.

---

#### **3. Cache en Mémoire (Redis 7-Alpine)**

**Rôle** : C'est un super-accélérateur. Redis stocke les données fréquemment accédées en mémoire pour des réponses ultra-rapides.

**Technologie** :
- **Redis 7** : Une base de données "en mémoire" extrêmement rapide.

**Qu'est-ce qui se passe ici ?**
- Quand vous consultez la liste des clients pour la 10e fois dans la journée, Redis dit : "J'ai déjà cette liste ! Je vais te la donner instantanément au lieu de chercher dans la base de données."
- Cela rend la plateforme beaucoup plus rapide.
- Redis stocke aussi les sessions utilisateur (pour que vous restiez connecté).

**Performance** :
Redis est environ 100x plus rapide que PostgreSQL pour les petites données. C'est pourquoi nous l'utilisons pour les données très consultées.

**Ressources** :
- Port 6379 (Communication interne uniquement)

---

#### **4. Queue de Tâches Asynchrones (Celery + Redis)**

**Rôle** : C'est le travailleur de nuit. Celery exécute les tâches longues sans bloquer l'interface.

**Technologie** :
- **Celery** : Un framework Python pour exécuter des tâches asynchrones.
- **Redis** : Utilisé comme "broker de messages" pour communiquer les tâches.

**Qu'est-ce qui se passe ici ?**

Imaginez un scénario : un client clique sur "Télécharger mon rapport de crédit en PDF". Si cela prenait 30 secondes à générer (extraction des données, création du PDF, etc.), l'interface serait figée pendant 30 secondes. C'est un mauvaise expérience utilisateur.

Avec Celery :
1. L'utilisateur clique sur "Télécharger".
2. Django dit : "Ok, je vais demander à Celery de faire ça. Et je vais te dire que c'est en cours."
3. Django revient immédiatement avec une réponse : "Votre PDF est en cours de génération, vous recevrez une notification quand c'est prêt."
4. Celery, en arrière-plan, génère le PDF sans déranger l'utilisateur.

**Tâches gérées par Celery** :
- Génération de rapports PDF
- Envoi d'alertes par email ou SMS
- Calculs lourds de statistiques
- Nettoyage automatique des anciennes données

**Ressources** :
- Utilise Redis comme système de communication
- Peut être parallélisé : plusieurs Celery peuvent tourner en même temps pour plus de performance

---

#### **5. Serveur Web Inverse (Nginx)**

**Rôle** : C'est le portier de l'immeuble. Nginx dirige le trafic internet vers les bons services.

**Technologie** :
- **Nginx** : Un serveur web léger et ultra-rapide.

**Qu'est-ce qui se passe ici ?**
- Quand quelqu'un accède à `http://localhost:8000`, c'est Nginx qui reçoit d'abord la requête.
- Nginx dit : "Cette requête est pour une page web ? Je vais la passer au service Django (port 8000)."
- Nginx retourne la réponse au client.

**Avantages de Nginx** :
- **Reverse Proxy** : Il peut équilibrer la charge si vous avez plusieurs services Django.
- **Compression** : Il compresse les données envoyées au client pour économiser la bande passante.
- **SSL/TLS** : Si vous aviez un certificat HTTPS, Nginx le gèrerait.
- **Caching** : Il peut mettre en cache certaines réponses pour les servir encore plus vite.

**Ressources** :
- Port 80 (HTTP)
- Port 443 (HTTPS, si configuré)

---

### **Comment Ces Services Communiquent Entre Eux ?**

Imaginez une symphonie orchestrale. Chaque instrument (service) doit jouer au bon moment et écouter les autres.

```
┌─────────────────────────────────────────────────────────┐
│                  VOTRE NAVIGATEUR                        │
└────────────────────┬────────────────────────────────────┘
                     │ http://localhost
                     ↓
┌─────────────────────────────────────────────────────────┐
│         NGINX (Reverse Proxy)                            │
│         • Reçoit les requêtes HTTP                       │
│         • Dirige vers Django                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│    DJANGO/GUNICORN (Service Web)                         │
│    • Traite la logique métier                            │
│    • Demande des données à PostgreSQL                    │
│    • Envoie des tâches à Celery                          │
└──┬──────────────────┬──────────────────┬────────────────┘
   │                  │                  │
   ↓                  ↓                  ↓
┌──────────┐    ┌──────────┐    ┌──────────┐
│PostgreSQL│    │  Redis   │    │ Celery   │
│          │    │          │    │          │
│ • Clients│    │• Cache   │    │• Rapports│
│ • Prêts  │    │• Sessions│    │• Alertes │
│ • Données│    │• Queue   │    │• Calculs │
└──────────┘    └──────────┘    └──────────┘
```

**Exemple d'une requête complète** :

1. **Requête initiale** : Vous cliquez sur "Voir les clients"
   - Requête HTTP envoyée à Nginx
   
2. **Nginx reçoit** : Il dit "C'est une requête web, je la passe à Django"
   - Django reçoit la demande
   
3. **Django traite** : Il dit "Ok, il faut que je récupère la liste des clients"
   - Django demande à Redis : "As-tu déjà la liste en cache ?"
   - Redis : "Oui, la voilà !"
   - Django formatte les données et les renvoie à Nginx
   
4. **Nginx retourne** : La liste des clients s'affiche dans votre navigateur
   - Tout cela en moins de 200 millisecondes !

**Si Redis n'avait pas la liste en cache** :
   - Django demande à PostgreSQL : "Donne-moi tous les clients"
   - PostgreSQL extrait les données, les retourne
   - Django met à jour le cache Redis
   - Prochaine fois, ce sera plus rapide

---

### **Avantages de Cette Architecture Multi-Services**

**Scalabilité** : 
Si vous avez trop de requêtes, vous pouvez ajouter un deuxième service Django. Nginx équilibrera la charge entre les deux.

**Fiabilité** :
Si un service tombe, les autres continuent. Si Django crash, vos données dans PostgreSQL sont sûres.

**Maintenabilité** :
Chaque service a une responsabilité unique. C'est facile de comprendre et de modifier.

**Performance** :
Chaque service est optimisé pour son rôle. Redis pour la vitesse, PostgreSQL pour la fiabilité, Celery pour les tâches longues.

---

### **Déploiement et Mise à Jour**

**Avant Docker** : 
"Je dois installer Python, PostgreSQL, Redis, Nginx sur le serveur... et si les versions ne sont pas compatibles? Et si un collègue utilise une version différente?"

**Avec Docker** :
```bash
docker-compose up
```

Boom ! Tous les services démarrent avec les bonnes versions, prêts à fonctionner.

**Mise à jour** :
Pour passer à une nouvelle version, vous mettez simplement à jour les versions dans le fichier `docker-compose.yml`, et c'est tout.

---

## **SECTION 1 : LE TABLEAU DE BORD**

Et bien, commençons par le cœur de la plateforme : **le Tableau de Bord**.

Le tableau de bord est votre centre de commande. C'est le premier écran que vous voyez quand vous vous connectez. Il vous donne une photographie instantanée de la santé de votre portefeuille de crédit.

### **Les KPI - Indicateurs Clés de Performance**

En haut du tableau de bord, vous avez quatre cartes avec les KPIs, c'est-à-dire les **Indicateurs Clés de Performance**. Voici ce que vous y voyez :

#### **1. Montant Total Décaissé**
C'est la somme totale de tous les crédits que vous avez accordés à vos clients. Par exemple, si vous avez accordé 10 prêts de 500 000 FCFA chacun, le montant total décaissé est 5 millions de FCFA. Cet indicateur vous montre l'ampleur de votre activité de crédit.

#### **2. Nombre de Prêts Actifs**
C'est simple : combien de prêts sont actuellement en cours de remboursement ? Si vous avez 50 clients qui remboursent actuellement, vous avez 50 prêts actifs. C'est important pour comprendre votre volume d'activité.

#### **3. Taux d'Arriéré (PAR 30)**
C'est l'un des indicateurs les plus importants en microfinance. Et je vais vous expliquer pourquoi.

Le **PAR 30** signifie "Portfolio At Risk" supérieur à 30 jours. En clair : c'est le montant total des crédits dont les clients ont un retard de paiement de plus de 30 jours. 

Imaginez : vous avez accordé 100 millions FCFA de crédits. Mais 5 millions n'ont pas été remboursés, et le client a 45 jours de retard. Ce client est comptabilisé dans votre PAR 30. 

Ce ratio est crucial parce qu'il vous indique la qualité de votre portefeuille. Plus le PAR 30 est bas, plus votre portefeuille est sain. Un PAR 30 supérieur à 5% est généralement considéré comme inquiétant pour une institution de microfinance.

#### **4. Taux de Renouvellement**
C'est un indicateur de fidélité. Le taux de renouvellement montre quel pourcentage de vos clients qui ont terminé un prêt en prennent un nouveau. 

Par exemple : vous aviez 10 clients dont les prêts étaient terminés le mois dernier. Et voilà, 7 d'entre eux ont déjà demandé un nouveau crédit. Votre taux de renouvellement est de 70%. C'est un excellent signe d'une relation de confiance avec vos clients.

### **Les Graphiques Analytiques**

Maintenant, vous avez quatre graphiques qui vous donnent une analyse plus profonde :

#### **Graphique 1 : Montants Décaissés par Mois**
C'est un graphique en barres qui montre votre activité de crédit sur les 12 derniers mois. Vous pouvez voir les tendances : est-ce que vous accordez plus de crédits ? Moins ? C'est important pour la planification.

#### **Graphique 2 : Répartition des Statuts de Prêts**
C'est un graphique en camembert qui vous montre : combien de prêts sont "en cours" ? Combien sont "remboursés" ? Combien sont "en défaut" ? C'est une vue d'ensemble de la santé du portefeuille.

#### **Graphique 3 : L'Indicateur PAR 30 - Visualisé en Jauge**
Le PAR 30 n'est pas juste un nombre. Il est visualisé avec une jauge de couleur. Si le PAR 30 est inférieur à 5%, la jauge est verte – c'est bon. Entre 5% et 10%, elle est orange – attention. Au-delà de 10%, elle est rouge – alerte maximale. Cela vous permet de voir d'un coup d'œil l'état de votre portefeuille.

#### **Graphique 4 : Le Taux de Renouvellement sur 12 Mois**
C'est un graphique en courbe qui montre l'évolution du taux de renouvellement mois après mois. Cela vous aide à identifier les tendances : est-ce que vos clients reviennent emprunter ? Ou estiment-ils que votre taux d'intérêt est trop élevé ?

---

## **SECTION 2 : LA GESTION DES CLIENTS**

Maintenant, parlons des clients. C'est la base de tout. Pas de clients, pas de prêts.

### **Qui sont vos Clients ?**

Dans l'onglet "Clients", vous avez la liste complète de tous les clients de votre institution. Chaque client a un profil détaillé avec les informations essentielles :

- **Nom complet** et **ville de résidence** : Cela vous permet de localiser vos clients et de comprendre votre couverture géographique.

- **Type d'emploi** : Est-ce un commerçant ? Un agriculteur ? Un employé ? C'est important pour évaluer la stabilité des revenus.

- **Revenu mensuel** : C'est le revenu déclaré par le client. Attention : en microfinance, beaucoup de clients ont des revenus irréguliers. Un commerçant peut gagner 200 000 FCFA un mois et 50 000 FCFA le mois suivant.

- **Situation familiale** : Nombre de personnes à charge, état matrimonial. C'est important pour comprendre les obligations financières du client.

- **Compte bancaire** : Est-ce que le client a un compte bancaire ? Cela indique un certain niveau de bancarisation et donc une traçabilité financière.

### **Crédit Score**

Chaque client a un **Credit Score**. Ce score est calculé par notre intelligence artificielle basée sur deux modèles de machine learning :

#### **1. Le Random Forest**
C'est un algorithme qui utilise 100 arbres de décision pour évaluer le risque. Imaginez : chaque arbre pose des questions différentes au sujet du client. 

- "Est-ce qu'il a un emploi stable ?" 
- "Est-ce qu'il a remboursé ses dettes précédentes ?" 
- "Son ratio dette/revenu est-il acceptable ?" 

En combinant toutes ces réponses, nous obtenons un score robuste et fiable.

#### **2. La Régression Logistique**
C'est un modèle plus simple mais puissant qui estime la probabilité que le client rembourse ou ne rembourse pas. Elle utilise des variables statistiques pour évaluer le risque.

**Le score final** varie de 0 à 100. 
- Un score de 80-100 signifie que le client a une très faible probabilité de défaut.
- Un score de 40-80 signifie un risque modéré.
- Un score de 0-40 signifie un risque très élevé.

---

## **SECTION 3 : LA GESTION DES PRÊTS**

L'onglet "Prêts" est où le vrai travail opérationnel se fait.

### **Les Produits de Crédit**

D'abord, vous avez plusieurs produits de crédit. Imaginons que vous proposez quatre produits différents :

#### **1. Crédit Consommation**
- **Montant** : entre 50 000 et 500 000 FCFA
- **Durée** : 6 à 24 mois
- **Taux d'intérêt** : 24% par an
- **Frais de dossier** : 3%

Ce produit est destiné aux clients qui ont besoin de liquide pour des dépenses courantes.

#### **2. Crédit Productif Petit Commerce**
- **Montant** : entre 200 000 et 2 millions FCFA
- **Durée** : 12 à 36 mois
- **Taux d'intérêt** : 18% par an
- **Frais de dossier** : 2%

Ce produit est pour les petits commerçants qui veulent augmenter leur stock ou investir dans leur activité.

#### **3. Crédit Agricole**
- **Montant** : entre 100 000 et 5 millions FCFA
- **Durée** : 6 à 24 mois
- **Taux d'intérêt** : 15% par an
- **Frais de dossier** : 1.5%

Ce produit est pour les agriculteurs, avec un taux plus bas parce que le secteur agricole est souvent subventionné.

#### **4. Crédit Immobilier/Amélioration d'Habitat**
- **Montant** : entre 500 000 et 10 millions FCFA
- **Durée** : 24 à 60 mois
- **Taux d'intérêt** : 12% par an
- **Frais de dossier** : 2%

Ce produit est pour ceux qui veulent améliorer leur habitation.

### **Mécanisme d'Amortissement**

Maintenant, parlons d'un terme technique important : **l'amortissement**. 

L'amortissement est la façon dont les remboursements du prêt sont structurés. Il existe deux types principaux :

#### **Type 1 : Amortissement Linéaire (ou Amortissement Constant)**

Imaginez qu'un client emprunte 600 000 FCFA sur 12 mois. Avec l'amortissement linéaire, il rembourse chaque mois :
- Une portion du capital : 600 000 ÷ 12 = 50 000 FCFA
- Les intérêts du mois

Donc si le taux annuel est 24%, les intérêts du premier mois seraient : 
```
(600 000 × 24%) ÷ 12 = 12 000 FCFA
```

Le premier paiement est : 50 000 + 12 000 = **62 000 FCFA**.

Le deuxième mois, le capital restant est 550 000, donc l'intérêt est : 
```
(550 000 × 24%) ÷ 12 = 11 000 FCFA
```

Le deuxième paiement est : 50 000 + 11 000 = **61 000 FCFA**.

Vous remarquez ? Chaque mois, le paiement diminue légèrement. C'est prévisible et facile à comprendre pour le client.

#### **Type 2 : Amortissement Dégressif (ou Paiements Égaux)**

Ici, le client paie le même montant chaque mois. Mais la structure interne change. Les premiers paiements sont surtout des intérêts, et progressivement, le capital augmente.

Pour 600 000 FCFA sur 12 mois à 24% annuel, le paiement mensuel serait environ **54 000 FCFA** chaque mois.

- **Au début** : beaucoup d'intérêt, peu de capital.
- **À la fin** : moins d'intérêt, plus de capital.

**Quel amortissement choisir ?** Cela dépend de la politique de votre institution et de la capacité de remboursement du client.

### **Le Processus d'Accord d'un Prêt**

Quand un client demande un prêt, voici le processus :

1. **Demande et Évaluation du Score** : Le client remplit un formulaire. Notre système calcule automatiquement son score de crédit.

2. **Évaluation Manuelle** : Un agent examine le dossier. Est-ce que le score de crédit et les autres critères justifient l'approbation ?

3. **Approbation ou Rejet** : Si approuvé, le prêt est accepté. Si rejeté, le client est informé.

4. **Décaissement** : L'argent est transféré au compte du client (ou parfois un chèque est remis).

5. **Suivi des Remboursements** : Le client commence à rembourser selon l'échéancier.

---

## **SECTION 4 : L'ÉCHÉANCIER ET LE SUIVI DES REMBOURSEMENTS**

Maintenant, parlons de l'échéancier. C'est le cœur battant de la relation entre vous et vos clients.

### **Qu'est-ce qu'un Échéancier ?**

Un échéancier est un tableau qui affiche toutes les dates et tous les montants que le client doit rembourser. Par exemple, pour un crédit de 600 000 FCFA sur 12 mois en amortissement linéaire à 24%, l'échéancier ressemblerait à ceci :

| Mois | Capital | Intérêt | Paiement Total | Capital Restant |
|------|---------|---------|----------------|-----------------|
| 1    | 50 000  | 12 000  | 62 000         | 550 000         |
| 2    | 50 000  | 11 000  | 61 000         | 500 000         |
| 3    | 50 000  | 10 000  | 60 000         | 450 000         |
| ...  | ...     | ...     | ...            | ...             |
| 12   | 50 000  | 1 000   | 51 000         | 0               |

Chaque ligne est une **échéance**, c'est-à-dire une obligation de paiement à une date donnée.

### **Suivi des Paiements**

Dans l'onglet "Échéancier", vous voyez toutes les échéances de tous vos clients. Chaque échéance a un statut :

- **Payée** : Le client a payé le montant requis.
- **En Cours** : C'est l'échéance du mois actuel, pas encore payée mais pas en retard.
- **En Retard** : Le client aurait dû payer mais ne l'a pas fait.

Vous pouvez voir :
- Combien de jours de retard ?
- Quel est le montant en retard ?
- Quel est le montant total restant à payer ?

### **Gestion des Retards**

Les retards de paiement peuvent arriver. Un client peut avoir eu un imprévu. Comment gérez-vous cela ?

#### **Jours de Retard**
- **0-7 jours** : Petit retard. Un rappel suffit souvent.
- **8-30 jours** : Retard modéré. Intervention requise.
- **31-60 jours** : Retard sérieux. Contact direct avec le client.
- **61+ jours** : Retard critique. Évaluation pour restructuration du prêt ou actions en recouvrement.

#### **Actions Possibles**
- **Remboursement Partiel** : Le client paie une partie du montant dû.
- **Restructuration** : Vous accordez plus de temps au client, généralement en augmentant légèrement les intérêts.
- **Recouvrement** : En dernier recours, vous devez recouvrer la dette par des voies légales.

### **Reporting sur les Paiements**

Chaque mois, vous pouvez générer un rapport sur les paiements :
- Combien d'échéances ont été payées ?
- Combien sont en retard ?
- Quel est le montant total recouvré ?
- Quel est le taux de remboursement ?

**Un bon taux de remboursement** pour une institution de microfinance est au-dessus de 95%. Moins que cela, et votre modèle économique est en danger.

---

## **CONCLUSION**

Voilà, vous avez maintenant une compréhension complète de notre plateforme.

- Le **Tableau de Bord** vous donne une vue d'ensemble stratégique.
- La gestion des **Clients** vous permet de connaître votre base clients et d'évaluer leur risque.
- La gestion des **Prêts** vous permet de structurer votre offre de crédit et de suivre chaque prêt.
- L'**Échéancier** vous permet de manager les remboursements et d'intervenir avant que des problèmes sérieux ne surviennent.

### **Avec cette plateforme, vous avez les outils pour :**

✅ **Prendre des décisions basées sur les données**  
✅ **Identifier rapidement les clients à risque**  
✅ **Optimiser votre portefeuille de crédit**  
✅ **Augmenter vos taux de remboursement**  
✅ **Croître de manière saine et durable**  

---

**Merci de votre attention. Je suis maintenant disponible pour répondre à vos questions.**

---

*Document généré automatiquement • Plateforme de Microfinance • Mars 2026*
