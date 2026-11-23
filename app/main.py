"""Punto de entrada ASGI.

Ejecutar: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import logging
import os

from app.bootstrap import build_app

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
app = build_app(os.getenv("REDIS_URL"), os.getenv("DATABASE_URL"))
