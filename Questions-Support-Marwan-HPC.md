# Questions pour le support de Marwan (accès automatisé / HPC)

Contexte : connexion actuelle par mot de passe + 2FA. Objectif : automatiser la soumission et
le suivi de calculs (via une app web) sans ressaisir le mot de passe/2FA à chaque fois.

## Accès automatisé / contournement du 2FA

1. Existe-t-il un mécanisme d'accès par clé SSH (sans mot de passe ni 2FA) pour des usages
   d'automatisation (soumission de jobs par script/API), par exemple restreint à une adresse IP
   source fixe ?
2. Si oui, quelle est la procédure pour en faire la demande (formulaire, ticket, validation du
   responsable de labo) ?
3. Les outils de gestion de workflows de calcul comme AiiDA ou FireWorks sont-ils utilisés par
   d'autres équipes sur Marwan ? Si oui, comment gèrent-ils l'authentification automatique étant
   donné le 2FA ?
4. Existe-t-il une API REST ou un endpoint web pour soumettre des jobs Slurm sans passer par SSH
   interactif (certains centres HPC en proposent un) ?
5. Un compte de service dédié à l'automatisation (distinct de mon compte personnel) est-il
   possible ?

## Détails techniques nécessaires si l'accès par clé est accordé

6. Quel algorithme de clé est accepté (RSA, ed25519) et y a-t-il une longueur minimale imposée ?
7. L'accès par clé serait-il limité à une seule IP source, ou à une plage d'IPs ? (Important :
   je dois savoir si le serveur qui hébergera l'automatisation aura une IP fixe.)
8. Y a-t-il une limite sur le nombre de connexions SSH simultanées ou sur la fréquence de
   soumission de jobs qu'un script automatisé doit respecter ?

## Contexte de l'ordonnanceur (pour préparer les templates de jobs)

9. Confirmez-vous que l'ordonnanceur est bien Slurm ? Quelles sont les partitions/queues
   disponibles et leurs limites de temps de calcul (walltime) par défaut et maximum ?
10. Y a-t-il une limite de quota de stockage ou de nombre de jobs en attente simultanés à
    respecter dans un usage automatisé ?

## Portail web Marwan (mentionné dans une présentation de l'an dernier)

Contexte : présentation mentionnant un projet de portail web pour l'accès au cluster,
destiné à réduire le "time to first job" pour les utilisateurs peu à l'aise avec Linux/le
shell, avec en parallèle l'ajout de logiciels spécialisés.

11. S'agit-il d'une solution basée sur Open OnDemand, ou d'un développement interne ?
12. Où en est ce projet aujourd'hui (statut, calendrier de déploiement) ?
13. Ce portail exposera-t-il une API programmatique (au-delà de l'interface web interactive)
    permettant à une application tierce de soumettre/suivre des jobs automatiquement ?
14. L'authentification sur ce portail contournera-t-elle le 2FA pour un usage automatisé, ou
    reproduira-t-elle le même mécanisme de login que l'accès SSH actuel ?
15. Les logiciels spécialisés mentionnés incluront-ils Quantum ESPRESSO et les outils de
    post-traitement associés ?
16. Serait-il envisageable d'intégrer une application externe développée pour des workflows
    spécifiques (génération d'inputs, post-traitement de résultats DFT) avec ce futur portail,
    plutôt que de dupliquer l'effort avec un accès SSH direct ?
