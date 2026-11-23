"""game_engine: el corazón del juego (ADR-01, particionamiento por dominio).

Submódulos: deck_card (Deck & Card), rule_engine (Rule Engine),
game_session (Game Session) y orchestrator (Turn & Timer).
Ninguno depende de FastAPI, Redis, SQLAlchemy ni de app.infrastructure (.importlinter).
"""
