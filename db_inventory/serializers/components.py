from rest_framework import serializers
from db_inventory.models.assets import Component



class ComponentSerializer(serializers.ModelSerializer):
    # Reference to associated equipment
    equipment_id = serializers.CharField(source='equipment.public_id', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    # Optional area info (room -> location -> department)
    area_id = serializers.SerializerMethodField()
    area_type = serializers.SerializerMethodField()
    area_name = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            'public_id',
            'name',
            'brand',
            'model',
            'serial_number',
            'quantity',
            'equipment',
            'equipment_id',
            'equipment_name',
            'area_id',
            'area_type',
            'area_name',
        ]

    def get_area_id(self, obj):
        if obj.equipment and obj.equipment.room:
            room = obj.equipment.room
            if room.location and room.location.department:
                # Return department id
                return room.location.department.public_id
            return room.location.public_id if room.location else room.public_id
        return None

    def get_area_type(self, obj):
        if obj.equipment and obj.equipment.room:
            room = obj.equipment.room
            if room.location and room.location.department:
                return "department"
            if room.location:
                return "location"
            return "room"
        return None

    def get_area_name(self, obj):
        if obj.equipment and obj.equipment.room:
            room = obj.equipment.room
            if room.location and room.location.department:
                return room.location.department.name
            if room.location:
                return room.location.name
            return room.name
        return "N/A" 


  # Write Serializer


class ComponentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = [
            'public_id',
            'name',
            'brand',
            'quantity',
            'model',
            'serial_number',
            'equipment',
        ]


  
__all__ = [
    'ComponentWriteSerializer',
    'ComponentSerializer'
]