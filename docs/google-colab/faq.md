Colaboratory

Questions fréquentes
====================

Les bases
---------

**Qu'est-ce que Colaboratory ?link**

Colab est un service hébergé de notebooks Jupyter qui ne nécessite aucune configuration et qui permet d'accéder sans frais à des ressources informatiques, y compris des GPU et des TPU. Colab est particulièrement adapté au machine learning, à la data science et à l'enseignement.

**Est-ce vraiment sans frais ?link**

Oui. L'utilisation de Colab est sans frais.

**Cela semble trop beau pour être vrai. Quelles sont les limites ?link**

Afin de fournir un accès au plus grand nombre possible d'élèves et de groupes défavorisés dans le monde, Colab donne la priorité aux utilisateurs qui font activement de la programmation sur un notebook. Colab limite également les actions qui ont un impact négatif sur d'autres utilisateurs ou qui sont associées au contournement de nos règles de lutte contre les abus. Consultez [Quelles activités sont limitées dans Colab ?](https://research.google.com/colaboratory/faq.html#disallowed-activities) pour consulter la liste des actions non autorisées. Les ressources de Colab ne sont pas illimitées, et l'accès n'est pas garanti. De plus, les limites d'utilisation sont susceptibles de fluctuer. Ces contraintes sont nécessaires pour maintenir un accès sans frais aux ressources de Colab. Pour plus de détails, consultez [Limites de ressources](https://research.google.com/colaboratory/faq.html#resource-limits).

**Quelles activités sont limitées dans Colab ?link**

Les environnements d'exécution gérés par Colab interdisent les actions abusives qui ont un impact négatif sur d'autres utilisateurs, ainsi que les actions associées au contournement de nos règles. Les éléments suivants sont interdits dans tous les environnements d'exécution gérés Colab :

-   Hébergement de fichiers, diffusion de contenus multimédias ou autres services Web non liés aux calculs interactifs avec Colab
-   Téléchargement de torrents ou partage de fichiers en peer-to-peer
-   Connexion à des proxys distants
-   Minage de cryptomonnaie
-   Exécution d'attaques par déni de service
-   Cassage de mot de passe
-   Utilisation de plusieurs comptes pour contourner les restrictions d'accès ou d'utilisation des ressources
-   Création de deepfakes
-   Utilisation de techniques telles que la conteneurisation pour contourner les règles de lutte contre les abus

Malheureusement, il n'est pas possible de fournir plus de détails sur le fonctionnement de notre système de détection des abus, car des acteurs malintentionnés tentent d'exploiter les subventions de calcul offertes par Colab.

En plus de ces restrictions et afin de fournir l'accès aux étudiants et aux groupes défavorisés dans le monde, Colab donne la priorité aux utilisateurs qui font activement de la programmation sur un notebook. Si vous ne disposez pas d'un solde d'unités de calcul positif, les éléments suivants sont interdits dans les environnements d'exécution gérés de la version sans frais de Colab et peuvent être fermés à tout moment sans avertissement :

-   Contrôle à distance (shells SSH, bureaux à distance, etc.)
-   Contournement de l'UI du notebook pour interagir principalement via une UI Web
-   Entraînement aux échecs
-   Exécution de nœuds de calcul distribués

Vous pouvez supprimer ces types de restrictions en souscrivant l'un de nos forfaits payants sur [cette page](http://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=disallowed-activities) et en maintenant un solde d'unités de calcul positif. Il se peut que les environnements d'exécution correspondant aux descriptions ne soient pas tous fermés, car nous essayons autant que possible de soutenir la communauté mondiale.

Vous pouvez acheter des ressources dont l'accès vous sera garanti sans les limites d'utilisation imposées par Colab sur [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=why_arent_resources_guaranteed) ou [Colab Enterprise](http://cloud.google.com/vertex-ai-notebooks), ou utiliser vos propres ressources de calcul via un [environnement d'exécution local](https://research.google.com/colaboratory/local-runtimes.html) que vous contrôlez. Notez que l'installation de Google Drive sur le système de fichiers en cours d'exécution ne fonctionne pas avec ces approches.

**Pourquoi mon environnement d'exécution Colab continue-t-il de s'arrêter prématurément ?link**

Pour permettre l'accès aux étudiants et aux groupes défavorisés dans le monde entier, Colab donne la priorité aux utilisateurs qui font activement de la programmation sur un notebook.

Les utilisateurs bénéficiant de la version sans frais sont souvent interrompus lorsqu'ils tentent de contourner l'interface du notebook et d'utiliser une interface Web sur un environnement d'exécution colab géré pour générer du contenu. Bien que ces expériences soient populaires et impressionnantes, elles nécessitent beaucoup de ressources de calcul et ne font pas partie de nos priorités pour les utilisateurs de la version sans frais, que nous souhaitons aider à programmer.

Vous pouvez supprimer ces types de restrictions en achetant l'un de nos forfaits payants sur [cette page](http://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=runtime-terminations).

Vous pouvez acheter des ressources dont l'accès vous sera garanti sans les limites d'utilisation imposées par Colab sur [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=why_arent_resources_guaranteed) ou [Colab Enterprise](http://cloud.google.com/vertex-ai-notebooks), ou utiliser vos propres ressources de calcul via un [environnement d'exécution local](https://research.google.com/colaboratory/local-runtimes.html) que vous contrôlez. Notez que l'installation de Google Drive sur le système de fichiers en cours d'exécution ne fonctionne pas avec ces approches.

**Quelle est la différence entre Jupyter et Colab ?link**

[Jupyter](https://jupyter.org/) est le projet Open Source sur lequel Colab est basé. Colab vous permet d'utiliser et de partager des notebooks Jupyter avec d'autres personnes, sans avoir besoin de télécharger, d'installer ni d'exécuter quoi que ce soit.

Utiliser Colab
--------------

**Où sont stockés mes notebooks, et puis-je les partager ?link**

Les notebooks Colab sont stockés dans [Google Drive](https://drive.google.com/). Vous pouvez aussi les charger depuis [GitHub](https://github.com/). Vous pouvez partager des notebooks Colab comme vous le feriez avec des documents Google Docs ou Sheets. Cliquez simplement sur le bouton "Partager" dans l'angle supérieur droit d'un notebook Colab ou suivez ces [instructions pour le partage de fichiers](https://support.google.com/drive/answer/2494822?co=GENIE.Platform%3DDesktop&hl=en) Google Drive.

**Si je partage mon notebook, quels éléments seront partagés ?link**

Si vous choisissez de partager un notebook, l'ensemble de son contenu (texte, code, élément de sortie et commentaires) sera partagé. Vous pouvez bloquer l'enregistrement ou le partage du contenu en sortie des cellules de code. Pour ce faire, sélectionnez **Modifier > Paramètres du notebook > Omettre l'élément de sortie des cellules de code lors de l'enregistrement de ce notebook**. La machine virtuelle que vous utilisez, y compris les fichiers et bibliothèques personnalisés que vous avez configurés, ne sera pas partagée. Nous vous conseillons donc d'inclure les cellules qui installent et chargent les [bibliothèques](https://colab.research.google.com/notebooks/snippets/importing_libraries.ipynb) ou les [fichiers](https://colab.research.google.com/notebooks/io.ipynb) personnalisés nécessaires à votre notebook.

**Puis-je importer un notebook Jupyter/IPython existant dans Colab ?link**

Oui. Dans le menu "Fichier", sélectionnez "Importer le notebook".

**Comment puis-je rechercher des notebooks Colab ?link**

Pour rechercher des notebooks Colab, utilisez [Google Drive](https://drive.google.com/). Cliquez sur le logo Colab dans l'angle supérieur gauche du notebook pour afficher tous les notebooks dans Google Drive. Vous pouvez également rechercher les notebooks que vous avez ouverts récemment dans **Fichier > Ouvrir le notebook**.

**Où mon code est-il exécuté ? Si je ferme la fenêtre du navigateur, quel impact cela a-t-il sur l'exécution du code ?link**

Votre code est exécuté sur une machine virtuelle propre à votre compte. Les machines virtuelles sont supprimées lorsqu'elles sont inactives pendant un certain temps et ont une durée de vie maximale imposée par le service Colab.

**Comment puis-je récupérer mes données ?link**

Vous pouvez télécharger n'importe quel notebook Colab créé à partir de Google Drive. Pour cela, suivez [ces instructions](https://support.google.com/drive/answer/2423534), ou accédez au menu "Fichier" dans Colab. Tous les notebooks Colab sont stockés au format Open Source de notebook Jupyter (.ipynb).

**Comment réinitialiser la ou les machines virtuelles sur lesquelles mon code est exécuté, et pourquoi cette fonctionnalité est-elle parfois indisponible ?link**

Sélectionnez **Exécution > Déconnecter et supprimer l'environnement d'exécution** pour rétablir l'état d'origine de toutes les machines virtuelles qui vous ont été attribuées. Cela peut être utile dans les cas où une machine virtuelle n'est plus fonctionnelle, par exemple suite à un remplacement accidentel de fichiers système ou à l'installation d'un logiciel incompatible. Colab limite la fréquence de telles réinitialisations pour éviter une consommation excessive des ressources. Si l'opération échoue, veuillez réessayer plus tard.

**Pourquoi `drive.mount()` affiche-t-il parfois l'erreur "Délai expiré", et pourquoi les opérations E/S de lecture à partir de dossiers échouent-elles parfois ?link**

Les opérations Google Drive peuvent parfois dépasser le délai lorsque le nombre de fichiers ou de sous-dossiers dans un dossier est trop élevé. Évitez de stocker des milliers d'éléments dans le dossier de premier niveau "Mon Drive". Si vous stockez plus d'environ 10 000 éléments dans le répertoire racine, l'installation peut échouer.\
Si vous rencontrez ce problème, essayez de déplacer les fichiers et dossiers contenus directement dans "Mon Drive" vers des sous-dossiers, mais veillez à ce que chaque dossier ne contienne pas plus d'environ 10 000 éléments.\
Un problème similaire peut survenir lorsque vous consultez les fichiers depuis d'autres dossiers après un `drive.mount()` réussi. Accéder à des éléments d'un dossier qui en contient beaucoup peut générer des erreurs telles que `OSError: [Errno 5] Input/output error`. Vous pouvez résoudre ce problème en déplaçant les éléments contenus directement dans le dossier vers des sous-dossiers.\
Sachez que "supprimer" des fichiers ou des sous-dossiers en les déplaçant vers la corbeille ne suffira pas forcément. Si cela n'a aucun effet, veillez à également [vider la corbeille](https://support.google.com/drive/answer/2375102#permanent).\
Vous pouvez aussi essayer d'utiliser DagsHub Storage, une alternative à Google Drive conçue pour travailler sur de grands ensembles de données et le machine learning. Elle est généralement plus évolutive et fiable pour les types de workflows courants sur Colab. Pour en savoir plus, consultez la [documentation correspondante](https://dagshub.com/docs/integration_guide/google_colab/index.html#dagshub-storage-buckets-integration-with-google-colab) ou le [notebook d'exemple](https://colab.research.google.com/#fileId=https%3A//dagshub.com/DagsHub/DagsHubxColab/raw/20590c0774d08c5e010c8c610dbc1aded7ccb2b3/DagsHub_x_Colab-DagsHub_Storage.ipynb). DagsHub est un service tiers non affilié à Google.

**Pourquoi `drive.mount()` est-il parfois lent ?link**

Les fichiers stockés dans Google Drive peuvent être stockés dans une région éloignée de votre environnement d'exécution Colab. Pour optimiser les performances, réduisez les lectures/écritures depuis Drive. Notez que les opérations dans les dossiers installés par `drive.mount()` dépendent de l'environnement d'exécution Colab. Si vous essayez de déplacer des fichiers d'un dossier à un autre via Colab et que votre opération est interrompue, vous pourriez perdre toutes les données en transit.

**Pourquoi "Installer Drive" insère parfois du code dans le notebook ?link**

Installer Google Drive sur Colab permet à n'importe quel code de votre notebook d'accéder à tous les fichiers de votre Google Drive. En général, nous exigeons que les utilisateurs accordent cet accès manuellement, en ajoutant une cellule de code au notebook, chaque fois qu'ils se connectent à un nouvel environnement d'exécution. Cela permet de s'assurer que l'utilisateur a bien compris les autorisations accordées au notebook.\
Dans certains cas, nous ne demandons qu'une autorisation Google Drive et nous réinstallons automatiquement Google Drive lors des sessions suivantes. Pour protéger vos fichiers, cette façon de faire n'est autorisée que si un notebook remplit un certain nombre de conditions. Par exemple, les notebooks modifiés par un autre utilisateur n'installent pas automatiquement Google Drive.

**Pourquoi les opérations Drive échouent-elles parfois en raison du quota ?link**

Diverses limites sont appliquées dans Google Drive, telles que le nombre d'opérations effectuées (par utilisateur et par fichier) et des quotas de bande passante. Le dépassement de ces limites déclenche une erreur `Input/output error` (comme dans l'exemple ci-dessus) et l'affichage d'une notification dans l'interface utilisateur de Colab. Ce scénario se produit habituellement lors d'une tentative d'accès à un fichier partagé populaire, ou à une quantité trop élevée de fichiers distincts de manière trop soudaine. Exemples de méthodes pour contourner le problème :

-   Copiez le fichier via [drive.google.com](https://drive.google.com/) et évitez de le partager à grande échelle, afin que les autres utilisateurs n'atteignent pas les limites qui s'y appliquent.
-   Évitez d'effectuer de nombreuses opérations de lecture d'E/S de faible ampleur. Privilégiez la copie des données de Drive vers la VM Colab dans un format d'archive (par exemple, `.zip` ou `.tar.gz`) et désarchivez les données localement sur la VM plutôt que dans le répertoire Drive installé.
-   Patientez une journée pour que les limites de quota soient réinitialisées.

**Pourquoi les opérations Drive échouent-elles parfois en raison du quota de stockage ?link**

La quantité de données que chaque utilisateur peut stocker dans Google Drive est limitée. Si les opérations Drive échouent avec une erreur `Input/output error`, et qu'une notification indique que le quota de stockage a été dépassé, supprimez certains fichiers via [drive.google.com](https://drive.google.com/) et [videz la corbeille](https://support.google.com/drive/answer/2375102#permanent) pour libérer de l'espace. Vous devrez peut-être patienter un instant avant que l'espace libéré soit disponible dans Colab.

Pour acheter davantage d'espace Drive, accédez à [Google Drive](https://drive.google.com/settings/storage). Sachez que l'achat d'espace supplémentaire sur Drive ne permet pas d'augmenter l'espace disque disponible sur les VM Colab. En revanche, cela est possible grâce à un abonnement [Colab Pro](http://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=storage_full).

Limites de ressources link
--------------------------

**Pourquoi l'accès aux ressources n'est-il pas garanti dans Colab ?link**

Pour proposer dynamiquement de puissants GPU à grande échelle et à bas prix, Colab doit rester flexible pour ajuster dynamiquement les limites d'utilisation et la disponibilité du matériel.

Dans la version sans frais de Colab, l'accès aux ressources coûteuses, comme les GPU, est extrêmement limité. Pour la version payante, nous tenons à offrir un bon rapport qualité/prix aux utilisateurs.

Vous pouvez acheter des ressources dont l'accès vous sera garanti sans les limites d'utilisation imposées par Colab sur [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=why_arent_resources_guaranteed) ou [Colab Enterprise](http://cloud.google.com/vertex-ai-notebooks), ou utiliser vos propres ressources de calcul via un [environnement d'exécution local](https://research.google.com/colaboratory/local-runtimes.html) que vous contrôlez. Notez que l'installation de Google Drive sur le système de fichiers en cours d'exécution ne fonctionne pas avec ces approches.

**Quelles sont les limites d'utilisation de Colab ?link**

Colab peut fournir un accès sans frais à des ressources dont l'utilisation est limitée dynamiquement et pour lesquelles l'accès n'est pas garanti ni illimité. Cela signifie que les limites d'utilisation globale, les délais d'expiration en cas d'inactivité, la durée de disponibilité maximale des machines virtuelles, les types de GPU disponibles et d'autres facteurs vont varier au fil du temps. Colab ne publie pas ces limites, entre autres parce qu'elles peuvent varier au fil du temps.

Pour bénéficier d'une puissance de calcul accrue et des temps d'exécution prolongés, souscrivez l'un de nos forfaits payants sur [cette page](http://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=what_are_usage_limits). Ces forfaits ont une dynamique similaire, dans le sens où la disponibilité des ressources peut évoluer avec le temps. Les utilisateurs payants dont le solde d'unités de calcul est épuisé seront soumis aux règles et restrictions liées à la version sans frais jusqu'à ce que le solde soit augmenté.

Vous pouvez acheter des ressources dont l'accès vous sera garanti sans les limites d'utilisation imposées par Colab sur [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=why_arent_resources_guaranteed) ou [Colab Enterprise](http://cloud.google.com/vertex-ai-notebooks), ou utiliser vos propres ressources de calcul via un [environnement d'exécution local](https://research.google.com/colaboratory/local-runtimes.html) que vous contrôlez. Notez que l'installation de Google Drive sur le système de fichiers en cours d'exécution ne fonctionne pas avec ces approches.

**Quels types de GPU/TPU sont disponibles dans Colab ?link**

Cela varie avec le temps (une fluctuation nécessaire pour maintenir un accès sans frais à ces ressources de Colab).

Pour accéder aux GPU premium (sous réserve de disponibilité), choisissez l'un de nos forfaits payants sur [cette page](http://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=what_types_of_gpus).

Si vous voulez accéder à du matériel dédié spécifique, recherchez-le sur Colab via [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=what_types_of_gpus).

**Combien de temps les notebooks peuvent-ils être exécutés dans Colab ?link**

Colab priorise les calculs interactifs. Si vous êtes inactif, les environnements d'exécution expireront.

Dans la version sans frais de Colab, la durée d'exécution maximale des notebooks est de 12 heures, selon la disponibilité et vos habitudes d'utilisation. Colab Pro, Pro+ et le paiement à l'usage vous offrent une disponibilité de calcul accrue en fonction de votre solde d'unités de calcul.

En règle générale, la durée d'exécution maximale des notebooks est de 12 heures, selon la disponibilité et vos habitudes d'utilisation. Après l'épuisement de vos unités de calcul disponibles avec le forfait Pro, Pro+ ou de paiement à l'usage, vous pouvez vous attendre à ce que le backend cesse de fonctionner.

Colab Pro+ permet l'exécution continue de code pendant 24 heures maximum, si vous disposez de suffisamment d'unités de calcul. Les délais d'inactivité ne s'appliquent que si l'exécution du code prend fin.

Vous pouvez assouplir entièrement les limites d'exécution et délais d'inactivité en achetant une VM dédiée sur [GCP Marketplace](https://research.google.com/colaboratory/marketplace.html?utm_source=faq&utm_medium=link&utm_campaign=how_long_can_nbs_run).

**Quelle est la quantité de mémoire disponible dans Colab ?link**

Dans la version sans frais de Colab, vous pouvez accéder aux VM avec un profil de mémoire système standard.

Dans les versions payantes de Colab, vous pouvez accéder aux machines avec un profil système à haute capacité de mémoire, selon la disponibilité et votre solde d'unités de calcul.

Notez que la mémoire renvoie à la mémoire système. Toutes les puces GPU ont le même profil de mémoire.

**Comment exploiter tout le potentiel de Colab ?link**

Une fois que vous avez terminé votre tâche, pensez à fermer les onglets Colab. Évitez aussi de recourir inutilement à des GPU ou à de la mémoire supplémentaire. Vous réduirez ainsi le risque de voir votre utilisation limitée dans Colab. Si vous atteignez les limites, vous pouvez toujours acheter d'autres ressources de calcul via le paiement à l'usage.

Pour savoir comment exploiter pleinement la version payante de Colab, consultez [Tirer pleinement parti de votre abonnement à Colab](https://colab.research.google.com/notebooks/pro.ipynb).

**Un message m'avertit que mon GPU n'est pas utilisé. Que dois-je faire ?link**

Colab propose des environnements informatiques accélérés facultatifs, y compris le GPU et le TPU. L'exécution de code dans un environnement GPU ou TPU ne signifie pas automatiquement que le GPU ou le TPU sont utilisés. Pour éviter d'atteindre vos [limites d'utilisation](https://research.google.com/colaboratory/faq.html#usage-limits) du GPU, nous vous recommandons de passer à un environnement d'exécution standard si vous n'utilisez pas le GPU. Sélectionnez **Exécution > Modifier le type d'exécution** et définissez l'option Accélérateur matériel sur Aucun.

Pour en savoir plus sur l'utilisation des environnements d'exécution GPU et TPU dans Colab, consultez les exemples de notebooks [TensorFlow With GPU](https://colab.research.google.com/notebooks/gpu.ipynb) (TensorFlow avec GPU) et [TPUs In Colab](https://colab.research.google.com/notebooks/tpu.ipynb) (TPU dans Colab).

La nouvelle version de Colab axée sur l'IA
------------------------------------------

**En quoi consiste la nouvelle version de Google Colab axé sur l'IA ?link**

Cette nouvelle version réinvente l'expérience avec Colab en le transformant en un partenaire de codage intelligent. Elle propose une suite de fonctionnalités d'IA profondément intégrées, conçues pour comprendre vos objectifs et accélérer l'ensemble de votre workflow. Tout cela est accessible à travers une expérience conversationnelle unifiée, disponible directement dans votre notebook. Voici les principales fonctionnalités :

-   Requêtes itératives : interface conversationnelle simple pour générer du code, expliquer des concepts et corriger des erreurs
-   Data Science Agent (DSA) de nouvelle génération : agent capable d'analyser des données, de générer un plan, d'exécuter du code et de présenter des résultats de manière autonome
-   Transformation de code sans effort : possibilité de modifier le code existant dans votre notebook à l'aide de descriptions en langage naturel

**Comment utiliser les nouvelles fonctionnalités d'IA dans Colab ?link**

Les fonctionnalités d'IA sont activées par défaut pour tous les utilisateurs éligibles et sont intégrées dans l'ensemble de l'interface Colab. Pour commencer, le moyen le plus simple est de cliquer sur l'icône Gemini en forme d'étincelle, dans le pied de page du notebook, pour ouvrir le panneau de discussion principal. À mesure que vous tapez, vous verrez aussi des suggestions de saisie semi-automatique basées sur l'IA.

**Je ne trouve pas les nouvelles fonctionnalités d'IA. Pourquoi ?link**

Pour que vous puissiez accéder aux fonctionnalités d'IA de Colab, votre compte Google doit indiquer que vous avez au moins 18 ans. Si vous avez l'âge requis et que vous ne voyez toujours pas ces fonctionnalités (comme l'icône Gemini en forme d'étincelle ou les suggestions de saisie semi-automatique basées sur l'IA), veuillez vérifier si votre langue est prise en charge.

Si, après vérification, vous remplissez bien les conditions et vous n'avez toujours pas accès aux fonctionnalités, veuillez le signaler à l'aide de l'outil de commentaires intégré au produit (**Aide > Donner votre avis**). Pour recevoir une réponse par e-mail, vous devez cocher la case "Nous pourrons vous demander plus d'informations ou vous en envoyer par e-mail".

**Que puis-je faire avec l'IA dans Colab ?link**

L'IA de Colab est conçue pour être un partenaire polyvalent. Vous pouvez lui demander d'effectuer ce qui suit :

-   Générer et transformer du code : demandez des fonctions courtes, du code standard, ou même de refactoriser du code dans plusieurs cellules.
-   Discuter des bibliothèques Python : découvrez de nouveaux outils et demandez des exemples d'utilisation dans le contexte de votre travail.
-   Corriger les erreurs intelligemment : en cas d'erreurs, Colab suggérera des corrections de manière itérative dans une vue de comparaison afin que vous puissiez les étudier.
-   Exécuter des flux agentifs autonomes : déclenchez des workflows analytiques complets avec Data Science Agent. Indiquez simplement un objectif général, et l'agent générera un plan, exécutera le code nécessaire et présentera ses résultats.
-   Analyser vos données : importez des fichiers CSV, JSON ou Excel, par exemple, ou placez le curseur sur des données dans votre environnement d'exécution, et demandez à l'IA d'effectuer une analyse approfondie, de créer des visualisations et de dégager des insights.

**L'IA peut-elle exécuter du code de manière autonome dans mon notebook ?link**

Oui. L'une des principales caractéristiques de Colab axé sur l'IA est sa capacité à créer et exécuter des plans pour atteindre un objectif. Lorsque vous demandez une tâche en plusieurs étapes, comme analyser un ensemble de données, l'agent vous présente un plan à examiner. Vous pouvez ensuite choisir de l'exécuter, tout en gardant le contrôle pendant que l'agent travaille. Lors de l'exécution, il peut analyser les résultats, corriger automatiquement les erreurs et ajuster son plan.

**L'IA dans Colab a-t-elle accès à Internet ?link**

L'IA de Colab ne navigue pas directement sur Internet. Toutefois, elle peut générer et exécuter du code qui accède à Internet (par exemple, en utilisant des requêtes pour appeler une API ou wget afin de télécharger un fichier dans votre environnement d'exécution).

**L'IA de Colab peut-elle accéder à mes fichiers Google Drive ou à mes secrets utilisateur ?link**

Par défaut, l'IA de Colab n'a pas accès à vos fichiers Google Drive ni à vos secrets utilisateur. Toutefois, elle peut générer du code qui y accède **à votre demande explicite**.

**Quels types de fichiers l'IA de Colab peut-elle traiter en vue d'une analyse de données ?link**

L'IA de Colab prend en charge différents types de fichiers courants, dont les fichiers CSV, TSV, JSON et Excel (XLS, XLSX, XLSM, XLSB). Vous pouvez importer des fichiers directement dans l'interface de chat pour les analyser.

**Comment puis-je donner mon avis sur les fonctionnalités d'IA dans Colab ?link**

Votre avis est essentiel pour que des améliorations puissent être apportées. Lorsque l'IA génère une réponse, vous pouvez évaluer celle-ci à l'aide des icônes J'aime ou Je n'aime pas. Pour envoyer des commentaires plus détaillés, utilisez le menu à développer à droite, indiqué par trois points (...) > Donner votre avis.

**Comment utiliser le code généré par l'IA de Colab ?link**

L'IA de Colab est un puissant collaborateur conçu pour accélérer votre workflow et vous aider à prototyper des idées plus rapidement que jamais. Comme pour tout assistant de codage, vous êtes responsable de l'utilisation que vous faites du code. Nous vous recommandons vivement de soigneusement tester, vérifier et valider tout le code généré pour vous assurer qu'il est exact, sûr et conforme aux exigences de votre projet avant de l'utiliser. Pour vous aider dans cette optique, Colab cite aussi tout code généré qui cite directement une source sous licence Open Source.

**Quelles sont les données recueillies ? Comment sont-elles utilisées ?link**

Lorsque vous utilisez des fonctionnalités d'IA génératives dans Colab, Google collecte des requêtes, du code associé, des résultats générés, des informations associées sur l'utilisation des fonctionnalités et vos commentaires. Google utilise ces données pour fournir, améliorer et développer ses produits et services, ainsi que les technologies de machine learning, y compris les produits d'entreprise de Google tels que Google Cloud.

Afin de nous aider à améliorer nos produits et leur qualité, des évaluateurs manuels peuvent lire, annoter et traiter vos requêtes, le résultat généré, les informations associées sur l'utilisation des fonctionnalités et vos commentaires. Veuillez ne pas inclure d'informations sensibles (confidentielles) ni personnelles permettant de vous identifier ou d'identifier d'autres personnes dans vos requêtes ou vos commentaires. Vos données seront stockées de telle sorte que Google ne pourra pas savoir qui les a fournies, ne pourra plus traiter les demandes de suppression et les conservera pendant 18 mois au maximum.

Abonnements Colab Pro for Education.
------------------------------------

**Qu'est-ce qu'un abonnement Colab Pro for Education ?link**

Les abonnements Colab Pro for Education sont des abonnements Colab Pro sans frais d'un an destinés aux étudiants et aux professeurs des universités basées aux États-Unis. Ils sont sans frais pendant un an une fois l'éligibilité validée, et proposent exactement les mêmes avantages qu'un abonnement Colab Pro personnel (y compris un quota mensuel d'unités de calcul).

**Puis-je m'abonner à Colab Pro for Education ?link**

Tous les étudiants et enseignants d'universités basées aux États-Unis qui se trouvent aux États-Unis au moment de la validation sont éligibles, dans la limite des stocks disponibles. Consultez les articles du centre d'aide de SheerID pour connaître les critères d'éligibilité pour les [étudiants](https://verify.sheerid.com/student-faq-b/) et les [enseignants](https://verify.sheerid.com/teacher-faq-b/), ainsi que pour en savoir plus sur votre éligibilité spécifique et sur les documents pouvant être requis pour la confirmer.

**Puis-je valider à nouveau mon statut pour bénéficier d'une année supplémentaire d'abonnement à Colab Pro for Education ?link**

Vous pouvez valider à nouveau votre statut d'étudiant ou d'enseignant 335 jours après votre inscription initiale à Colab Pro for Education. Vous pouvez consulter votre date de renouvellement en accédant à Paramètres -> Colab Pro. Ensuite, pour valider à nouveau votre statut, accédez à la [page d'inscription à Colab](https://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=reverify_for_edu_pro) et cliquez sur "Sans frais pour les élèves et les enseignants".

**Comment puis-je m'abonner à Colab Pro for Education ?link**

Cliquez sur le bouton "Sans frais pour les élèves et les enseignants" ci-dessus pour être redirigé vers SheerID, le partenaire tiers de Colab chargé de la validation de l'identité, afin de confirmer votre éligibilité. Si le lien n'apparaît pas, cela signifie que les abonnements Colab Pro for Education à prix réduit sont épuisés pour le moment.

SheerID vous guidera dans le processus de validation de votre éligibilité après que vous aurez cliqué sur le lien ci-dessus. Assurez-vous de remplir le formulaire avec l'adresse e-mail du compte auquel vous étiez connecté lorsque vous avez accédé à la page d'inscription sur Colab (et non avec votre adresse e-mail .edu). Sinon, votre validation ne sera pas enregistrée et vous ne bénéficierez pas de l'abonnement à prix réduit.

Une fois le formulaire SheerID envoyé, vous serez prévenu si la validation instantanée a réussi ou vous serez invité à fournir des documents/informations supplémentaires. SheerID vous tiendra au courant par e-mail jusqu'à ce que le processus soit terminé.

Peu de temps après avoir reçu la confirmation de la validation, vous devriez voir votre abonnement Colab Pro for Education à prix réduit dans votre compte. Vous pouvez vous en assurer en accédant à Paramètres > Colab Pro.

**Puis-je avoir un abonnement Colab Pro for Education et un abonnement personnel en même temps ?link**

Non, vous ne pouvez pas utiliser simultanément un abonnement personnel et un abonnement Colab Pro for Education. Si vous vous inscrivez à l'un, vous serez désabonné de l'autre. Par exemple, si vous payez actuellement un abonnement personnel via Google Payments et que vous validez votre éligibilité à un nouvel abonnement Colab Pro for Education, Colab vous désabonnera automatiquement de votre abonnement personnel payant, puis vous inscrira à un abonnement sans frais.

Cela signifie que si vous souhaitez conserver un abonnement personnel payant à Colab après l'expiration de votre abonnement Colab Pro for Education, vous devrez vous réinscrire à un abonnement payant (sauf si vous êtes éligible à une autre année de Pro à prix réduit grâce à votre statut d'étudiant ou d'enseignant).

Réciproquement, si vous avez un abonnement Colab Pro for Education et que vous vous inscrivez à un compte payant, votre abonnement Colab Pro for Education sera supprimé de votre compte. Vous devrez vous réinscrire auprès de SheerID si vous souhaitez en bénéficier à nouveau.

**Puis-je avoir un abonnement Colab Pro for Education et un abonnement Workspace en même temps ?link**

Oui. Dans ce scénario, un administrateur d'entité Workspace choisit d'acheter une licence Colab payante et de l'attribuer à l'utilisateur. L'utilisateur devra également faire valider son identité séparément auprès de SheerID et obtenir un abonnement Colab Pro for Education. Dans ce cas, l'utilisateur verra des unités de calcul supplémentaires pour l'abonnement Colab Pro for Education être ajoutées à son compte chaque mois pendant toute la durée de l'abonnement (un an), en fonction du moment où la validation avec SheerID a été effectuée. Cette distribution aura lieu à une fréquence différente de celle de la distribution des unités de calcul Workspace (qui a lieu le premier jour du mois).

**Combien de temps durera cette offre ?link**

Cette offre promotionnelle pour Google Colab est disponible pour une durée limitée et pour un nombre limité d'utilisateurs. Google se réserve le droit de modifier ou de résilier l'offre à sa seule discrétion.

**Un message indiquant que l'offre n'est plus disponible s'affiche sur le formulaire de validation. Qu'est-ce que cela signifie ?link**

Le quota actuel d'abonnements Colab Pro for Education sans frais est épuisé pour le moment. Vous pourrez vérifier ultérieurement si l'offre est de nouveau disponible en accédant à la [page d'inscription à Colab](https://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=reverify_for_edu_pro) et en cliquant sur "Sans frais pour les élèves et les enseignants". Si ce bouton n'apparaît pas, cela signifie également que l'offre n'est plus disponible.

**À l'aide ! J'ai bien effectué la validation avec SheerID, mais je ne vois pas d'abonnement Colab Pro for Education dans mon compte.link**

Une fois la validation effectuée avec SheerID, vous devriez voir immédiatement un abonnement Colab Pro for Education dans votre compte lorsque vous utilisez Colab.

Le problème est souvent dû au fait que les utilisateurs lancent la validation avec le mauvais compte. Veuillez vous assurer d'être connecté au compte que vous avez utilisé pour accéder à la page d'inscription à Colab afin de lancer la procédure de validation, car c'est ce compte qui bénéficiera de l'abonnement Colab Pro for Education sans frais. Il n'existe actuellement aucun moyen de transférer rétroactivement l'abonnement vers un autre compte.

**J'ai déjà effectué une validation avec SheerID pour un autre produit Google (Google One, YouTube, etc.). Cela me rend-il éligible à un abonnement Colab Pro for Education ?link**

Non. Les validations SheerID ne sont pas transférables entre les produits Google. Si vous avez effectué la validation avec SheerID pour un autre produit Google (Google One, YouTube Premium, etc.), vous devrez le refaire pour Colab afin de bénéficier d'un abonnement Colab Pro for Education.

**Je rencontre des difficultés pour valider mon éligibilité. Qui dois-je contacter ?link**

SheerID est notre partenaire tiers de validation de l'identité. Veuillez le contacter directement si vous avez des questions sur votre état ou votre éligibilité, ou pour tout problème lié à la procédure de validation. Vous pouvez [consulter son centre d'aide](https://support.sheerid.com/en-US/help-center) ou [le contacter en envoyant une demande d'assistance](https://support.sheerid.com/en-US/help-center/contact-form). Si vous avez bien effectué la validation avec SheerID, mais que vous ne voyez pas l'abonnement Colab Pro for Education dans votre compte lorsque vous utilisez Colab, veuillez consulter la réponse à la question fréquente ci-dessus.

Questions supplémentaires
-------------------------

**Quels sont les navigateurs compatibles ?link**

Colab fonctionne avec la plupart des principaux navigateurs, et a fait l'objet des tests les plus complets pour les dernières versions de [Chrome](https://www.google.com/chrome/browser/desktop/index.html), [Firefox](https://www.mozilla.org/en-US/firefox/) et [Safari](https://www.apple.com/safari/).

**En quoi ce projet est-il lié à colaboratory.jupyter.org ?link**

En 2014, nous avons collaboré avec l'équipe de développement de Jupyter pour publier une première version de l'outil. Depuis, Colab a continué d'évoluer pour répondre aux besoins en interne.

**Qu'en est-il des autres langages de programmation ?link**

Colab vise principalement la prise en charge de Python et de son écosystème d'outils tiers. Nous savons que les utilisateurs apprécieraient une compatibilité avec d'autres noyaux Jupyter (tels que R ou Scala). Nous aimerions assurer une compatibilité avec ces noyaux, mais nous n'avons pas encore de date d'échéance estimative.

**J'ai trouvé un bug ou j'ai une question. Qui dois-je contacter ?link**

Ouvrez n'importe quel notebook Colab. Accédez au menu "Aide", puis sélectionnez "Donner votre avis".

**Pourquoi envoyer une invite demandant l'activation des cookies tiers ?link**

Colab utilise des iFrames HTML et des service workers hébergés sur des origines séparées afin d'afficher les sorties riches de manière sécurisée. Les navigateurs [nécessitent l'activation des cookies tiers pour utiliser les service workers dans les iFrames](https://dev.chromium.org/Home/chromium-security/security-faq/service-worker-security-faq#TOC-Can-iframes-register-Service-Workers-). La solution alternative à l'activation des cookies tiers pour tous les sites consiste à autoriser le nom d'hôte suivant dans les paramètres du navigateur : googleusercontent.com.

**Comment puis-je modifier la police de l'éditeur ?link**

Colab utilise une police monospace générique pour l'éditeur. Vous pouvez configurer la famille de polices qui est utilisée pour le format monospace dans la plupart des navigateurs modernes. Voici quelques exemples courants :

-   Pour Firefox, suivez les instructions fournies dans les [documents d'assistance de Firefox](https://support.mozilla.org/en-US/kb/change-fonts-and-colors-websites-use#w_changing-font) afin de configurer la police "Monospace".
-   Dans Chrome, accédez à "chrome://settings/fonts" et modifiez la section "Police à largeur fixe".

**Colab est-il compatible avec Python 2 ?link**

Python 2 n'est plus compatible avec Colab. Pour plus d'informations sur la migration de votre code Python 2 vers Python 3, consultez la section [Portage de code Python 2 vers Python 3](https://docs.python.org/3/howto/pyporting.html).

**Où puis-je en savoir plus sur les versions payantes de Colab ?link**

Consultez les questions fréquentes sur la [page d'inscription](https://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=learn_more_about_pro).

**Comment la facturation fonctionne-t-elle pour les versions payantes de Colab ?link**

Vous trouverez sur la [page d'inscription](https://colab.research.google.com/signup?utm_source=faq&utm_medium=link&utm_campaign=how_billing_works) des informations sur Colab Pro, Colab Pro+ et le paiement à l'usage, y compris sur les tarifs et la gestion des mises à niveau.

**Comment puis-je accéder à Colab avec un compte Workspace ?link**

C'est [l'administrateur de votre organisation qui autorise ou non](https://support.google.com/a/answer/11254550) les utilisateurs Workspace à accéder à Colab.

Les organisations disposant de Workspace for Education sont tenues d'obtenir une autorisation parentale permettant aux élèves (de moins de 18 ans) d'utiliser les services supplémentaires avec leur compte Google Workspace for Education. Pour ce faire, utilisez [ce modèle de document](https://support.google.com/a/answer/7391849). Assurez-vous d'inclure Colab dans la liste des services supplémentaires.

Pour en savoir plus, consultez l'article [Communiquer avec les parents et représentants légaux au sujet de Google Workspace for Education](https://support.google.com/a/answer/6356509) du centre d'aide.