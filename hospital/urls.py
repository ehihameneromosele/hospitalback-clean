# hospital/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentCreateView, AppointmentListView, AppointmentDetailView,
    AssignmentViewSet, AppointmentAssignmentsView,
    AvailableStaffView,
    AssignStaffView, PatientListView,
    VitalRequestCreateView, VitalRequestListView,
    VitalsCreateView, LabResultCreateView, TestRequestListView, MedicalReportCreateView,
    StaffListView,
    BlogCategoryListView,
    BlogPostLatestView, BlogPostListCreateView,
    BlogPostRetrieveUpdateDestroyView, BlogPostSearchView,
    BlogPostSuggestView,
    AdminBlogPostListView, BlogPostByAuthorView, BlogStatsView,
)

router = DefaultRouter()
router.register(r'assignments', AssignmentViewSet, basename='assignment')

urlpatterns = [
    # ── Appointments ──────────────────────────────────────────────────────────
    path('appointments/',          AppointmentListView.as_view(),   name='appointment-list'),
    path('appointments/create/',   AppointmentCreateView.as_view(), name='appointment-create'),
    path('appointments/<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),

    # ── Assignments ───────────────────────────────────────────────────────────
    path('assignments/available-staff/',
         AvailableStaffView.as_view(), name='available-staff'),
    path('assignments/assign-staff/',
         AssignStaffView.as_view(), name='assign-staff'),
    path('assignments/appointment/<int:appointment_id>/',
         AppointmentAssignmentsView.as_view(), name='appointment-assignments'),
    path('', include(router.urls)),

    # ── Staff / Patients ──────────────────────────────────────────────────────
    path('staff/',    StaffListView.as_view(),   name='staff-list'),
    path('patients/', PatientListView.as_view(), name='patient-list'),

    # ── Clinical ──────────────────────────────────────────────────────────────
    path('vital-requests/',        VitalRequestListView.as_view(),   name='vital-request-list'),
    path('vital-requests/create/', VitalRequestCreateView.as_view(), name='vital-request-create'),
    path('vitals/create/',         VitalsCreateView.as_view(),       name='vitals-create'),
    path('lab-results/create/',    LabResultCreateView.as_view(),    name='lab-result-create'),
    path('medical-reports/create/', MedicalReportCreateView.as_view(), name='medical-report-create'),
    path('test-requests/',         TestRequestListView.as_view(),    name='test-request-list'),

    # ── Blog ──────────────────────────────────────────────────────────────────
    # NOTE: Exact paths MUST come before the slug catch-all.
    path('blog/categories/',                BlogCategoryListView.as_view(),            name='blog-categories'),
    path('blog/latest/',                    BlogPostLatestView.as_view(),              name='blog-latest'),
    path('blog/search/',                    BlogPostSearchView.as_view(),              name='blog-search'),
    path('blog/suggest/',                   BlogPostSuggestView.as_view(),             name='blog-suggest'),
    path('blog/admin/stats/',               BlogStatsView.as_view(),                   name='blog-stats'),
    path('blog/admin/all/',                 AdminBlogPostListView.as_view(),           name='blog-admin-all'),
    path('blog/author/<int:author_id>/',    BlogPostByAuthorView.as_view(),            name='blog-by-author'),
    path('blog/',                           BlogPostListCreateView.as_view(),          name='blog-list-create'),
    path('blog/<slug:slug>/',               BlogPostRetrieveUpdateDestroyView.as_view(), name='blog-detail'),
]