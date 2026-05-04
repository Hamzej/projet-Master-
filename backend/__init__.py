"""
Smart Attendance System - Initialisation du module Django
Ce fichier configure l'application principale et active PyMySQL
comme driver MySQL pour Django.

Version: 1.0.0
Auteur: Hamze
"""

import pymysql

# Permet à Django d'utiliser PyMySQL comme remplacement de mysqlclient
pymysql.install_as_MySQLdb()

# Tu peux aussi définir des métadonnées globales
__version__ = "1.0.0"
__author__ = "Hamze"
__all__ = []
