# from form_generator.models import CreateProcess, Case, FormDataInfo, UserData
from django.db import models
import jsonfield
import uuid

from django.contrib.auth.models import Permission


def user_directory_path(instance, filename):
    return f'temp_files/{uuid.uuid4()}_{filename}'


class Bot(models.Model):
    """
    bot 0.1
    """
    BOT_CHOICES = [
        ('google_drive', 'google_drive'),
        ('email', 'email'),
        ('screen_scraping', 'screen_scraping'),
        ('file_extractor', 'file_extractor'),
    ]

    bot_uid = models.CharField(max_length=50, unique=True, blank=True, null=True, )
    name = models.CharField(max_length=50, null=True, blank=True)
    bot_name = models.CharField(max_length=100, choices=BOT_CHOICES, default='google_drive')
    bot_description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.bot_uid} - {self.bot_name}"


# Model to create organizations
class Organization(models.Model):
    org_name = models.CharField(max_length=100)
    org_code = models.CharField(max_length=5, unique=True)
    email = models.EmailField()
    org_description = models.TextField(blank=True, null=True)
    large_logo_url = models.URLField(blank=True, null=True)
    small_logo_url = models.URLField(blank=True, null=True)
    primary_color = models.CharField(max_length=10, blank=True, null=True)
    secondary_color = models.CharField(max_length=10, blank=True, null=True)
    accent1_color = models.CharField(max_length=10, blank=True, null=True)
    accent2_color = models.CharField(max_length=10, blank=True, null=True)
    accent3_color = models.CharField(max_length=10, blank=True, null=True)

    # form = models.ForeignKey('form_generator.FormDataInfo', on_delete=models.CASCADE, blank=True, null=True)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, blank=True, null=True)
    # integration = models.ForeignKey(Integration, on_delete=models.CASCADE, blank=True, null=True)
    # dms = models.ForeignKey(Dms, on_delete=models.CASCADE, blank=True, null=True)
    # ocr = models.ForeignKey(Ocr, on_delete=models.CASCADE, blank=True, null=True)
    # dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, blank=True, null=True)
    # process = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, blank=True, null=True,
    #                             related_name='organization_process')

    # user_groups = models.ForeignKey(UserGroup, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.org_name


# Model to create user groups for the organizations
class UserGroup(models.Model):
    group_name = models.CharField(max_length=255)
    group_description = models.TextField()
    status = models.BooleanField(blank=True, null=True)
    # permissions = models.ManyToManyField(Permission, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='user_groups', blank=True,
                                     null=True)

    def __str__(self):
        return self.group_name


class Dashboard(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    dashboard_types = models.CharField(max_length=100, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='dashboard', blank=True,
                                     null=True)
    usergroup = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name='usergroup_dashboard', blank=True,
                                  null=True)
    dashboard_config = jsonfield.JSONField(blank=True, null=True)
    status = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return self.name


class BotSchema(models.Model):
    # bot = Bot(source='bot', read_only=True)
    """
    bot 0.2
    """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, default=1)
    bot_schema_json = jsonfield.JSONField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='bot_schema', blank=True,
                                     null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='process_bot_schema')

    def __str__(self):
        return f" Bot schema : {self.id}, {self.bot.bot_uid} - {self.bot.bot_name}"


class BotData(models.Model):
    """
    bot 0.3
    """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, blank=True, null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='bot_data')
    case_id = models.ForeignKey('form_generator.Case', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='case_bot_data')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='org_bot_data', blank=True,
                                     null=True)

    data_schema = jsonfield.JSONField(blank=True)
    temp_data = models.FileField(upload_to=user_directory_path, blank=True, null=True)

    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.id}"


class Integration(models.Model):
    """
    Integration 0.1.1
    """
    INTEGRATION_CHOICES = [
        ('api', 'api'),
    ]

    Integration_uid = models.CharField(max_length=50, blank=True, null=True)
    integration_type = models.CharField(max_length=100, choices=INTEGRATION_CHOICES, default='api')
    integration_name = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=50, blank=True, null=True)
    integration_schema = jsonfield.JSONField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='integration_schema',
                                     blank=True,
                                     null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='org_integration_schema')

    def __str__(self):
        return f"{self.id} - {self.integration_type}"


class IntegrationDetails(models.Model):
    """
    Integration 0.1.2
    """
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, default=1)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, default=1,
                                related_name='integration_details')
    case_id = models.ForeignKey('form_generator.Case', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='case_integration_details')
    data_schema = models.JSONField(blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='org_integration_details',
                                     blank=True,
                                     null=True)

    def __str__(self):
        return str(self.id)


class Dms(models.Model):
    """
        Dms 0.1.1
    """
    CONFIG_TYPES = [
        ('Google Drive', 'Google Drive'),
        ('S3 Bucket', 'S3 Bucket'),
        ('One Drive', 'One Drive')
    ]
    dms_uid = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True,
                            null=True)
    description = models.CharField(max_length=100, blank=True,
                                   null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)

    drive_types = models.CharField(max_length=100, choices=CONFIG_TYPES, default='Google Drive')
    config_details_schema = models.JSONField(blank=True, null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE,
                                related_name='flow_dms',blank=True,
                                     null=True)

    def __str__(self):
        return str(self.id)


class Dms_data(models.Model):
    filename = models.CharField(max_length=100, blank=True,
                                null=True)
    folder_id = models.CharField(max_length=100, blank=True,
                                 null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, default=1,
                                related_name='dms_data')
    case_id = models.ForeignKey('form_generator.Case', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='case_dms_data')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='org_dms_data',
                                     blank=True,
                                     null=True)
    usergroup = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name='usergroup_dms_data', blank=True,
                                  null=True)
    dms = models.ForeignKey(Dms, on_delete=models.CASCADE, related_name='dms_dms_data', blank=True,
                            null=True)
    meta_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class Ocr(models.Model):
    """
        OCR 0.1.1
        """
    OCR_CHOICES = [
        ('Aadhar Card Extraction', 'Aadhar Card Extraction'),
        ('Pan Card Extraction', 'Pan Card Extraction'),
        ('PDF to TEXT Extraction', 'Pan Card Extraction')


    ]

    ocr_uid = models.CharField(max_length=50, blank=True, null=True)
    ocr_type = models.CharField(max_length=100, choices=OCR_CHOICES, default='Aadhar Card Extraction')
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=100, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ocr',
                                     blank=True,
                                     null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE,
                                related_name='process_ocr', blank=True,
                                null=True)

    def __str__(self):
        return str(self.id)


class Ocr_Details(models.Model):
    ocr_uid = models.CharField(max_length=50, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ocr_details',
                                     blank=True,
                                     null=True)
    data_schema = models.JSONField(blank=True, null=True)
    flow_id = models.ForeignKey('form_generator.CreateProcess', on_delete=models.CASCADE, default=1,
                                related_name='process_ocr_details')
    case_id = models.ForeignKey('form_generator.Case', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='case_ocr_details')

    def __str__(self):
        return str(self.id)

# class Permission(models.Model):
#     codename = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=255)
#     description = models.CharField(max_length=255)
#
#     def __str__(self):
#         return self.codename
