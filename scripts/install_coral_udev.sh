#!/bin/bash
# install_coral_udev.sh
# Script d'installation automatique des règles udev et permissions pour le Google Coral TPU (PCIe M.2 et USB)

set -e

echo "[Coral TPU] Démarrage de l'installation des permissions système..."

# 1. Vérifier si le groupe plugdev existe, sinon le créer
if ! getent group plugdev > /dev/null; then
    echo "[Coral TPU] Création du groupe 'plugdev'..."
    sudo groupadd plugdev
else
    echo "[Coral TPU] Le groupe 'plugdev' existe déjà."
fi

# 2. Ajouter l'utilisateur courant au groupe plugdev
if ! groups "$USER" | grep -q "\bplugdev\b"; then
    echo "[Coral TPU] Ajout de l'utilisateur $USER au groupe 'plugdev'..."
    sudo usermod -aG plugdev "$USER"
else
    echo "[Coral TPU] L'utilisateur $USER appartient déjà au groupe 'plugdev'."
fi

# 3. Créer le fichier de règles udev pour le Coral TPU
UDEV_RULE_FILE="/etc/udev/rules.d/99-coral-tpu.rules"
echo "[Coral TPU] Configuration des règles udev dans $UDEV_RULE_FILE..."

# Utiliser un fichier temporaire pour construire les règles
TMP_RULE=$(mktemp)
cat << 'EOF' > "$TMP_RULE"
# Règles UDEV pour Google Coral Edge TPU
# PCIe M.2 (Pilote gasket/apex)
SUBSYSTEM=="apex", MODE="0660", GROUP="plugdev"

# USB Edge TPU
SUBSYSTEM=="usb", ATTR{idVendor}=="1a6e", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", GROUP="plugdev"
EOF

# Vérifier si les règles existent déjà ou si on doit les écraser
if [ -f "$UDEV_RULE_FILE" ] && cmp -s "$TMP_RULE" "$UDEV_RULE_FILE"; then
    echo "[Coral TPU] Les règles udev sont déjà à jour."
else
    sudo cp "$TMP_RULE" "$UDEV_RULE_FILE"
    sudo chmod 644 "$UDEV_RULE_FILE"
    echo "[Coral TPU] Règles udev mises à jour. Rechargement des règles..."
    sudo udevadm control --reload-rules
    sudo udevadm trigger
fi

rm -f "$TMP_RULE" || true

echo "[Coral TPU] Vérification du noeud /dev/apex_0..."
if [ -c /dev/apex_0 ]; then
    ls -l /dev/apex_0
else
    echo "[Coral TPU] AVERTISSEMENT : Le noeud /dev/apex_0 n'existe pas actuellement."
    echo "Assurez-vous que le TPU M.2 est branché et que le pilote gasket-driver est chargé."
fi

echo "[Coral TPU] Installation terminée avec succès."
echo "NOTE : Si vous venez d'être ajouté au groupe plugdev, vous devrez peut-être vous déconnecter/reconnecter pour que le changement prenne effet."
