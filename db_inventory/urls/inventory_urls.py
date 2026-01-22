from django.urls import path


from db_inventory.viewsets.asset_assignment import equipment_assignment
from db_inventory.viewsets.asset_assignment import accessory_assignnment
from db_inventory.viewsets.asset_assignment.consumable_assignment import AdminReturnConsumableView, ConsumableDistributionViewSet, ConsumableEventHistoryViewSet, IssueConsumableView, ReportConsumableLossView, RestockConsumableView, UseConsumableView


urlpatterns = [
    # Inventory Mnaagemnt URLSs
    
    path("equipment/<str:public_id>/events/", equipment_assignment.EquipmentEventHistoryViewset.as_view({"get": "list"}), name="equipment-event-history"),
    path("equipment/assign/", equipment_assignment.AssignEquipmentView.as_view(), name="assign-equipment"),
    path("equipment/unassign/", equipment_assignment.UnassignEquipmentView.as_view(), name="unassign-equipment"),
    path("equipment/reassign/",  equipment_assignment.ReassignEquipmentView.as_view(), name="reassign-equipment"),
    path("equipment/assignments/<str:equipment_id>/", equipment_assignment.EquipmentAssignmentViewSet.as_view({"get": "retrieve",}), name="equipment-assignment-detail",),
    path("equipment/assignments/",equipment_assignment.EquipmentAssignmentViewSet.as_view({"get": "list",}),name="equipment-assignment-list",),

    path("accessories/assign/", accessory_assignnment.AssignAccessoryView.as_view(), name="assign-accessory"),
    path("accessories/condemn/", accessory_assignnment.CondemnAccessoryView.as_view(), name="condemn-accessory"),
    path("accessories/return/", accessory_assignnment.AdminReturnAccessoryView.as_view(), name="return-accessory"),
    path("accessories/<str:public_id>/distribution/", accessory_assignnment.AccessoryDistributionView.as_view(),name="accessory-distribution",),

    path("inventory/accessories/<str:public_id>/events/", accessory_assignnment.AccessoryEventHistoryViewSet.as_view({"get": "list"}), name="accessory-event-history"),
    path("inventory/accessories/return/", accessory_assignnment.AdminReturnAccessoryView.as_view(), name="accessory-return"),
    path("inventory/accessories/restock/", accessory_assignnment.RestockAccessoryView.as_view(), name="accessory-restock"),
    path("inventory/accessories/use/", accessory_assignnment.UseAccessoryView.as_view(), name="use-accessory"),

    path("consumables/<str:public_id>/events/", ConsumableEventHistoryViewSet.as_view({"get": "list"}), name="consumable-event-history"),
    path("consumables/restock/", RestockConsumableView.as_view(), name="consumable-restock"),
    path("consumables/issue/", IssueConsumableView.as_view(), name="issue-consumable"),
    path("consumables/use/", UseConsumableView.as_view(), name="use-consumable"),
    path("consumables/return/", AdminReturnConsumableView.as_view(), name="return-consumable"),
    path("consumables/report-loss/", ReportConsumableLossView.as_view(), name="report-consumable-loss"),
    path("consumables/<str:public_id>/distribution/", ConsumableDistributionViewSet.as_view({"get": "list"}), name="consumable-distribution"),

]