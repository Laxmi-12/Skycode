"""
author : mohan
app_name : form_generator
"""
from rest_framework import serializers
from .models import *
import json
from django import forms
from .models import FormPermission


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
    """
    filled  data serializer
    """

    class Meta:
        """
        Metaclass is used to define metadata options for the model.
        """
        model = FilledFormData
        fields = '__all__'


class FormPermissionForm(forms.ModelForm):
    class Meta:
        model = FormPermission
        fields = ['user_group', 'form', 'read', 'write', 'edit']


class UserLoginSerializer(serializers.Serializer):
    username = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=True, min_length=8)


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = '__all__'


# adding this for process and case management :
class CreateProcessSerializer(serializers.ModelSerializer):
    participants = JSONField()

    class Meta:
        """
        process create
        Metaclass is used to define metadata options for the model.
        """

        model = CreateProcess
        fields = ['id', 'process_name', 'participants', 'process_description', 'organization', 'usergroup']
        # fields = '__all__'


class CreateProcessResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreateProcess
        fields = ['id', 'process_name', 'process_description']


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
