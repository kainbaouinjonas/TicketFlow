#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings


def check_python_version():
    """Vérifie que la version de Python est compatible"""
    if sys.version_info < (3, 10):
        warnings.warn(
            f"Python {sys.version_info.major}.{sys.version_info.minor} is not recommended. "
            "Please use Python 3.11 or 3.12 for production.",
            RuntimeWarning
        )
    elif sys.version_info >= (3, 14):
        warnings.warn(
            f"Python {sys.version_info.major}.{sys.version_info.minor} is an alpha/pre-release version. "
            "Some packages may not be compatible. Use Python 3.11 or 3.12 for production.",
            RuntimeWarning
        )


def main():
    """Run administrative tasks."""
    check_python_version()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()