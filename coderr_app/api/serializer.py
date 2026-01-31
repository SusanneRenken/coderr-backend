"""Serializers for coderr_app.

This module contains serializers for creating/updating offers, orders and
reviews. Most validation (for example: exactly three OfferDetail entries
with unique offer_type values) happens here to keep models thin.
"""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from coderr_app.models import Offer, OfferDetail, Order, Review
from django.contrib.auth.models import User

# --- CREATE and UPDATE SERIALIZERS ---


class OfferDetailItemNestedSerializer(serializers.ModelSerializer):
    """Nested serializer used when creating/updating Offer details.

    It applies simple min-value validation and requires a non-empty
    features list; `offer_type` is mandatory for creation.
    """

    revisions = serializers.IntegerField(min_value=0)
    delivery_time_in_days = serializers.IntegerField(min_value=1)
    price = serializers.IntegerField(min_value=0)
    features = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )

    class Meta:
        model = OfferDetail
        fields = [
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'offer_type': {'required': True}
        }


class OfferSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating an Offer with nested details.

    The validate() method enforces exactly three detail items on creation
    and prevents duplicate `offer_type` values on update.
    """

    image = serializers.FileField(required=False, allow_null=True)
    details = OfferDetailItemNestedSerializer(many=True, required=False)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']
        read_only_fields = ['id']

    def validate(self, attrs):
        # On create require exactly three details (basic, standard, premium)
        if self.instance is None:
            details = attrs.get('details')
            if not details or len(details) != 3:
                raise serializers.ValidationError(
                    "Exactly 3 details must be provided.")
            required = {'basic', 'standard', 'premium'}
            types = [d.get('offer_type') for d in details]
            if set(types) != required or len(types) != len(set(types)):
                raise serializers.ValidationError(
                    "Each offer_type (basic, standard, premium) must appear exactly once."
                )
        else:
            # On update, if details are provided ensure no duplicate types
            details = attrs.get('details')
            if details:
                # Ensure each provided detail includes offer_type (required on patch too)
                missing_offer_type = [d for d in details if 'offer_type' not in d]
                if missing_offer_type:
                    raise serializers.ValidationError(
                        "Each detail must include 'offer_type'."
                    )
                types = [d.get('offer_type') for d in details]
                if len(types) != len(set(types)):
                    raise serializers.ValidationError(
                        "Duplicate offer_type values are not allowed."
                    )
        return attrs

    def create(self, validated_data):
        # Create the Offer and its nested details
        detail_data = validated_data.pop('details')

        offer = Offer.objects.create(**validated_data)
        for detail in detail_data:
            OfferDetail.objects.create(offer=offer, **detail)
        return offer

    def update(self, instance, validated_data):
        # Update the offer fields and patch existing details by offer_type
        detail_data = validated_data.pop('details', None)

        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get(
            'description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        if detail_data:
            for detail in detail_data:
                try:
                    single_detail = instance.details.get(
                        offer_type=detail['offer_type'])
                except OfferDetail.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Detail with offer_type '{detail['offer_type']}' does not exist."
                    )
                for attr, value in detail.items():
                    if attr == 'offer_type':
                        continue
                    setattr(single_detail, attr, value)
                single_detail.save()

        return instance

# --- LIST and DETAIL SERIALIZERS ---


class OfferListUserNestedSerializer(serializers.ModelSerializer):
    """Minimal user info included on Offer list items."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']


class OfferListDetailNestedSerializer(serializers.ModelSerializer):
    """Representation for details on offer listing: id + url."""

    url = serializers.HyperlinkedIdentityField(
        view_name='offerdetail-detail', lookup_field='pk'
    )

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']
        read_only_fields = ['id', 'url']


