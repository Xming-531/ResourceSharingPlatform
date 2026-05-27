"""
Legacy template views kept for compatibility.

Your Vue SPA should call JSON APIs in `users/api.py` via `/api/...`.
"""

from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render

from users import models
