from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from core.admin_views import admin_landing, teacher_overview, teacher_overview_export
from core.auth_views import PhoneOrUsernameTokenView
from core.guidance_views import guidance_workbench, teacher_workspace, feedback_editor, document_download

admin.site.site_header = "教研云管理后台"
admin.site.site_title = "教研云"
admin.site.index_title = "数据管理中心"

urlpatterns = [
    path("admin/teaching/", guidance_workbench, name="guidance_workbench"),
    path("admin/teaching/teachers/<int:profile_id>/", teacher_workspace, name="teacher_workspace"),
    path("admin/teaching/feedback/new/", feedback_editor, name="teaching_feedback_new"),
    path("admin/teaching/feedback/<int:feedback_id>/edit/", feedback_editor, name="teaching_feedback_edit"),
    path("admin/teaching/documents/<str:kind>/<int:object_id>/download/", document_download, name="teaching_document_download"),
    path("admin/overview/", teacher_overview, name="teacher_overview"),
    path("admin/overview/export/", teacher_overview_export, name="teacher_overview_export"),
    path("admin/", admin.site.admin_view(admin_landing)),
    path("admin/", admin.site.urls),
    path("api/auth/token/", PhoneOrUsernameTokenView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.urls")),
    path("api/", include("learning.urls")),
    path("api/", include("community.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
