from django.urls import path, include

"""
API URL structure:

- CRUD inventory records: /equipments, /accessories, /consumables
- Inventory operations (assign, use, restock, events): /inventory/...
- phsyical site structure: /departments, /locations, /rooms
"""

urlpatterns = [

    # ----------------------------
    # Core Modules
    # ----------------------------
    path("self/", include("users.urls.self_profile_urls")),
    path("", include("users.urls.users_urls")),

]