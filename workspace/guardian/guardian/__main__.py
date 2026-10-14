"""Point d'entrée : python -m guardian"""
from __future__ import annotations

import logging
import signal
import sys

from .api import Mailbox, serve
from .bitvavo import BitvavoClient
from .config import load_settings
from .revolutx import RevolutXClient
from .guardian import Guardian, Halt
from .state import Journal, State


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("main")
    settings = load_settings()

    if settings.exchange == "revolutx":
        client = RevolutXClient(settings.revx_key, settings.revx_private_key_path)
    else:
        client = BitvavoClient(settings.bitvavo_key, settings.bitvavo_secret)
    state = State.load_or_create(settings.state_path, settings.game_start)
    journal = Journal(settings.journal_path)

    if not state.alive:
        log.error("L'état indique une mort constatée. Rien à faire.")
        return 43

    mailbox = Mailbox(token=settings.api_token)
    server = serve(mailbox, settings.api_host, settings.api_port)
    guardian = Guardian(settings, client, state, journal, mailbox)
    guardian.startup_checks()

    def _stop(signum, _frame):
        log.info("Signal %s reçu : arrêt propre", signum)
        state.save(settings.state_path)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    journal.write("startup", state.score, "-", f"start:{settings.mode}")
    try:
        guardian.run()
    except Halt as h:
        log.warning("Arrêt : %s", h)
        journal.write("halt", state.score, "-", "halt", "-", "-", "-", str(h))
        return 42
    return 0


if __name__ == "__main__":
    sys.exit(main())
