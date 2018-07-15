Title: La place du libre dans les effets spéciaux
Slug: place-libre-vfx
Date: 2018-07-18 17:03
Tags: vfx, free software, open source
Lang: fr
Abstract: Précisions sur la place des logiciels libres dans les studios d'effets spéciaux suite à un journal de LinuxFr.org
Tweet: La place des #LogicielsLibres dans les studios d'effets spéciaux #LinuxFr #VFX #Blender #OSS

*Cet article a d'abord été publié sur LinuxFR.org en commentaire au journal [Le libre intéresse un studio d'animation français](https://linuxfr.org/users/rewind/journaux/le-libre-interesse-un-studio-d-animation-francais#comment-1744075).*

# Du libre pour le système…

Pour un studio d'animation ou d'effets spéciaux le coût des licences est un véritable problème qui amène à choisir du libre, mais il y a d'excellentes raisons pour choisir du propriétaire acheté ou développé en interne.

Tous les gros studios ([ILM](https://www.ilm.com/), [MPC](https://moving-picture.com/), [Mikros](http://www.mikrosimage.com/) je crois, [The Mill](http://www.themill.com/) où j'ai bossé, [BUF](https://buf.com/)) tournent sous Linux, stations de travail et fermes de rendu, pour au moins trois raisons:

- pas de licence à payer pour les OS (et il y a facilement des centaines de racks sur les renderfarms)
- la pile réseau a toujours bien marché pour cet usage, pourquoi changer ?
- l'héritage et les habitudes des stations Unix / Irix des pionniers des années 90

Seule exception: les artistes pour les textures ont souvent un Mac avec Photoshop pas loin et les quelques monteurs aussi.

# …et beaucoup d'applications propriétaires

En revanche les applications sont presque exclusivement propriétaires. Et d'ailleurs, ce n'est pas 3 ou 4 softs comme dit l'un des commentaires, mais une myriade d'outils qui sont utilisés pour des raisons différentes. Pour une production un peu complexe, il y aura facilement:

- Shotgun pour la gestion de projet (mais il y a aussi FTrack)
- RV pour visualiser les rendus (il y en a d'autres)
- Maya pour le modelling, texturing et animation des personnages (mais suivant les régions du monde et l'industrie, il y a aussi 3DSMax ou Cinema4D)
- Realflow pour l'animation des fluides (mais aussi Houdini)
- Massive pour la simulation des foules
- Nuke pour le compositing
- des logiciels dont les noms m'échappent pour l'étalonnage
- Houdini pour plein de trucs plus spécialisés (particules, fumées, mais c'est très réducteur)
- Arnold pour le rendu (mais aussi PRMan, VRay et une quantité d'autres)
- Mari pour le texturing 3D
- Katana pour la gestion procédurale d'énormes scènes
- des softs de reconstructions 3D pour les LiDar, la photogrammétrie
- des logiciels pour le Motion Capture
- d'autres dont je n'ai même pas idée parce qu'ils internes à des studios

# Pipeline et artistes

La multitude de logiciels utilisés force les studios à avoir des équipes entières pour automatiser le flux de production au maximum: c'est le fameux "pipeline", aux contours aussi obscurs que le nom est générique. Ce pipeline est composé de plein de bouts de code plus ou moins liés aux logiciels: ça va du script pour forcer des conventions de nommage de fichiers (rigolez pas, quand il y a 1000 artistes dans des studios autour du monde, c'est un problème crucial) à des formats de données très spécifiques pour pouvoir réutiliser le résultat d'un logiciel dans un autre (et qui donc force à développer des plugins pour chaque hôte ciblée) à des logiciels entiers parce qu'on ne les trouve pas le commerce.

Du coup quand on remplace un soft par un autre, ce n'est pas juste un exécutable différent à lancer en début de journée: il faut prendre en compte toute son intégration dans une chaine de production, avec tout ce que ça implique pour le pipeline d'une part, mais aussi pour trouver des artistes qui puissent l'utiliser d'autre part. Si c'est déjà compliqué de trouver de bons utilisateurs de Maya avec de l'expérience qui ne pensent plus à leur outil mais au boulot à faire, alors trouver un équivalent pour Blender c'est presque mission impossible. Et pourtant Blender a bien plus d'utilisateurs que Maya: Maya a cependant énormément plus d'utilisateurs professionnels que l'on peut embaucher sur portfolio et réputation. Je le regrette, mais c'est un fait qui compte beaucoup dans l'inertie à évoluer sur d'autres logiciels, sans même avoir commencé à parler de la qualité des alternatives.

# Déléguer la maintenance des applications aux éditeurs

C'est d'ailleurs ces deux facteurs (pipelines et disponibilité des artistes) qui a poussé deux points importants de l'industrie: l'abandon et la revente progressifs des logiciels internes et l'ouverture des sources de plein de briques de base.

Des logiciels comme Nuke, Arnold ou Massive (ou… Blender, mais l'ouverture s'est faite dans un tout autre contexte) étaient d'abord des logiciels développés aux seins de studios pour leur propre usage. Ils ont été revendus à des éditeurs ou sont devenus des boites à parts entières parce que d'une part payer des licences revient moins cher que de payer des développeurs dans certains cas, mais surtout cela rend le recrutement moins cher vu que les artistes sont déjà formés et expérimentés en arrivant dans le studio. L'éditeur a tout intérêt à mettre le paquet sur la formation et la qualité de ses softs s'il veut vendre des licences: c'est autant d'argent qui est économisé par les studios.

En somme, un artiste formé à l'outil est un artiste plus facile à intégrer dans le "pipeline humain": c'est toujours plus marrant de discuter des effets à produire plutôt que des boutons à cliquer.

# Passer ses technos en libre pour faciliter l'intégration

Les départements R&D ouvrent de plus en plus des bibliothèques de code ou contribuent à des projets libres pour suivre la même logique d'intégration dans le pipeline. Par exemple le format d'image OpenEXR était utilisé en interne chez Industrial Light & Magic avant d'être libéré sous BSD-3. L'intérêt était moins de recevoir des patches que de laisser aux éditeurs la tâche d'intégrer EXR à leurs softs. Ça a été un succès, et c'est loin d'être le seul: les technos libérées par [Mikros](http://opensource.mikrosimage.eu/), [Disney](https://disney.github.io/), [ILM](https://www.ilm.com/hatsrabbits/materialx-released/) ou [Pixar](http://graphics.pixar.com/) valent le coup d'oeil. Il y a un blog qui parle de l'open source (c'est très clairement la philosophie Open Source plutôt que Free Software qui domine cette industrie), mais il ne semble plus très actif: [http://opensourcevfx.org/](http://opensourcevfx.org/).

# Du libre partout ?

À titre personnel je rêve de voir les studios tourner le dos aux grands éditeurs de logiciels et de dépenser les montagnes de fric de leurs budgets licences pour mutualiser leurs efforts dans Blender, Gimp, Krita, Cycle, DjvView et les autres. Mais on y viendra. La gronde contre les éditeurs monopolistiques monte et les alternatives sont de plus en plus abouties: Eevee, le nouveau moteur temps réel de Blender commence à faire saliver pas mal de monde et ouvre de belles portes.
