from django.urls import path
from ..views import *


urlpatterns = [
path('', room_list_create_view, name='rooms'),
path('list/', room_list_view, name='rooms-list'),
path('<str:public_id>/', room_id_detail_view, name='room-detail'),

# Full endpoints
path('<str:public_id>/users/', room_users_view, name='room-users'),
path('<str:public_id>/equipment/', room_equipment_view, name='room-equipment'),
path('<str:public_id>/consumables/', room_consumables_view, name='room-consumables'),
path('<str:public_id>/accessories/', room_accessories_view, name='room-accessories'),
path('<str:public_id>/components/', room_components_view, name='room-components'),

# Light endpoints
path('<str:public_id>/users-light/', room_users_light_view, name='room-users-light'),
path('<str:public_id>/equipment-light/', room_equipment_light_view, name='room-equipment-light'),
path('<str:public_id>/consumables-light/', room_consumables_light_view, name='room-consumables-light'),
path('<str:public_id>/accessories-light/', room_accessories_light_view, name='room-accessories-light'),
path('<str:public_id>/components-light/', room_components_light_view, name='room-components-light'),
]