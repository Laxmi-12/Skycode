"""
author : mohan
app_name : form_generator
"""
from django.contrib.auth.models import User
from django.db import models
import jsonfield
from datetime import date


# from custom_components.models import Organization


# adding this for process and case management TWS:
class CreateProcess(models.Model):
    """
    create process
    """
    process_name = models.CharField(max_length=200, blank=True)
    process_description = models.CharField(max_length=200, blank=True, null=True)
    initiator_group = models.IntegerField(null=True, blank=True)
    prefix = models.CharField(max_length=255, blank=True)
    first_step = models.CharField(max_length=255, blank=True)
    participants = jsonfield.JSONField(blank=True)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='create_process', blank=True, null=True)
    user_group = models.ManyToManyField('custom_components.UserGroup',
                                  related_name='usergroup_create_process', blank=True)

    def __str__(self):
        return str(self.id)


# adding this for process and case management TWS:
class Case(models.Model):
    """
    case management
    """
    processId = models.ForeignKey(CreateProcess, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    created_by = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=500)
    updated_on = models.DateTimeField(auto_now=True,null=True, blank=True)
    updated_by = models.CharField(max_length=300, blank=True)
    next_step = models.CharField(max_length=200, blank=True)
    data_json = jsonfield.JSONField(blank=True)
    path_json = jsonfield.JSONField(blank=True, default=list)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='case', blank=True, null=True)

    # assigned_to =  models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)


class FormDataInfo(models.Model):
    """
    form data records
    """
    Form_uid = models.CharField(max_length=50, blank=True)
    form_description = models.CharField(max_length=50, blank=True)
    # heading = models.CharField(max_length=200, blank=True)
    # subheading = models.CharField(max_length=200, blank=True)
    # logo = models.URLField(blank=True)
    # menu_name = models.CharField(max_length=200, blank=True)
    form_name = models.CharField(max_length=200, blank=True)
    form_json_schema = jsonfield.JSONField(blank=True)
    form_status = models.BooleanField(default=False)
    form_created_by = models.CharField(default="admin", max_length=200, blank=True)
    form_created_on = models.DateField(default=date.today)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='form_data_info', blank=True, null=True)
    processId = models.ForeignKey(CreateProcess, on_delete=models.CASCADE, null=True, blank=True)
    # usergroup = models.ManyToManyField('custom_components.UserGroup', on_delete=models.CASCADE,
    #                               related_name='usergroup_form_data_info', blank=True, null=True)

    user_groups = models.ManyToManyField('custom_components.UserGroup', through='FormPermission',
                                         related_name='usergroup_form_data_info', blank=True)

    def __str__(self):
        return str(self.id)


class UserData(models.Model):
    """
    user details database models
    """
    user_name = models.CharField(max_length=200, blank=True)
    mail_id = models.EmailField(unique=True)
    password = models.CharField(max_length=200, blank=True)
    profile_pic = models.CharField(max_length=300, blank=True)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='user_data', blank=True, null=True)
    usergroup = models.ForeignKey('custom_components.UserGroup', on_delete=models.CASCADE,
                                  related_name='usergroup_user_data', blank=True,
                                  null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True,
                                  null=True)  # Add this line

    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    # phone_number = models.CharField(max_length=10, blank=True)
    # created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user_name)


class FormPermission(models.Model):
    user_group = models.ForeignKey('custom_components.UserGroup', on_delete=models.CASCADE,
                                   related_name='form_permission')
    form = models.ForeignKey(FormDataInfo, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    edit = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user_group', 'form')


# adding this for process and case management TWS:
class FilledFormData(models.Model):
    """
    filled data models of users
    """
    formId = models.CharField(max_length=200, blank=True)
    userId = models.ForeignKey(UserData, on_delete=models.CASCADE, null=True, blank=True)
    processId = models.ForeignKey(CreateProcess, on_delete=models.CASCADE, null=True, blank=True)
    caseId = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    data_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='filled_data', blank=True, null=True)

    CHOICES = (
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    )
    status = models.CharField(max_length=500, choices=CHOICES, null=True, blank=True)
    # user_groups = models.ForeignKey('custom_components.UserGroup', on_delete=models.CASCADE,
    #                                      related_name='usergroup_filled_form_data', blank=True,null=True)
    user_groups = models.ManyToManyField('custom_components.UserGroup',
                                       related_name='usergroup_filled_form_data', blank=True)
    def __str__(self):
        return str(self.id)


# adding this for process and case management TWS:
class Rule(models.Model):
    """
    rule management
    """
    processId = models.ForeignKey(CreateProcess, on_delete=models.CASCADE, null=True, blank=True)
    ruleId = models.CharField(max_length=200, blank=True)
    rule_type = models.CharField(max_length=200, blank=True)
    rule_json_schema = jsonfield.JSONField(blank=True)
    organization = models.ForeignKey('custom_components.Organization', on_delete=models.CASCADE,
                                     related_name='rule', blank=True, null=True)

    def __str__(self):
        return str(self.id)


# adding this for process and case management TWS:
class Sla(models.Model):
    """
    rule management
    """
    processId = models.ForeignKey(CreateProcess, on_delete=models.CASCADE, null=True, blank=True)
    caseId = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    slaId = models.CharField(max_length=200, blank=True)
    sla_json_schema = jsonfield.JSONField(blank=True)

    def __str__(self):
        return str(self.id)
