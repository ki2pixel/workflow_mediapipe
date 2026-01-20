# Tests Legacy - Intégrations Obsolètes

Ce dossier contient les tests pour les intégrations MySQL et Airtable qui ont été dépréciées.

**Date de dépréciation :** 2025-12-13

**Raison :** L'architecture a été simplifiée pour utiliser exclusivement Webhook comme source de données.

## Fichiers Déplacés

- `test_mysql_integration.py` - Tests d'intégration MySQL
- `test_mysql_service.py` - Tests unitaires du service MySQL
- `test_mysql_validation.py` - Tests de validation MySQL

Ces tests sont conservés pour référence historique mais ne sont plus maintenus ni exécutés dans la suite de tests principale.

## Architecture Actuelle

Le système utilise désormais :
- **Source unique** : Webhook JSON externe
- **Monitoring** : Automatique au démarrage
- **Configuration** : `WEBHOOK_JSON_URL` dans `.env`

Pour plus d'informations, voir `docs/workflow/WEBHOOK_INTEGRATION.md`.
