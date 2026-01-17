from rest_framework import serializers

from db_inventory.models.users import User
from db_inventory.models.assets import Accessory, Consumable, Equipment, EquipmentStatus
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent, ConsumableEvent, ConsumableIssue, EquipmentAssignment, EquipmentEvent



class ConsumableEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField( source="user.email", read_only=True, allow_null=True, )
    reported_by = serializers.EmailField( source="reported_by.email", read_only=True, allow_null=True, )
    issue_id = serializers.IntegerField(source="issue.id", read_only=True)

    class Meta:
        model = ConsumableEvent
        fields = [
            "id",
            "event_type",
            "quantity",
            "quantity_change",
            "issue_id",
            "user_email",
            "reported_by",
            "notes",
            "occurred_at",
        ]
        read_only_fields = fields

class EquipmentAssignmentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.CharField(source='equipment.public_id', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    user_id = serializers.CharField(source='user.public_id', read_only=True)
    user_name = serializers.CharField(source="user.get_full_name",read_only=True)

    assigned_by = serializers.StringRelatedField()

    class Meta:
        model = EquipmentAssignment
        fields = [
            "id",
            "equipment_id",
            "equipment_name",
            "user_id",
            "user_name",
            "assigned_at",
            "returned_at",
            "assigned_by",
            "notes",
        ]



class AssignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(public_id=attrs["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "User not found"})

        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError({"equipment_id": "Equipment not found"})

        # State-based business rules
        if equipment.is_assigned:
            raise serializers.ValidationError(
                "This equipment is already assigned"
            )

        if equipment.status in {
            EquipmentStatus.LOST,
            EquipmentStatus.RETIRED,
        }:
            raise serializers.ValidationError(
                "This equipment cannot be assigned in its current state"
            )

        # Attach resolved objects
        attrs["user"] = user
        attrs["equipment"] = equipment
        return attrs

class UnassignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Resolve user
        try:
            user = User.objects.get(public_id=attrs["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "User not found"})

        # Resolve equipment
        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError({"equipment_id": "Equipment not found"})

        # Must be assigned
        if not equipment.is_assigned:
            raise serializers.ValidationError(
                "This equipment is not currently assigned"
            )

        # Attach resolved objects
        attrs["equipment"] = equipment
        attrs["user"] = user
        return attrs
    
class ReassignEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.CharField(max_length=15)
    from_user_id = serializers.CharField(max_length=15)
    to_user_id = serializers.CharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["from_user_id"] == attrs["to_user_id"]:
            raise serializers.ValidationError(
                "from_user_id and to_user_id cannot be the same"
            )

        try:
            equipment = Equipment.objects.get(public_id=attrs["equipment_id"])
        except Equipment.DoesNotExist:
            raise serializers.ValidationError(
                {"equipment_id": "Equipment not found"}
            )

        try:
            from_user = User.objects.get(public_id=attrs["from_user_id"])
            to_user = User.objects.get(public_id=attrs["to_user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user")

        if not equipment.is_assigned:
            raise serializers.ValidationError("This equipment is not currently assigned")

        attrs.update({
            "equipment": equipment,
            "from_user": from_user,
            "to_user": to_user,
        })
        return attrs


class EquipmentEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    reported_by_email = serializers.EmailField(
        source="reported_by.email", read_only=True
    )

    class Meta:
        model = EquipmentEvent
        fields = [
            "id",
            "event_type",
            "occurred_at",
            "user",
            "user_email",
            "reported_by",
            "reported_by_email",
            "notes",
        ]

class AssignAccessorySerializer(serializers.Serializer):
    accessory = serializers.SlugRelatedField(slug_field="public_id",queryset=Accessory.objects.all())
    user = serializers.SlugRelatedField(slug_field="public_id",queryset=User.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)

class AdminReturnAccessorySerializer(serializers.Serializer):
    assignment = serializers.PrimaryKeyRelatedField(queryset=AccessoryAssignment.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    def validate(self, attrs):
        assignment = attrs["assignment"]

        if assignment.returned_at is not None:
            raise serializers.ValidationError(
                "This assignment is already closed"
            )

        return attrs

class SelfReturnAccessorySerializer(serializers.Serializer):
    accessory = serializers.SlugRelatedField(slug_field="public_id",queryset=Accessory.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class CondemnAccessorySerializer(serializers.Serializer):
    accessory = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Accessory.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class AccessoryEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    reported_by_email = serializers.EmailField( source="reported_by.email", read_only=True )

    quantity_display = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    action_label = serializers.SerializerMethodField()

    class Meta:
        model = AccessoryEvent
        fields = [
            "id",
            "event_type",
            "action_label",
            "occurred_at",
            "quantity_change",
            "quantity",
            "quantity_display",
            "user",
            "user_email",
            "reported_by",
            "reported_by_email",
            "notes",
        ]

    def get_quantity(self, obj):
        """
        Human-meaningful quantity involved in the action
        (assigned / returned / condemned / restocked).
        """
        if hasattr(obj, "quantity") and obj.quantity is not None:
            return obj.quantity

        # Safety fallback for legacy rows (optional)
        if obj.quantity_change:
            return abs(obj.quantity_change)

        return None

    def get_quantity_display(self, obj):
        """
        Stock impact display (+ / -), kept for inventory context.
        """
        if obj.quantity_change == 0:
            return None
        sign = "+" if obj.quantity_change > 0 else ""
        return f"{sign}{obj.quantity_change}"

    def get_action_label(self, obj):
        return {
            "assigned": "Assigned",
            "returned": "Returned",
            "condemned": "Condemned",
            "restocked": "Restocked",
            "adjusted": "Adjusted",
        }.get(obj.event_type, obj.event_type.replace("_", " ").title())
    

class IssueConsumableSerializer(serializers.Serializer):
    consumable = serializers.SlugRelatedField(slug_field="public_id",queryset=Consumable.objects.all())
    user = serializers.SlugRelatedField(slug_field="public_id",queryset=User.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

class UseConsumableSerializer(serializers.Serializer):
    consumable = serializers.SlugRelatedField(slug_field="public_id",queryset=Consumable.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)

class ReturnConsumableSerializer(serializers.Serializer):
    issue = serializers.PrimaryKeyRelatedField(queryset=ConsumableIssue.objects.select_related("consumable", "user"))
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)

class ReportConsumableLossSerializer(serializers.Serializer):
    consumable = serializers.SlugRelatedField(slug_field="public_id",queryset=Consumable.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    event_type = serializers.ChoiceField(
        choices=[
            ConsumableEvent.EventType.LOST,
            ConsumableEvent.EventType.DAMAGED,
            ConsumableEvent.EventType.EXPIRED,
            ConsumableEvent.EventType.CONDEMNED,
        ]
    )
    notes = serializers.CharField(required=False, allow_blank=True)