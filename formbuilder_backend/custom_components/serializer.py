from venv import logger

from rest_framework import serializers

from form_generator.models import CreateProcess
from .models import Bot, BotSchema, BotData, Integration, IntegrationDetails, Organization, UserGroup, Ocr, Ocr_Details, Dashboard, \
    Dms,Dms_data,Ocr_Details
import json
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType





class JSONField(serializers.Field):
    def to_internal_value(self, data):
        # Convert JSON data to Python dictionary
        if isinstance(data, str):
            return json.loads(data)
        return data

    def to_representation(self, value):
        # Convert Python dictionary to JSON data
        if isinstance(value, dict):
            return value
        return json.dumps(value)


class BotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = ['name', 'bot_name', 'bot_description', 'bot_uid']


class BotSchemaSerializer(serializers.ModelSerializer):
    bot = serializers.PrimaryKeyRelatedField(queryset=Bot.objects.all())
    # bot = BotSerializer()
    # bot = BotSerializer(read_only=True)
    bot_schema_json = JSONField()
    flow_id = serializers.PrimaryKeyRelatedField(queryset=CreateProcess.objects.all(), allow_null=True, required=False)  # Add this line

    class Meta:
        model = BotSchema
        # fields = ['bot', 'bot_schema_json']
        # fields = '__all__'
        fields = ['id', 'bot_schema_json', 'flow_id', 'organization', 'bot']


class BotDataSerializer(serializers.ModelSerializer):
    data_schema = JSONField()
    bot_name = serializers.CharField(source='bot.bot_name',
                                     read_only=True)  # Include bot_name from the related Bot model

    class Meta:
        model = BotData
        fields = '__all__'


class IntegrationSerializer(serializers.ModelSerializer):
    integration_schema = JSONField()

    class Meta:
        model = Integration
        fields = '__all__'


class IntegrationDetailsSerializer(serializers.ModelSerializer):
    data_schema = JSONField()
    integration_type = serializers.CharField(source='integration.integration_type',
                                             read_only=True)  # Include bot_name from the related Bot model

    class Meta:
        model = IntegrationDetails
        fields = '__all__'


class OcrSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ocr
        fields = ['id', 'ocr_uid', 'ocr_type', 'name', 'description', 'organization']


class Ocr_DetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ocr_Details
        fields = '__all__'


class DashboardSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='usergroup.group_name', read_only=True)
    dashboard_config = JSONField()

    class Meta:
        model = Dashboard
        fields = '__all__'

    def create(self, validated_data):
        usergroup = validated_data.get('usergroup')
        if Dashboard.objects.filter(usergroup=usergroup).exists():
            logger.error(f"Usergroup {usergroup.group_name} already has an assigned dashboard.")
            raise serializers.ValidationError("This usergroup already has an assigned dashboard.")

        # return data
        # Call the parent class's create method to actually create the object
        return super().create(validated_data)


# class PermissionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Permission
#         fields = ['id', 'codename', 'name', 'content_type']
class CustomPermissionSerializer(serializers.Serializer):
    read = serializers.BooleanField()
    write = serializers.BooleanField()
    delete = serializers.BooleanField()


# serializer to validate the incoming password
class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data


# class UserGroupSerializer(serializers.ModelSerializer):
#     permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True)
#     organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
#
#     class Meta:
#         model = UserGroup
#         fields = ['id', 'group_name', 'group_description', 'permissions', 'organization']
#
#     def create(self, validated_data):
#         permissions_data = validated_data.pop('permissions')
#         user_group = UserGroup.objects.create(**validated_data)
#         user_group.permissions.set(permissions_data)
#         return user_group
#
#     def update(self, instance, validated_data):
#         permissions_data = validated_data.pop('permissions')
#         instance.group_name = validated_data.get('group_name', instance.group_name)
#         instance.group_description = validated_data.get('group_description', instance.group_description)
#         instance.organization = validated_data.get('organization', instance.organization)
#         instance.save()
#         instance.permissions.set(permissions_data)
#         return instance
# class PermissionsField(serializers.Field):
#     def to_representation(self, value):
#         permissions = value.all()
#         return {
#             'read': permissions.filter(codename='read').exists(),
#             'write': permissions.filter(codename='write').exists(),
#             'delete': permissions.filter(codename='delete').exists(),
#         }
#
#     def to_internal_value(self, data):
#         if not isinstance(data, dict):
#             raise serializers.ValidationError('Permissions should be a dictionary with boolean values.')
#
#         codenames = []
#         if data.get('read', False):
#             codenames.append('read')
#         if data.get('write', False):
#             codenames.append('write')
#         if data.get('delete', False):
#             codenames.append('delete')
#
#         permissions = Permission.objects.filter(codename__in=codenames)
#         if len(permissions) != len(codenames):
#             missing = set(codenames) - set(permissions.values_list('codename', flat=True))
#             raise serializers.ValidationError(f"Permissions not found: {', '.join(missing)}")
#
#         return permissions


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = ['id', 'group_name', 'group_description', 'status', 'organization']


class OrganizationSerializer(serializers.ModelSerializer):
    user_groups = UserGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'

    # class Meta:
    #     model = Organization
    #     fields = [
    #         'id', 'org_name', 'org_code', 'email', 'org_description', 'logo',
    #         'primary_color', 'secondary_color', 'accent1', 'accent2', 'accent3',
    #         'form', 'bot', 'integration', 'dms', 'ocr', 'dashboard', 'process',
    #         'user_groups'
    #     ]


class DmsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dms
        fields = '__all__'


class DmsDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dms_data
        fields = '__all__'
