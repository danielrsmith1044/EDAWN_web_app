from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Companies
    path('companies/',                      views.company_list,         name='company_list'),
    path('companies/<int:pk>/',             views.company_detail,       name='company_detail'),
    path('companies/<int:pk>/contact/',     views.log_contact_attempt,  name='log_contact_attempt'),
    path('companies/<int:pk>/visit/',       views.log_visit,            name='log_visit'),

    # Goals
    path('goals/',          views.goal_list,   name='goal_list'),
    path('goals/<int:pk>/', views.goal_detail, name='goal_detail'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
