from django.urls import path
from ..views import *


urlpatterns = [
path('',room_list_create_view, name='rooms'),
path('<str:public_id>/', room_id_detail_view , name='room-detail'),

path('<str:public_id>/users/', room_users_view, name='room-users'),
# path('rooms/<int:room_id>/users-dashboard/', room_users_dashboard_view, name='room-users-dashboard'),

path('<str:public_id>/equipment/', room_equipment_view, name='room-equipment'),
# path('rooms/<int:room_id>/equipment-dashboard/', room_equipment_dashboard_view, name='room-equipment-dashboard'),

path('<str:public_id>/consumables/', room_consumables_view, name='room-consumables'),
# path('rooms/<int:room_id>/consumables-dashboard/', room_consumables_dashboard_view, name='room-consumables-dashboard'),

path('<str:public_id>/accessories/', room_accessories_view, name='room-accessories'),
# path('rooms/<int:room_id>/accessories-dashboard/', room_accessories_dashboard_view, name='room-accessories-dashboard'),

path('<str:public_id>/components/', room_components_view, name='room-components'),
# path('rooms/<int:room_id>/components-dashboard/', room_components_dashboard_view, name='room-components-dashboard'),
]