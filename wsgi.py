"""WSGI entry point for Waitress and Flask administration commands."""
from app import create_app

app = create_app()
