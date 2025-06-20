from django.urls import path
from . import views

app_name = 'friendly_games'

urlpatterns = [
    path('create/', views.create_game, name='create_game'),
    path('<int:game_id>/', views.game_detail, name='game_detail'),
    path('join/', views.join_game, name='join_game'),
    path('<int:game_id>/start/', views.start_match, name='start_match'),
    path('<int:game_id>/submit-score/', views.submit_score, name='submit_score'),
    path('<int:game_id>/validate-result/', views.validate_result, name='validate_result'),
]

