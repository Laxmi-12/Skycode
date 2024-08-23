"""
author : mohan
app_name : form_generator
"""
from rest_framework import serializers
from .models import *
import json
from django import forms
from .models import FormPermission

from rest_framework import serializers
from django.contrib.auth.models import User


# To convert Json field from string to dict in serializer for API to accept the data in json format

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


class FormDataInfoSerializer(serializers.ModelSerializer):
    # form_json_schema = JSONField()
    form_json_schema = serializers.ListField(child=serializers.DictField())

    class Meta:
        model = FormDataInfo
        fields = '__all__'
        extra_kwargs = {
            'processId': {'required': False, 'allow_null': True},
            'organization': {'required': False, 'allow_null': True},
        }


class FilledDataInfoSerializer(serializers.ModelSerializer):
    data_json = JSONField()
    created_on = serializers.DateTimeField(source='caseId.created_on', read_only=True)
    updated_on = serializers.DateTimeField(source='caseId.updated_on', read_only=True)
    process_name = serializers.CharField(source='processId.process_name', read_only=True)
    user_groups = serializers.SerializerMethodField()
    #user_groups = serializers.IntegerField(source='user_groups.id', read_only=True)
    """
    filled  data serializer
    """

    class Meta:
        """
        Metaclass is used to define metadata options for the model.
        """
        model = FilledFormData
        fields = '__all__'

    def get_user_groups(self, obj):
        return obj.user_groups.values_list('id', flat=True)

class FormPermissionForm(forms.ModelForm):
    class Meta:
        model = FormPermission
        fields = ['user_group', 'form', 'read', 'write', 'edit']


class UserLoginSerializer(serializers.Serializer):
    username = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=True, min_length=8)


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        # Add any additional password validations here
        return value


# class UserInfoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserData
#         fields = '__all__'
#
#     def create(self, validated_data):
#         user = User.objects.create_user(
#             username=validated_data['username'],
#             email=validated_data['email'],
#             password=validated_data['password']
#         )
#         # Set the role if you have a role field or separate model
#         # user.role = validated_data.get('role', None)
#         # user.save()
#         return user

class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = ['id', 'user_name', 'mail_id', 'organization', 'usergroup', 'profile_pic']


# adding this for process and case management :
class CreateProcessSerializer(serializers.ModelSerializer):
    participants = JSONField()

    class Meta:
        """
        process create
        Metaclass is used to define metadata options for the model.
        """

        model = CreateProcess
        fields = ['id', 'process_name', 'participants', 'process_description', 'organization', 'user_group']
        # fields = '__all__'


class CreateProcessResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreateProcess
        fields = ['id', 'process_name', 'process_description','user_group']


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        """
        Case management
        Metaclass is used to define metadata options for the model.
        """
        model = Case
        fields = '__all__'


class RuleSerializer(serializers.ModelSerializer):
    rule_json_schema = JSONField()

    class Meta:
        """
        Rule management
        """
        model = Rule
        fields = '__all__'


class SlaSerializer(serializers.ModelSerializer):
    class Meta:
        """
        Rule management
        """
        model = Sla
        fields = '__all__'
