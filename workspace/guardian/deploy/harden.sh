#!/usr/bin/env bash
# Séparation des privilèges sur la machine du Grok Bot (Debian 13).
# À exécuter en SSH comme box (qui a encore sudo) :
#   bash deploy/harden.sh "ssh-ed25519 AAAA... quentin@mac"
#
# Fait (idempotent) :
#   1. utilisateur admin  : ta clé SSH, sudo complet         -> ton canal d'administration
#   3. utilisateur guardian : possède /workspace/guardian    -> le bot ne peut plus lire clé/env/état
#   5. sudoers chirurgical : box peut UNIQUEMENT relancer run.sh en tant que guardian (watchdog)
# N'exécute PAS l'étape 4 (retrait du sudo de box) : elle est affichée à la fin,
# à lancer À LA MAIN après avoir vérifié une connexion SSH admin fonctionnelle.
set -euo pipefail

PUBKEY="${1:-}"
[[ -n "$PUBKEY" ]] || { echo "Usage : harden.sh \"<ta clé publique SSH>\""; exit 64; }
ROOT="/workspace/guardian"
[[ -d "$ROOT" ]] || { echo "$ROOT introuvable"; exit 1; }

# --- 1. admin -----------------------------------------------------------------
if ! id admin &>/dev/null; then
    sudo useradd -m -s /bin/bash admin
fi
sudo install -d -m 700 -o admin -g admin /home/admin/.ssh
echo "$PUBKEY" | sudo tee /home/admin/.ssh/authorized_keys >/dev/null
sudo chown admin:admin /home/admin/.ssh/authorized_keys
sudo chmod 600 /home/admin/.ssh/authorized_keys
echo "admin ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/10-admin >/dev/null
sudo chmod 440 /etc/sudoers.d/10-admin
sudo visudo -cf /etc/sudoers.d/10-admin >/dev/null

# --- 3. guardian --------------------------------------------------------------
if ! id guardian &>/dev/null; then
    sudo useradd -r -m -s /usr/sbin/nologin guardian
fi
# le gardien doit être arrêté avant le transfert de propriété
if [[ -f "$ROOT/guardian.pid" ]] && kill -0 "$(cat "$ROOT/guardian.pid")" 2>/dev/null; then
    echo "Gardien actif : bash $ROOT/deploy/run.sh stop, puis relancer harden.sh"; exit 1
fi
sudo chown -R guardian:guardian "$ROOT"
sudo chmod 700 "$ROOT"
sudo chmod 600 "$ROOT/.env" 2>/dev/null || true
sudo chmod 600 "$ROOT/private.pem" 2>/dev/null || true
sudo find "$ROOT/deploy" -type f -name "*.sh" -exec chmod 755 {} \;

# --- 5. sudoers watchdog ------------------------------------------------------
echo "box ALL=(guardian) NOPASSWD: $ROOT/deploy/run.sh" | sudo tee /etc/sudoers.d/20-box-watchdog >/dev/null
sudo chmod 440 /etc/sudoers.d/20-box-watchdog
sudo visudo -cf /etc/sudoers.d/20-box-watchdog >/dev/null

echo "--------------------------------------------------------------------------"
echo "1, 3, 5 : OK."
echo "Démarrage du gardien désormais : sudo -u guardian bash $ROOT/deploy/run.sh"
echo "Watchdog côté bot            : sudo -u guardian $ROOT/deploy/run.sh"
echo ""
echo "ÉTAPE 2 — STOP : depuis ton Mac, vérifie MAINTENANT :"
echo "    ssh admin@<machine>   puis   sudo -n true && echo SUDO_OK"
echo ""
echo "ÉTAPE 4 — seulement après le STOP, exécute À LA MAIN (en admin) :"
echo "    sudo rm -f /etc/sudoers.d/*box* ; sudo gpasswd -d box sudo 2>/dev/null ;"
echo "    sudo sed -i 's/^box .*//' /etc/sudoers 2>/dev/null ; sudo visudo -c"
echo "    (garde /etc/sudoers.d/20-box-watchdog : c'est la seule capacité restante de box)"
echo "--------------------------------------------------------------------------"
