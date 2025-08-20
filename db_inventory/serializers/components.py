from rest_framework import serializers
from ..models import Component
from .equipment import EquipmentNameSerializer

  


  # Write Serializer


class ComponentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'quantity',
            'model',
            'serial_number',
            'equipment',
        ]

# Read Serializer
class ComponentReadSerializer(serializers.ModelSerializer):
    equipment = EquipmentNameSerializer( read_only=True)

    class Meta:
        model = Component
        fields = [
            'id',
            'identifier',
            'name',
            'brand',
            'quantity',
            'model',
            'serial_number',
            'equipment',
            
        ]
  
__all__ = [
    'ComponentWriteSerializer',
    'ComponentReadSerializer',
]