Title: In Mortem Resolume
Slug: in-mortem-resolume
Date: 2017-10-08 09:00
Tags: live show, mapping, resolume, osc, control, audio, video
Lang: fr
Abstract: Resolume, multi-projection, vidéo live et contrôle sur scène pour In Mortem
HeaderImage: ![]({attach}in-mortem-live.jpg)
Tweet: #Resolume, multi-projection, vidéo #live et interfaces #OSC pour @4rd3stop
Status: draft

# In Mortem

Le nouveau spectacle d'[Ardestop](https://www.facebook.com/ardestop/) *In Mortem* aborde le thème du transhumanisme sous la forme d'une conférence futuriste entre un immortel et une intelligence artificielle. Lors du spectacle, plusieurs scènes requièrent la diffusion de contenus de différentes natures:

- **Cyclo** les propos du conférencier sont illustrés par des projections de vidéos sur un cyclo en fond de scène. Sur cet écran sont également projetés des logos avant et après le spectacle.
- **Feed** un flux vidéo provenant d'une petite caméra type GoPro sur scène est parfois mélangé avec les médias d'illustration de conférence et projeté sur le cyclo
- **Scanner** un média simulant le passage du conférencier dans un scanner médical est parfois projeté sur le comédien depuis un second projecteur en bord de scène
- **Sons** les comédiens doivent synchroniser leur jeu sur des sons de durées différentes (effets sonores type coup de feu court, interventions pré-enregistrées de l'IA de quelques secondes, orchestrations de plusieurs minutes sur lesquelles les comédiens chantent)

![alt text]({attach}in-mortem-stage.jpg "Schéma de la scène")

Si le déclenchement des médias se fait en majorité depuis la régie, deux contraintes sont néanmoins à satisfaire:

1. la technicienne son étant assignée au lancement des medias, cette tâche doit être facilitée au maximum pour lui permettre de garder sa concentration sur sa fonction principale
2. certains effets (comme le scanner) doivent pouvoir être pilotés depuis les comédiens sur scène

La mise en œuvre technique du project est réalisée autour d'une composition [Resolume Avenue](Resolume Avenue) (serveur de média) pilotée *via* le protocole [OSC](https://fr.wikipedia.org/wiki/Open_Sound_Control) par des inferfaces simplifiées sur smartphones et laptops.

# La composition Resolume Avenue

La composition est organisée de la sorte:

1. la première colonne définie les deux sources indépendantes, pilotables depuis la scène (layer *Feed* pour le retour vidéo et le layer *Scanner*)
2. les autres colonnes sont des assemblages de sources à destination du cyclo
3. le layer *Cyclo* permet de séparer les layers à envoyer sur les projecteurs en assignant sur chacune de ses colonnes un clip *Layer Router* dont le paramètre *Input* est réglé sur *Layers Below*. Le layer *Cyclo* a son opacité vidéo réglée au maximum afin d'occulter complètement les layers qui le compose afin d'éviter des doubles affichages.
4. Le layer *SFX* est réservé aux sources audio. Il est exclu du déclenchement par colonnes. Les sons ne devant être joués qu'une fois et immédiatement à chaque déclenchement, ils sont configurés de la sorte:

    - *Transport: Timeline* pour un déclenchement immédiat
    - *Play Once* pour ne les jouer qu'une fois à chaque déclenchement
    - *Restart* pour jouer chaque son depuis le début à chaque déclenchement

![alt text]({attach}in-mortem-resolume.png "Composition Resolume")

Le routage des médias vers l'un des projecteurs se fait en assignant deux écrans dont le paramètre *Device* est assigné à un projecteur, chacun contenant une unique slice dont l'entrée est assignée à un layer (layer *Cyclo* ou layer *Scanner*).

![alt text]({attach}in-mortem-outputs.png "Sorties Resolume")


# Contrôles depuis la régie

Contrôler directement Resolume Avenue lors des représentations peut engendrer des erreurs de manipulation de par la relative complexité de son interface d'une part, et par la possibilité de dérégler certains paramètres d'autre part. Pour faciliter la tâche des techniciens en régie, Resolume Avenue est piloté par une interface réalisé avec [OSCWidgets](https://github.com/ETCLabs/OSCWidgets) *via* le protocole [OSC](https://fr.wikipedia.org/wiki/Open_Sound_Control).

L'interface est une grille de boutons. Chaque pression sur un des boutons envoie un message OSC à une instance de Resolume Avenue.

![alt text]({attach}in-mortem-osc-foh.png "Interface de contrôle régie")

- les assemblages pour le cyclo et les logos (les colonnes de la composition Resolume Avenue) sont lancés en connectant des `tracks`, par exemple `/track4/connect 1`
- les sons sont lancés en connectant des clips du layer *SFX*, par exemple `/layer6/clip1/connect 1`
- les sources indépendantes *Scanner* et *Feed* ont deux boutons: l'un pour afficher la source, l'autre pour l'éteindre. Dans le premier cas (affichage), le clip est connecté (`/layer6/clip1/connect 1` pour lancer le scanner par exemple). Dans le second cas (extinction), le layer est réinitialisé (`/layer5/clear 1`).

![alt text]({attach}in-mortem-resolume-osc.png "Mapping OSC de la composition Resolume")

Pendant les répétitions ou pour s'adapter au jeu des comédiens sur scène, deux boutons permettent de fondre au noir toutes les sources vidéos et de couper les sons.
- `/composition/disconnectall 1` permet de couper toutes les sources audio et vidéo
- `/layer6/clear 1`, en réinitialisant le layer *SFX*, coupe les sons

![alt text]({attach}in-mortem-oscwidgets.png "Configuration d'OSCWidgets")

# Contrôles depuis la scène

Pour permettre une meilleure interaction, les comédiens sur scène peuvent piloter le scanner et le retour vidéo depuis leur smartphone Android. L'interface est plus simple que pour la régie et se concentre uniquement sur les fonctions nécessaires sur scène afin d'éviter toute confusion de la part des comédiens:

- Scanner ON
- Scanner OFF
- Feed ON
- Feed OFF

![alt text]({attach}in-mortem-osc-stage.jpg "Interface de contrôle depuis la scène")

L'application utilisée est une version modifiée d'[AndrOSC](https://github.com/charlesfleche/AndrOSC), la version officielle disponible sur le store Google étant déficiente et non-maintenue. L'installation se fait donc manuellement en [téléchargeant](https://github.com/charlesfleche/AndrOSC/releases/tag/v0.9.2-inmortem) un .apk externe.
