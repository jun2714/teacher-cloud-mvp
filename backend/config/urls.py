from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from core.admin_views import teacher_overview
from core.auth_views import PhoneOrUsernameTokenView

admin.site.site_header = "教研云管理后台"
admin.site.site_title = "教研云"
admin.site.index_title = "数据管理中心"

urlpatterns = [
    path("admin/overview/", teacher_overview),
    path("admin/", admin.site.urls),
    path("api/auth/token/", PhoneOrUsernameTokenView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.urls")),
    path("api/", include("learning.urls")),
    path("api/", include("community.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
