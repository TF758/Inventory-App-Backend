from rest_framework import serializers

class ExtendAgreementSerializer( serializers.Serializer ):

    new_expiry_date = ( serializers.DateField() )

    reason = (
        serializers.CharField(
            required=False,
            allow_blank=True,
        )
    )

class ExtendAgreementSerializer( serializers.Serializer ):

    new_expiry_date = (
        serializers.DateField()
    )

    reason = (
        serializers.CharField(
            required=False,
            allow_blank=True,
        )
    )

class RenewAgreementSerializer(
    serializers.Serializer,
):

    new_expiry_date = (
        serializers.DateField()
    )

    new_renewal_date = (
        serializers.DateField(
            required=False,
            allow_null=True,
        )
    )

    reason = (
        serializers.CharField(
            required=False,
            allow_blank=True,
        )
    )