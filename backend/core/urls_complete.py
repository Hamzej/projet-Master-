"""
backend/core/urls_complete.py
Clean production-ready API routing (aligned with optimized views)
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ViewSets principaux
from .views_optimized import StudentViewSet, AttendanceViewSet

# Auth views
from .auth_views import (
    LoginView,
    LogoutView,
    RegisterView,
    RefreshTokenView,
    MeView
)

# ======================
# ROUTER DRF
# ======================
router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'attendance', AttendanceViewSet, basename='attendance')

# ======================
# URL PATTERNS
# ======================
urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API ROOT
    path('api/', include(router.urls)),

    # AUTH API
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('api/auth/me/', MeView.as_view(), name='me'),

    # DRF Login (Browsable API)
    path('api-auth/', include('rest_framework.urls')),
]
# ======================
# MEDIA FILES (DEBUG MODE)
# ======================
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)