# Contexte Actif (Active Context)

## Tâche en Cours
- Aucune tâche active.

## Dernière Session Clôturée
- [2026-07-15 11:31:24] Optimisation STEP5 CV5 terminée : pool global adaptatif d'inférence par chunks, budget CPU de 15 workers, écriture atomique des sorties et maintien de l'ordre pour le filtre temporel et le tracking.
- Dissociation effectuée entre le mode CPU CV5 et les variables GPU InsightFace : `STEP5_CV5_INFERENCE_DEVICE=cpu` laisse le pool CV5 utiliser le budget CPU, tandis que `cuda` force ONNX Runtime CUDA et un seul worker pour protéger la VRAM.
- Variables de planification CV5 ajoutées dans `.env` et `.env.example`.
- Validation : 460 tests backend réussis, 28 ignorés ; tests ciblés CV5 et commandes réussis ; compilation, lint fatal et typecheck ciblé réussis.

## Prochaine Action
- Aucune action planifiée.
