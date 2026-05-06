from django.urls import path
from . import views

urlpatterns = [
    # Landing page (public)
    path('about/', views.landing, name='landing'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Staff portal
    path('staff/',             views.staff_dashboard,  name='staff_dashboard'),
    path('staff/volunteers/',  views.staff_volunteers, name='staff_volunteers'),
    path('staff/import/',                          views.staff_import_csv,         name='staff_import_csv'),
    path('staff/expansion-signals/',               views.staff_expansion_signals,   name='staff_expansion_signals'),
    path('staff/volunteers/<int:pk>/training/',    views.staff_mark_training,       name='staff_mark_training'),
    path('staff/volunteers/<int:pk>/bbv/',          views.staff_mark_bbv,            name='staff_mark_bbv'),
    path('staff/volunteers/<int:pk>/temp-password/', views.staff_set_temp_password,  name='staff_set_temp_password'),
    path('staff/add-company/', views.quick_add_company, name='staff_add_company'),
    path('staff/assign/',      views.quick_assign,      name='staff_assign'),
    path('staff/invite/',      views.quick_invite,      name='staff_invite'),
    path('staff/create-admin/', views.create_admin,          name='staff_create_admin'),
    path('staff/export/',       views.staff_export_visits,   name='staff_export_visits'),
    path('staff/requests/',     views.staff_requests,        name='staff_requests'),
    path('staff/requests/<int:pk>/approve/', views.staff_approve_request, name='staff_approve_request'),
    path('staff/requests/<int:pk>/deny/',    views.staff_deny_request,    name='staff_deny_request'),
    path('staff/notices/',               views.staff_notices,       name='staff_notices'),
    path('staff/notices/new/',           views.staff_notice_form,   name='staff_notice_create'),
    path('staff/notices/<int:pk>/edit/', views.staff_notice_form,   name='staff_notice_edit'),
    path('staff/notices/<int:pk>/delete/', views.staff_notice_delete, name='staff_notice_delete'),
    path('staff/guide/',                   views.staff_guide,          name='staff_guide'),
    path('volunteer-guide/',               views.volunteer_guide,      name='volunteer_guide'),

    # Resources
    path('resources/',                   views.resource_list,   name='resource_list'),
    path('resources/new/',               views.resource_form,   name='resource_add'),
    path('resources/<int:pk>/edit/',     views.resource_form,   name='resource_edit'),
    path('resources/<int:pk>/delete/',   views.resource_delete, name='resource_delete'),

    # Companies
    path('companies/',                                        views.company_list,        name='company_list'),
    path('companies/<int:pk>/',                               views.company_detail,      name='company_detail'),
    path('companies/<int:pk>/contact/',                       views.log_contact_attempt, name='log_contact_attempt'),
    path('companies/<int:pk>/visit/',                         views.log_visit,           name='log_visit'),
    path('companies/<int:pk>/visit/<int:note_pk>/edit/',      views.edit_visit_note,     name='edit_visit_note'),

    # Badges
    path('badges/', views.badge_list, name='badge_list'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Messages
    path('messages/',              views.message_list,   name='message_list'),
    path('messages/new/',          views.message_create,  name='message_create'),
    path('messages/<int:pk>/',     views.message_detail,  name='message_detail'),
]
