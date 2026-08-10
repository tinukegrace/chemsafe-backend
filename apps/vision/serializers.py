from rest_framework import serializers


class LabelScanUploadSerializer(serializers.Serializer):
    # DRF's ImageField already runs a Pillow-based validity check as part of
    # to_internal_value — the view adds an explicit verify()+reopen pass on
    # top as defense in depth for a public file-upload endpoint.
    image = serializers.ImageField()


class LabelScanLinkSerializer(serializers.Serializer):
    chemical_id = serializers.UUIDField()
