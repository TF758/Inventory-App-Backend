from rest_framework import serializers

from sites.models.sites import Department, Location, Room

class SiteNameChangeSerializer(serializers.Serializer):
    SITE_CHOICES = (
        ("department", "department"),
        ("location", "location"),
        ("room", "room"),
    )

    site_type = serializers.ChoiceField(choices=SITE_CHOICES)
    public_id = serializers.CharField()
    new_name = serializers.CharField(max_length=255)
    reason = serializers.CharField()

    def validate_new_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("New name cannot be blank.")
        return value

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Reason is required.")
        return value

    def validate(self, attrs):
        model_map = {
            "department": Department,
            "location": Location,
            "room": Room,
        }

        model = model_map[attrs["site_type"]]

        try:
            obj = model.objects.get(public_id=attrs["public_id"])
        except model.DoesNotExist:
            raise serializers.ValidationError({
                "public_id": "Site not found."
            })

        if obj.name == attrs["new_name"]:
            raise serializers.ValidationError({
                "new_name": "Name is unchanged."
            })

        attrs["target_obj"] = obj
        return attrs
    
class SiteRelocationSerializer(serializers.Serializer):
    SITE_CHOICES = (
        ("location", "location"),
        ("room", "room"),
    )

    TARGET_CHOICES = (
        ("department", "department"),
        ("location", "location"),
    )

    site_type = serializers.ChoiceField(choices=SITE_CHOICES)
    object_public_id = serializers.CharField()
    target_site = serializers.ChoiceField(choices=TARGET_CHOICES)
    target_public_id = serializers.CharField()
    reason = serializers.CharField()

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Reason is required.")
        return value

    def validate(self, attrs):
        site_type = attrs["site_type"]
        target_site = attrs["target_site"]

        if site_type == "location" and target_site != "department":
            raise serializers.ValidationError({
                "target_site": "Locations can only move under a department."
            })

        if site_type == "room" and target_site != "location":
            raise serializers.ValidationError({
                "target_site": "Rooms can only move under a location."
            })

        return attrs