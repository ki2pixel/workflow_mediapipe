# Documentation de référence sur dev.nix

Cette page inclut des informations sur le schéma de votre fichier de configuration de l'environnement de l'espace de travail, qui doit toujours se trouver à l'emplacement `.idx/dev.nix`.

Pour en savoir plus sur le langage Nix, consultez le [tutoriel officiel sur le langage Nix](https://nixos.org/guides/nix-pills/).

## packages

Packages à installer dans l'environnement.

Vous pouvez utiliser l'argument `pkgs` pour sélectionner les packages à installer, par exemple `pkgs.python3`. Notez que le contenu de `pkgs` dépend de l'option de canal `channel` sélectionnée.

Exemple :

```nix
{pkgs, ...}: {
  channel = "stable-23.11";
  packages = [pkgs.vim];
}
```

Vous pouvez rechercher les packages disponibles ici : [stable-23.11](https://search.nixos.org/packages?channel=23.11) ou [unstable](https://search.nixos.org/packages?channel=unstable).

*Type :* liste de packages
*Par défaut :* `[ ]`

## chaîne

Canal nixpkgs à utiliser.

Ce canal définit le contenu de l'argument `pkgs`.

Type : "stable-23.05", "stable-23.11", "stable-24.05", "stable-24.11" ou "unstable"

*Par défaut :* `"stable-23.11"`

## env

Variables d'environnement définies dans l'environnement de développement.

Elles sont propagées à tous vos shells et au serveur d'aperçu. Les variables d'environnement peuvent être particulièrement utiles si votre application nécessite un ensemble spécifique de variables.

La valeur de chaque variable peut être une chaîne ou une liste de chaînes. Ces derniers sont concaténés et séparés par des deux-points.

`PATH` doit être une liste, car elle est toujours étendue et jamais complètement remplacée.

Exemple :

```nix
{pkgs, ...}: {
  env = {
    HELLO = "world";
    # append an entry to PATH
    PATH = ["/some/path/bin"];
  };
}
```

*Type :* ensemble d'attributs de ((liste de chaînes) ou autre)
*Par défaut :* `{ }`

## idx.extensions

Extensions de code que vous souhaitez installer dans votre espace de travail IDX.

Il s'agit d'une liste d'ID d'extension complets, par exemple `${publisherId}.${extensionId}`.

Vous trouverez la liste des extensions disponibles sur le [registre Open VSX](https://open-vsx.org/). Vous pouvez les saisir dans votre fichier `dev.nix` en utilisant `${publisherId}.${extensionId}`.

*Type :* liste de (chaîne non vide ou chemin d'accès)
*Par défaut :* `[ ]`

## idx.previews.enable

Définissez cette valeur sur `true` pour activer les aperçus IDX.

Cette fonctionnalité permet d'exécuter et de recharger automatiquement vos applications pendant que vous les développez.

*Type :* booléen
*Par défaut :* `true`
*Exemple :* `true`

## idx.previews.previews

Prévisualisez les configurations.

Définissez les commandes qu'IDX exécute dans votre environnement de développement.

Exemple :

```nix
{pkgs, ...}: {
  idx.previews = {
    enable = true;
    previews = {
      web = {
        command = ["yes"];
        cwd = "subfolder";
        manager = "web";
        env = {
          HELLO = "world";
        };
      };
    };
  };
}
```

*Type :* ensemble d'attributs de (sous-module)
*Par défaut :* `{ }`

### idx.previews.previews.\<name\>.activity

Activité de lancement Android

*Type :* chaîne
*Par défaut :* `""`

### idx.previews.previews.\<name\>.command

Commande à exécuter

*Type :* liste de chaînes
*Par défaut :* `[ ]`

### idx.previews.previews.\<name\>.cwd

Répertoire de travail

*Type :* chaîne
*Par défaut :* `""`

### idx.previews.previews.\<name\>.env

Variables d'environnement à définir.

*Type :* ensemble d'attributs de chaîne
*Par défaut :* `{ }`

### idx.previews.previews.\<name\>.manager

Responsable

*Type :* "web", "flutter", "android" ou "gradle"

## idx.workspace.onCreate

Commandes à exécuter lorsque l'espace de travail est créé et ouvert pour la première fois.

Cela peut être utile pour configurer l'environnement de développement. Par exemple, voici comment spécifier l'exécution de `npm install` :

```nix
{pkgs, ...}: {
  idx.workspace.onCreate = {
    npm-install = "npm install";
    # files to open when the workspace is first opened.
    default.openFiles = [ "src/index.ts" ];
  };
}
```

*Type :* ensemble d'attributs (chemin d'accès, chaîne ou {[ openFiles = [ string ];]})
*Par défaut :* `{ }`

## idx.workspace.onStart

Commandes à exécuter chaque fois que l'espace de travail est ouvert.

Cela peut être utile pour démarrer les observateurs de compilation. Par exemple, nous spécifions ici deux commandes à exécuter :

```nix
{pkgs, ...}: {
  idx.workspace.onStart = {
    npm-watch-fe = "npm run watch:frontend";
    npm-watch-be = "npm run watch:backend";
    # files to open when the workspace is (re)opened.
    default.openFiles = [ "src/index.ts" ];
  };
}
```

*Type :* ensemble d'attributs (chemin d'accès, chaîne ou {[ openFiles = [ string ];]})
*Par défaut :* `{ }`

## importations

Vous pouvez étendre votre fichier dev.nix avec un fichier importé.

```nix
# dev.nix
{ pkgs, ... }: {
  imports = [
    ./some-file.nix
  ];
  # ...
}

# some-file.nix
{ pkgs, ... }: {
  packages = [
    pkgs.python3
  ];
  # ...
}
```

Vous pouvez importer un fichier `.nix` personnalisé dans `dev.nix` pour plusieurs raisons :

1.  Votre fichier `dev.nix` est volumineux et vous souhaitez le modulariser pour améliorer la maintenabilité.

    ```nix
    { pkgs, ... }: {
      channel = "stable-24.11";
      # ...
      imports = [
        ./env-cfg.nix
        ./preview-config.nix
      ];
    }
    ```

2.  Vous souhaitez configurer des options spécifiques à votre environnement local et ajouter le fichier à votre liste `.gitignore`.

    ```nix
    # dev.nix
    { pkgs, lib, ... }: {
      # ...

      imports = lib.optionals (builtins.pathExists ./.dev.local.nix ) [ ./.dev.local.nix ];
    }
    ```

    ```gitignore
    # .gitignore
    .idx/dev.local.nix
    ```

*Type :* liste de chemins d'accès
*Par défaut :* `[ ]`

## services

Services courants à activer lorsque l'espace de travail s'ouvre.

Par exemple, pour activer Postgres et utiliser l'extension `pgvector`, ajoutez les éléments suivants à `dev.nix` :

```nix
services.postgres = {
  extensions = ["pgvector"];
  enable = true;
};
```

Les sections suivantes listent tous les services compatibles et leurs options configurables.

### services.docker.enable

Indique si Docker sans racine doit être activé.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.mongodb.enable

Indique si le serveur MongoDB doit être activé.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.mongodb.package

Package MongoDB à utiliser.

*Type :* package
*Par défaut :* `<derivation mongodb-6.0.11>`

### services.mongodb.port

Configure le port sur lequel Mongod écoutera.

Par défaut, le protocole TCP est désactivé et Mongod n'écoute que sur /tmp/mongodb/mongodb.sock.

Pour vous connecter, utilisez la chaîne de connexion `mongodb://%2Ftmp%2Fmongodb%2Fmongodb.sock`.

*Type :* entier non signé de 16 bits, compris entre 0 et 65 535 (inclus)
*Par défaut :* `0`

### services.mysql.enable

Indique si le serveur MySQL doit être activé.

Le serveur est initialisé avec un utilisateur racine sans mot de passe. Pour créer des utilisateurs et des bases de données supplémentaires, utilisez SQL `mysql -u root`.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.mysql.package

Package MySQL à utiliser.

*Type :* package
*Par défaut :* `pkgs.mysql`
*Exemple :* `pkgs.mysql80`

### services.postgres.enable

Indique si le serveur PostgreSQL doit être activé.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.postgres.enableTcp

Indique si Postgres doit écouter sur TCP.

*Type :* booléen
*Par défaut :* `true`
*Exemple :* `true`

### services.postgres.package

Package PostgreSQL à utiliser.

*Type :* package
*Par défaut :* `pkgs.postgresql`
*Exemple :* `pkgs.postgresql_15`

### services.postgres.extensions

Extensions Postgres à installer.

*Type :* liste (une des valeurs suivantes : "age", "apache_datasketches", "cstore_fdw", "hypopg", "jsonb_deep_sum", "periods", "pg_auto_failover", "pg_bigm", "pg_cron", "pg_ed25519", "pg_embedding", "pg_hint_plan", "pg_hll", "pg_ivm", "pg_net", "pg_partman", "pg_rational", "pg_repack", "pg_safupdate", "pg_similarity", "pg_topn", "pg_uuidv7", "pgaudit", "pgjwt", "pgroonga", "pgrouting", "pgsql-http", "pgtap", "pgvector", "plpgsql_check", "plr", "plv8", "postgis", "promscale_extension", "repmgr", "rum", "smlar", "tds_fdw", "temporal_tables", "timescaledb", "timescaledb-apache", "timescaledb_toolkit", "tsearch_extras", "tsja", "wal2json")

*Par défaut :* `[ ]`
*Exemple :* `[ "pgvector" "postgis" ];`

### services.pubsub.enable

Indique si l'émulateur Google Cloud Pub/Sub doit être activé.

Pour en savoir plus sur l'utilisation de l'émulateur, consultez la page https://cloud.google.com/pubsub/docs/emulator#using_the_emulator .

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.pubsub.port

Configure le port sur lequel Pub/Sub écoutera.

*Type :* entier non signé de 16 bits, compris entre 0 et 65 535 (inclus)
*Par défaut :* `8085`

### services.pubsub.project-id

ID de projet à utiliser pour exécuter l'émulateur Pub/Sub. Ce projet est destiné aux tests uniquement. Il n'a pas besoin d'exister et n'est utilisé que localement.

*Type :* chaîne correspondant au modèle [a-z][a-z0-9-]{5,29}
*Par défaut :* `"idx-pubsub-emulator"`

### services.redis.enable

Indique si le serveur Redis doit être activé.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.redis.port

Configure le port sur lequel Redis écoutera.

Par défaut, le protocole TCP est désactivé et Redis n'écoute que sur /tmp/redis/redis.sock.

*Type :* entier non signé de 16 bits, compris entre 0 et 65 535 (inclus)
*Par défaut :* `0`

### services.spanner.enable

Indique si l'émulateur Google Cloud Spanner doit être activé.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.spanner.fault-injection

Indique s'il faut activer l'injection de pannes aléatoires dans les transactions.

*Type :* booléen
*Par défaut :* `false`
*Exemple :* `true`

### services.spanner.grpc-port

Port TCP auquel l'émulateur doit être lié.

*Type :* entier non signé de 16 bits, compris entre 0 et 65 535 (inclus)
*Par défaut :* `9010`

### services.spanner.rest-port

Port sur lequel les requêtes REST sont traitées

*Type :* entier non signé de 16 bits, compris entre 0 et 65 535 (inclus)
*Par défaut :* `9020`