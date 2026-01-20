# Services Dépréciés - Intégrations Obsolètes

Ce dossier contient les services pour les intégrations MySQL et Airtable qui ont été dépréciées.

**Date de dépréciation :** 2025-12-13

**Raison :** L'architecture a été simplifiée pour utiliser exclusivement Webhook comme source de données pour le monitoring des téléchargements.

## Services Déplacés

### `mysql_service.py`
Service d'intégration MySQL pour le monitoring des téléchargements.
- Connexion et gestion de pool MySQL
- Récupération des enregistrements depuis une table MySQL
- Cache intelligent avec TTL configurable

### `airtable_service.py`
Service d'intégration Airtable pour le monitoring des téléchargements.
- Authentification via Personal Access Token (PAT)
- Récupération des enregistrements depuis une base Airtable
- Support des champs personnalisés et validation

## Architecture Actuelle

Le système utilise désormais :
- **Source unique** : `WebhookService` - Endpoint JSON externe
- **Configuration** : `WEBHOOK_JSON_URL`, `WEBHOOK_MONITOR_INTERVAL`, `WEBHOOK_CACHE_TTL`
- **Monitoring** : Automatique au démarrage via thread dédié dans `app_new.py`

## Migration

Si vous utilisez encore MySQL ou Airtable :
1. Mettre en place un endpoint Webhook JSON retournant le format attendu
2. Configurer `WEBHOOK_JSON_URL` dans `.env`
3. Supprimer les anciennes variables d'environnement (`USE_MYSQL`, `USE_AIRTABLE`, etc.)
4. Redémarrer l'application

Pour plus d'informations, voir :
- `docs/workflow/WEBHOOK_INTEGRATION.md`
- `docs/workflow/CSV_DOWNLOADS_MANAGEMENT.md`

## Conservation

Ces fichiers sont conservés pour référence historique mais ne sont plus maintenus. Ils peuvent être supprimés dans une future version majeure.