class OfferListSerializer(OfferSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_detail = OfferListUserNestedSerializer(source='user', read_only=True)
    details = OfferListDetailNestedSerializer(many=True, read_only=True)

    # Annotated fields provided by the view's queryset
    min_price = serializers.IntegerField(read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Offer
        fields = ['id', 'user', 'title', 'image', 'description', 'created_at',
                  'updated_at', 'details', 'min_price', 'min_delivery_time', 'user_detail']
        read_only_fields = ['id']


class OfferDetailSerializer(OfferListSerializer):

    class Meta:
        model = Offer
        fields = ['id', 'user', 'title', 'image', 'description', 'created_at',
                  'updated_at', 'details', 'min_price', 'min_delivery_time']
        read_only_fields = ['id']

# --- OFFER DETAIL ITEM SERIALIZER ---


class OfferDetailItemSerializer(serializers.ModelSerializer):
    """Flat serializer for OfferDetail detail endpoints."""

    class Meta:
        model = OfferDetail
        fields = ['id', 'title', 'revisions', 'delivery_time_in_days',
                  'price', 'features', 'offer_type']
        read_only_fields = ['id']


# --- ORDER SERIALIZER ---

class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Orders. The input requires `offer_detail_id` and the
    serializer exposes nested offer_detail fields as read-only values.
    """

    offer_detail_id = serializers.IntegerField(write_only=True)

    customer_user = serializers.PrimaryKeyRelatedField(read_only=True)
    business_user = serializers.PrimaryKeyRelatedField(read_only=True)

    title = serializers.CharField(source='offer_detail.title', read_only=True)
    revisions = serializers.IntegerField(
        source='offer_detail.revisions', read_only=True)
    delivery_time_in_days = serializers.IntegerField(
        source='offer_detail.delivery_time_in_days', read_only=True)
    price = serializers.IntegerField(
        source='offer_detail.price', read_only=True)
    features = serializers.ListField(
        source='offer_detail.features', read_only=True)
    offer_type = serializers.CharField(
        source='offer_detail.offer_type', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer_user', 'business_user', 'status', 'offer_detail_id', 'title', 'revisions',
                  'delivery_time_in_days', 'price', 'features', 'offer_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'customer_user',
                            'business_user', 'status', 'created_at', 'updated_at']
        
class OrderStatusUpdateSerializer(OrderSerializer):

    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)

    class Meta:
        model = Order
        fields = ['id', 'customer_user', 'business_user', 'status', 'title', 'revisions',
                  'delivery_time_in_days', 'price', 'features', 'offer_type', 'created_at', 'updated_at']
        read_only_fields = [
            'id', 'customer_user', 'business_user', 'title', 'revisions',
            'delivery_time_in_days', 'price', 'features', 'offer_type', 'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        # Only allow updating the `status` field via this serializer
        allowed = {'status'}
        forbidden = set(attrs.keys()) - allowed
        if forbidden:
            raise serializers.ValidationError(f"Forbidden fields: {', '.join(forbidden)}")
        if not attrs:
            raise serializers.ValidationError("No data provided.")
        return attrs
    
# --- REVIEW SERIALIZER ---

class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating and listing reviews.

    Validation ensures the target user is a business and prevents double
    reviews by the same reviewer for the same business_user.
    """

    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    description = serializers.CharField()

    class Meta:
        model = Review
        fields = ['id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        business_user = attrs.get("business_user")

        # Ensure target is a business profile
        if not hasattr(business_user, "profile") or business_user.profile.type != "business":
            raise serializers.ValidationError({"business_user": "Must be a business profile."})

        # Prevent duplicate reviews from the same reviewer
        if user and Review.objects.filter(reviewer=user, business_user=business_user).exists():
            raise serializers.ValidationError("You have already reviewed this business user.")

        return attrs

class ReviewPatchSerializer(ReviewSerializer):

    class Meta(ReviewSerializer.Meta):
        model = Review
        fields = ['id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'business_user', 'reviewer', 'created_at', 'updated_at']

    def validate(self, attrs):
        # When patching, forbid changes to business_user or reviewer
        if not hasattr(self, 'initial_data') or not isinstance(self.initial_data, dict):
            return attrs

        forbidden = set(self.initial_data.keys()) & {'business_user', 'reviewer'}
        if forbidden:
            raise serializers.ValidationError({'non_field_errors': f"Forbidden fields: {', '.join(sorted(forbidden))}"})

        return attrs
