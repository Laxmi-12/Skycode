from django.http.multipartparser import MultiPartParser
from django.shortcuts import get_object_or_404, get_list_or_404
from django.urls import reverse
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.parsers import FormParser

from .models import Bot, BotSchema, Integration, IntegrationDetails, Organization, UserGroup, Permission, Ocr, Dms, \
    Dashboard,Dms_data
from form_generator.models import CreateProcess, FormDataInfo, Rule, Case, UserData, FormPermission
from form_generator.serializer import CreateProcessSerializer, FormDataInfoSerializer, RuleSerializer, \
    FilledDataInfoSerializer, UserLoginSerializer, CreateProcessResponseSerializer
from .serializer import BotSerializer, BotSchemaSerializer, BotDataSerializer, \
    IntegrationSerializer, IntegrationDetailsSerializer, OrganizationSerializer, UserGroupSerializer, \
    PasswordResetSerializer, OcrSerializer, DashboardSerializer, DmsSerializer, DmsDataSerializer
from custom_components.utils.email_utils import send_email  # Adjust the import based on your app name
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveUpdateAPIView
from django.contrib.auth import views as auth_views
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import APIException
# Import for Components BGN --Fo

# Google_drive bot imports BGN
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from rest_framework.decorators import api_view
from rest_framework import generics, status, serializers

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
# Google_drive bot imports END

# api integration and screen scraping BGN
from rest_framework.response import Response

from django.core.exceptions import ValidationError

"""----Screen scraping(Automation) package-----"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from time import sleep

# api integration and screen scraping END

# Import for Components END --

import json
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status
# password reset import
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework.authtoken.models import Token
# from django.contrib.auth import authenticate
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# import for OCR Components starts ######################################

import pandas as pd
import json
import requests
from requests.exceptions import RequestException, SSLError, Timeout
from requests.auth import HTTPBasicAuth

from PIL import Image, ImageDraw
from ultralytics import YOLO
import easyocr
import numpy as np
import tempfile
from pypdf import PdfReader
import ocrmypdf
from datetime import datetime

# import for OCR Components ends ######################################
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.file import Storage
from google.auth.transport.requests import Request
from selenium.webdriver.chrome.service import Service as ChromeService

"""----------------------OneDrive-----------------------"""
from msal import ConfidentialClientApplication, SerializableTokenCache

"""----------------s3 Bucket--------------------------"""
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

"""---------------Mail Monitor-----------------"""

import os

"""---------------Create Log file-------------------"""
import logging

logger = logging.getLogger(__name__)
User = get_user_model()
logger = logging.getLogger('formbuilder_backend')  # Replace 'myapp' with the name of your app
IGNORE_ERRORS = [
    "web view not found"
]


# class ListProcessesByOrganization(APIView):
#     """
#     List all processes in the organization
#     """
#
#     def get(self, request, organization_id):
#         try:
#             processes = CreateProcess.objects.filter(organization_id=organization_id)
#             serializer = CreateProcessSerializer(processes, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class ListProcessesByOrganization(APIView):
    """
    List processes by organization ID and optionally by process ID,
    along with related bots, integrations, and rules
    """

    def get(self, request, organization_id, process_id=None):
        try:
            processes = CreateProcess.objects.filter(organization_id=organization_id)

            if process_id:
                processes = processes.filter(id=process_id)

            serializer = CreateProcessSerializer(processes, many=True)
            data = serializer.data

            # Fetch related bots, integrations, and rules for each process
            for process_data in data:
                flow_id = process_data['id']
                process_data['bots'] = list(BotSchema.objects.filter(flow_id=flow_id).values())
                process_data['integrations'] = list(Integration.objects.filter(flow_id=flow_id).values())
                process_data['rules'] = {'RuleConditions': list(Rule.objects.filter(processId=flow_id).values())}
                process_data['form'] = list(FormDataInfo.objects.filter(processId=flow_id).values())

                # Fetch form data along with permissions
                forms = FormDataInfo.objects.filter(processId=flow_id).values()
                print("forms", forms)
                for form in forms:
                    form_permissions = FormPermission.objects.filter(form_id=form['id']).values('user_group', 'read',
                                                                                                'write', 'edit')
                    form['permissions'] = list(form_permissions) if form_permissions else None

                process_data['form'] = list(forms)
            # Logging success
            logger.info(f"Successfully retrieved processes for organization {organization_id}")

            # Determine the response format based on the presence of process_id
            if process_id:
                if data:
                    response_data = data[0]  # Return the single object for the specific process
                else:
                    response_data = {}  # If no process is found, return an empty object
            else:
                response_data = data  # Return the array of processes

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            # Logging the exception
            logger.error(f"Failed to retrieve processes: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateProcessView(APIView):
    """
    Create a new process
    """

    def post(self, request):
        try:
            serializer = CreateProcessSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                # Logging success
                logger.info("New process created successfully")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Logging the exception
            logger.error(f"Failed to create new process: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessDetailView(RetrieveUpdateAPIView):
    """
    Retrieve, update or delete a process instance.
    """
    queryset = CreateProcess.objects.all()
    serializer_class = CreateProcessSerializer


# API to create the Bot Component, List and Update  starts ############################

class BotListCreateView(generics.ListCreateAPIView):
    # queryset = BotSchema.objects.all()
    serializer_class = BotSchemaSerializer

    # List all the bots
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if organization_id:
            return BotSchema.objects.filter(organization=organization_id).select_related('bot')
        return BotSchema.objects.all().select_related('bot')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        response_data = []

        for botschema in queryset:
            combined_data = {
                'id': botschema.bot.id,
                'bot_schema_json': botschema.bot_schema_json,
                'flow_id': botschema.flow_id,
                'organization': botschema.organization.id,  # Assuming organization ID is enough
                'bot_name': botschema.bot.bot_name,
                'bot_description': botschema.bot.bot_description,
                'name': botschema.bot.name,
            }
            response_data.append(combined_data)

        return JsonResponse(response_data, safe=False, status=status.HTTP_200_OK)

    # def get_queryset(self):
    #     organization_id = self.kwargs.get('organization_id')
    #     if organization_id:
    #         return BotSchema.objects.filter(organization=organization_id).select_related('bot')
    #     return BotSchema.objects.all().select_related('bot')
    #
    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     response_data = []
    #
    #     for botschema in queryset:
    #         combined_data = {
    #             'bot_schema_json': botschema.bot_schema_json,
    #             'flow_id': botschema.flow_id,
    #             'organization': botschema.organization,
    #             'bot_name': botschema.bot.bot_name,
    #             'bot_description': botschema.bot.bot_description,
    #             'name': botschema.bot.name,
    #         }
    #         response_data.append(combined_data)
    #
    #     return JsonResponse(response_data, safe=False, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        logger.info("Creating a bot")
        bot_data = request.data

        bot_name = bot_data.get('bot_name')
        name = bot_data.get('name')
        bot_description = bot_data.get('bot_description')
        bot_schema_json = bot_data.get('bot_schema_json')
        organization_id = bot_data.get('organization')

        bot_data = {
            'name': name,
            'bot_name': bot_name,
            'bot_description': bot_description,
        }
        logger.debug(f"bot_data: {bot_data}")

        bot_serializer = BotSerializer(data=bot_data)

        if bot_serializer.is_valid():
            try:
                bot_instance = bot_serializer.save()
            except Exception as e:
                logger.error(f"Error saving bot: {e}")
                raise APIException(f"An error occurred while saving the bot: {e}")
        else:
            logger.error(f"Invalid bot data: {bot_serializer.errors}")
            return Response(bot_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        print("bot_instance", bot_instance.id)
        bot_schema_data = {
            'bot': bot_instance.id,
            'bot_schema_json': bot_schema_json,
            'flow_id': None,  # Assuming flow_id is not provided in the input
            'organization': organization_id
        }
        logger.debug(f"bot_schema_data: {bot_schema_data}")

        bot_schema_serializer = BotSchemaSerializer(data=bot_schema_data)
        print("bot_serializer", bot_schema_data)
        if bot_schema_serializer.is_valid():
            try:
                bot_schema_instance = bot_schema_serializer.save()
                print("bot_schema_instance", bot_schema_instance)
            except Exception as e:
                logger.error(f"Error saving bot schema: {e}")
                bot_instance.delete()
                raise APIException(f"An error occurred while saving the bot schema: {e}")
        else:
            logger.error(f"Invalid bot schema data: {bot_schema_serializer.errors}")
            bot_instance.delete()
            return Response(bot_schema_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Successfully created bot")
        return Response({"message": "Bot created successfully"}, status=status.HTTP_201_CREATED)


class BotDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BotSerializer

    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        bot_id = self.kwargs.get('id')
        return Bot.objects.filter(id=bot_id)

    def retrieve(self, request, *args, **kwargs):
        organization_id = self.kwargs.get('organization_id')
        bot_id = self.kwargs.get('id')
        try:
            bot_instance = Bot.objects.get(id=bot_id)
            bot_schema_instance = BotSchema.objects.get(bot=bot_id, organization=organization_id)
        except Bot.DoesNotExist:
            logger.error(f"Bot with id {bot_id} not found")
            return Response({"error": "Bot not found"}, status=status.HTTP_404_NOT_FOUND)
        except BotSchema.DoesNotExist:
            logger.error(f"BotSchema with bot id {bot_id} and organization {organization_id} not found")
            return Response({"error": "BotSchema not found"}, status=status.HTTP_404_NOT_FOUND)

        bot_serializer = self.get_serializer(bot_instance)
        bot_schema_json = bot_schema_instance.bot_schema_json  # Get only bot_schema_json

        response_data = bot_serializer.data
        response_data['bot_schema_json'] = bot_schema_json

        return Response(response_data)

    def update(self, request, *args, **kwargs):
        bot_id = self.kwargs.get('id')
        try:
            bot_instance = Bot.objects.get(id=bot_id)
        except Bot.DoesNotExist:
            logger.error(f"Bot with id {bot_id} not found")
            return Response({"error": "Bot not found"}, status=status.HTTP_404_NOT_FOUND)

        bot_data = request.data
        bot_schema_json = bot_data.get('bot_schema_json')
        organization_id = bot_data.get('organization')  # For bot schema

        bot_serializer = BotSerializer(bot_instance, data=bot_data, partial=True)
        if bot_serializer.is_valid():
            try:
                bot_instance = bot_serializer.save()
            except Exception as e:
                logger.error(f"Error updating bot: {e}")
                raise APIException(f"An error occurred while updating the bot: {e}")
        else:
            logger.error(f"Invalid bot data: {bot_serializer.errors}")
            return Response(bot_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if bot_schema_json is not None:
            try:
                bot_schema_instance = BotSchema.objects.get(bot=bot_instance.id, organization=organization_id)
                bot_schema_serializer = BotSchemaSerializer(bot_schema_instance,
                                                            data={'bot_schema_json': bot_schema_json}, partial=True)
                if bot_schema_serializer.is_valid():
                    bot_schema_instance = bot_schema_serializer.save()
                else:
                    logger.error(f"Invalid bot schema data: {bot_schema_serializer.errors}")
                    return Response(bot_schema_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except BotSchema.DoesNotExist:
                logger.error("Bot schema does not exist")
                return Response({"error": "Bot schema does not exist"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error updating bot schema: {e}")
                raise APIException(f"An error occurred while updating the bot schema: {e}")

        logger.info("Successfully updated bot")
        return Response({"message": "Bot updated successfully"}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        bot_id = self.kwargs.get('id')
        try:
            bot_instance = Bot.objects.get(id=bot_id)
        except Bot.DoesNotExist:
            logger.error(f"Bot with id {bot_id} not found")
            return Response({"error": "Bot not found"}, status=status.HTTP_404_NOT_FOUND)

        bot_instance.delete()
        logger.info(f"Successfully deleted bot with id: {bot_instance.id}")
        return Response({"message": "Bot deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# API to create the Bot Component, List and Update  ends #############################


# API to create the Integration starts ##############################

class IntegrationListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = IntegrationSerializer

    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if organization_id:
            return Integration.objects.filter(organization_id=organization_id)
        return Integration.objects.none()

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            logger.info(f"Integration created: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create integration: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IntegrationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Integration.objects.all()
    serializer_class = IntegrationSerializer


# API to create the Integration ends ###############################

# API to create OCR components Starts ##############################

class OcrListCreateView(generics.ListCreateAPIView):
    serializer_class = OcrSerializer

    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if organization_id:
            return Ocr.objects.filter(organization_id=organization_id)
        return Ocr.objects.all()

    def create(self, request, *args, **kwargs):
        request.data['organization'] = self.kwargs.get('organization_id')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class OcrDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OcrSerializer

    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        return Ocr.objects.filter(organization_id=organization_id)


# API to create OCR components Ends ##############################


# API to create Dashboard Starts #################################

class DashboardListCreateView(generics.ListCreateAPIView):
    serializer_class = DashboardSerializer



    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        print("organization_id",organization_id)
        return Dashboard.objects.filter(organization_id=organization_id)

    def perform_create(self, serializer):
        organization_id = self.kwargs.get('organization_id')
        print("organization_id", organization_id)
        try:
            # Fetch the organization object based on organization_id
            organization = Organization.objects.get(id=organization_id)
            serializer.save(organization=organization)
        except Organization.DoesNotExist:
            raise ValidationError("The specified organization does not exist.")
        except ValidationError as e:
            logger.error(f"Validation error while creating dashboard: {e.detail}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error while creating dashboard: {e}")
            raise ValidationError("An unexpected error occurred while creating the dashboard.")
    # def perform_create(self, serializer):
    #     organization_id = self.kwargs.get('organization_id')
    #     print("organization_id", organization_id)
    #     try:
    #         serializer.save(organization_id=organization_id)
    #     except ValidationError as e:
    #         logger.error(f"Validation error while creating dashboard: {e.detail}")
    #         raise e
    #     except Exception as e:
    #         logger.error(f"Unexpected error while creating dashboard: {e}")
    #         raise ValidationError("An unexpected error occurred while creating the dashboard.")

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DashboardSerializer
    queryset = Dashboard.objects.all()

    # permission_classes = [IsAuthenticated]

    # def get_queryset(self):
    #     organization_id = self.kwargs.get('organization_id')
    #     return Dashboard.objects.filter(organization_id=organization_id)


    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        usergroup = self.kwargs.get('usergroup')
        return Dashboard.objects.filter(organization_id=organization_id, usergroup=usergroup)

    def get_object(self):
        queryset = self.get_queryset()
        filter_kwargs = {
            'organization_id': self.kwargs.get('organization_id'),
            'usergroup': self.kwargs.get('usergroup')
        }
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj



    def perform_update(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            logger.error(f"Validation error while updating dashboard: {e.detail}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error while updating dashboard: {e}")
            raise ValidationError("An unexpected error occurred while updating the dashboard.")

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# API to create Dashboard Ends #################################

# API to create DMS Starts #####################################

class DmsListCreateView(generics.ListCreateAPIView):
    serializer_class = DmsDataSerializer

    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        return Dms.objects.filter(organization_id=organization_id)

    def perform_create(self, serializer):
        organization_id = self.kwargs['organization_id']
        serializer.save(organization_id=organization_id)


class DmsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = DmsDataSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        return Dms.objects.filter(organization_id=organization_id)

class DmsDataListView(generics.ListAPIView):
    queryset = Dms_data.objects.all()
    serializer_class = DmsDataSerializer


# def send_filename_to_api(dms_data_id):
#     try:
#         # Retrieve the Dms_data instance
#         dms_data = Dms_data.objects.get(id=dms_data_id)
#         print("dms_data",dms_data)
#         filename = dms_data.filename
#         print("filename", filename)
#
#
#         if filename is None:
#             raise ValueError("Filename is not set for the given Dms_data instance.")
#
#         # Prepare the data to send
#         data = {'filename': filename}
#
#         # Define the target API URL
#         target_api_url = 'http://192.168.0.106:8000/FileDownloadView/'
#
#         # Send the POST request
#         response = requests.post(target_api_url, json=data)
#
#         # Check the response
#         response.raise_for_status()  # Raise an exception for HTTP errors
#         print("Filename sent successfully!")
#
#     except Dms_data.DoesNotExist:
#         print("Dms_data instance not found.")
#
#     except ValueError as ve:
#         print(f"ValueError: {ve}")
#
#     except requests.RequestException as re:
#         print(f"RequestException: {re}")


class DMSAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract filename from request data
        filename = request.data.get('filename')
        organization_id = request.data.get('organization_id')

        if not filename:
            return Response({"error": "Filename not provided."}, status=status.HTTP_400_BAD_REQUEST)

        if not organization_id:
            return Response({"error": "Organization ID not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the Dms instance associated with the given organization ID
        try:
            dms_instance = Dms.objects.get(organization_id=organization_id)
        except Dms.DoesNotExist:
            return Response({"error": "DMS entry not found for the given organization."},
                            status=status.HTTP_404_NOT_FOUND)

        # Get the additional details from the Dms instance
        drive_types = dms_instance.drive_types
        config_details_schema = dms_instance.config_details_schema
        config_details_schema['drive_types'] = drive_types
        config_details_schema['filename']=filename
        # Prepare data to send to the external API
        # data = {
        #     'filename': filename,
        #     'drive_types': drive_types,
        #     'config_details_schema': config_details_schema
        # }
        # print("data",data)

        # Send the filename and additional data to another API
        self.send_filename_to_api(config_details_schema)

        return Response({"message": "Filename and details are downloaded ."}, status=status.HTTP_200_OK)

    def send_filename_to_api(self,config_details_schema):
        external_api_url = 'http://192.168.0.106:8000/custom_components/FileDownloadView/'
        # Separate config_details_schema from the other data
        # Prepare the data for the request
        # data_to_send = {
        #     'filename': data['filename'],
        #     'drive_types': data['drive_types'],
        #     'config_details_schema': json.dumps(data['config_details_schema'])  # JSON stringify the config details
        # }

        response = requests.post(
            external_api_url,
            data=config_details_schema
        )
        if response.status_code != 200:
            raise Exception(f"Failed to send data to external API: {response.text}")

    # def post(self, request, *args, **kwargs):
    #     # Extract filename from request data
    #     filename = request.data.get('filename')
    #
    #     if filename is None:
    #         return Response({"error": "Filename not provided."}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     # Send the filename to another API
    #     send_filename_to_api(filename)
    #
    #     return Response({"message": "Filename sent to API."}, status=status.HTTP_200_OK)
# API to create DMS Ends #####################################


class ProcessBuilder(APIView):
    """
    overall process created from here and this api will store all schemas to the particular tables.
    """

    def post(self, request):
        # Extract process id
        process_id = request.data.get("id")
        organization_id = request.data.get("org_id")
        # Extract participants
        participants = request.data.get("participants")
        data = request.data
        print("data", data)

        try:
            process = CreateProcess.objects.get(id=process_id)
            process.participants = participants  # Assuming participants is a JSON field
            process.save()

        except CreateProcess.DoesNotExist:
            return JsonResponse({"error": "Process not found"}, status=404)

        # Create Bots instances
        # The part of your view or function handling the request data
        bots_data = request.data.get('bots', [])  # Get list of bots data, default empty list
        print("bots_data", bots_data)
        for bot_data in bots_data:
            bot_name = bot_data.get('bot_name')
            bot_uid = bot_data.get('bot_uid')
            bot_description = bot_data.get('bot_description')
            bot_schema_json = bot_data.get('bot_schema_json')

            bot_data = {  # bot serializer
                'bot_uid': bot_uid,
                'bot_name': bot_name,
                'bot_description': bot_description,
            }
            print('bot_data---0.2', bot_data)
            bot_serializer = BotSerializer(data=bot_data)
            if bot_serializer.is_valid():
                bot_instance = bot_serializer.save()
            else:
                process.delete()  # Rollback if Bot creation fails
                return Response(bot_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Create BotSchema instance
            bot_schema_data = {  # bot schema serializer
                'bot': bot_instance.id,  # Assign the primary key (ID) of the bot instance
                'bot_schema_json': bot_schema_json,
                'flow_id': process_id,
                'organization': organization_id
            }

            print('bot_data---0.3', bot_data)
            bot_schema_serializer = BotSchemaSerializer(data=bot_schema_data)

            if bot_schema_serializer.is_valid():

                bot_schema_instance = bot_schema_serializer.save()
                # return Response({"message": "Bot created successfully"}, status=status.HTTP_201_CREATED)

            else:
                # process.delete()  # Rollback if BotSchema creation fails
                bot_instance.delete()
                return Response(bot_schema_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # Create Integrations instances
        integrations_data = request.data.get('integrations', [])  # Get list of integrations data, default empty list
        for integration_data in integrations_data:
            integration_type = integration_data.get('integration_type')
            Integration_uid = integration_data.get('Integration_uid')
            integration_schema_json = integration_data.get('integration_schema')

            # integration_schema = json.dumps(integration_schema_json)

            integration_data = {  # integration serializer
                'Integration_uid': Integration_uid,
                'integration_type': integration_type,
                'integration_schema': integration_schema_json,
                'flow_id': process_id,
                'organization': organization_id
            }
            print('integration_data---0.4', integration_data)
            integration_serializer = IntegrationSerializer(data=integration_data)
            if integration_serializer.is_valid():
                integration_instance = integration_serializer.save()
                # return Response({"message": "Integrations successfully"}, status=status.HTTP_201_CREATED)

            else:
                process.delete()  # Rollback if Integration creation fails
                integration_instance.delete()
                return Response(integration_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create FormDataInfo instances
        form_data_info_data = request.data.get('form_data_info', [])
        print("form_data_info_data", form_data_info_data)
        for form_data in form_data_info_data:
            form_name = form_data.get('form_name')
            Form_uid = form_data.get('Form_uid')
            form_json_schema = form_data.get('form_json_schema')
            form_description = form_data.get('form_description')
            user_permission = form_data.get('permissions')
            # print("user_permissionssssssssssssss", user_permission)
            # user_group = user_permission[0]['user_group']
            #
            # print("user_group_id", user_group)
            process_instance = CreateProcess.objects.get(id=process_id)
            organization_instance = Organization.objects.get(id=organization_id)
            # Create or update the Form
            form_data_instance, created = FormDataInfo.objects.update_or_create(
                Form_uid=Form_uid,
                organization=organization_instance,
                processId=process_instance,
                defaults={
                    'form_name': form_name,
                    'form_json_schema': form_json_schema,
                    'form_description': form_description

                }
            )

            # Clear existing permissions to avoid duplicates
            FormPermission.objects.filter(form=form_data_instance).delete()

            # Create or update FormPermissions
            for permission in user_permission:
                user_group = permission['user_group']
                read = permission['read']
                write = permission['write']
                edit = permission['edit']

                user_group = UserGroup.objects.get(id=user_group)

                FormPermission.objects.create(
                    form=form_data_instance,
                    user_group=user_group,
                    read=read,
                    write=write,
                    edit=edit,
                )

                # return Response({"message": "Form data and permissions saved successfully"}, status=status.HTTP_201_CREATED)

        rule_data_info_list = request.data.get('rules', {})
        print("rule_data_info", rule_data_info_list)

        # Extract the list of rule conditions
        rules = rule_data_info_list.get('RuleConditions', [])
        # Process each rule
        for rule_data in rules:
            try:
                print("Processing rule_data...")
                rule_id = rule_data.get('rule_uid')
                print("rule_id:", rule_id)

                rule_json_schema_conditions = rule_data.get('conditions')
                print("rule_json_schema_conditions:", rule_json_schema_conditions)

                # Serialize the conditions to JSON
                # rule_json_schema = json.dumps(rule_json_schema_conditions)

                # Prepare the data for serialization
                rule_data_payload = {
                    'ruleId': rule_id,
                    'rule_json_schema': rule_json_schema_conditions,
                    'processId': process.id,
                    'organization': organization_id
                    # Assuming you have a foreign key to process in your Rule model

                }

                print('rule_data_payload', rule_data_payload)
                rule_data_serializer = RuleSerializer(data=rule_data_payload)
                if rule_data_serializer.is_valid():
                    rule_data_instance = rule_data_serializer.save()
                    print(f"Rule {rule_id} saved successfully.")
                else:
                    process.delete()  # Rollback if FormDataInfo creation fails
                    # bot_instance.delete()
                    # integration_instance.delete()
                    return Response(rule_data_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                process.delete()  # Rollback if any exception occurs
                print(f"Error occurred: {e}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ## to get OCR component and save in process starts
        ocr_info_data = request.data.get('ocr', [])
        print("ocr_info_data", ocr_info_data)
        for ocr_data in ocr_info_data:
            name = ocr_data.get('name')
            description = ocr_data.get('description')
            ocr_uid = ocr_data.get('ocr_uid')
            ocr_type = ocr_data.get('ocr_type')
            organization_instance = Organization.objects.get(id=organization_id)
            process_instance = CreateProcess.objects.get(id=process_id)
            ocr_data, created = Ocr.objects.update_or_create(
                ocr_uid=ocr_uid,
                organization=organization_instance,
                name=name,
                description=description,
                flow_id=process_instance,
                ocr_type=ocr_type
            )
            return Response({"message": "OCR saved  successfully"})

        dms_info_data = request.data.get('dms', [])
        print("dms_info_data", dms_info_data)
        for dms_data in dms_info_data:
            name = dms_data.get('name')

            description = dms_data.get('description')

            dms_uid = dms_data.get('dms_uid')

            config_type = dms_data.get('drive_types')

            config_details = dms_data.get('config_details_schema')

            organization_instance = Organization.objects.get(id=organization_id)
            process_instance = CreateProcess.objects.get(id=process_id)
            print("process_instance", process_instance)
            dms_data, created = Dms.objects.update_or_create(
                dms_uid=dms_uid,
                organization=organization_instance,
                name=name,
                description=description,
                drive_types=config_type,
                flow_id=process_instance,
                config_details_schema=config_details
            )
            return Response({"message": "DMS created successfully"})

        ## to get OCR component and save in process ends

        return Response("Process created successfully", status=status.HTTP_201_CREATED)


############################## Google Drive Extraction Bot Functionality ######################################

# to store the log details of the extractions
logger = logging.getLogger(__name__)


# This function gets the Google Drive service file and authenticate to access the file service account key file is
# integrated in settings.py
def get_google_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_KEY_FILE,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)


# Download the file from drive and store
def download_file(drive_service, file_id, file_name):
    file_metadata = drive_service.files().get(fileId=file_id, fields='mimeType').execute()
    mime_type = file_metadata.get('mimeType')
    # mime_type = file_metadata['mimeType']
    # Handle Google Docs Editors file types
    export_mime_types = {
        'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }

    if mime_type in export_mime_types:
        export_mime_type = export_mime_types[mime_type]
        request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        file_extension = export_mime_type.split('/')[-1].split('.')[-1]
        file_name = f"{file_name.split('.')[0]}.{file_extension}"
    else:
        request = drive_service.files().get_media(fileId=file_id)
    temp_file_path = os.path.join(settings.MEDIA_ROOT, 'tmp', file_name)
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    with io.FileIO(temp_file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return temp_file_path


# move the file to completed folder
def move_file(drive_service, file_id, new_parent_id):
    try:
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = file.get('parents', [])

        if not previous_parents:
            print(f"No previous parents found for the file: {file_id}")
            return {"error": f"No previous parents found for the file: {file_id}"}

        previous_parents_str = ",".join(previous_parents)

        # Move the file to the new folder by removing the old parents and adding the new parent
        updated_file = drive_service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents_str,
            fields='id, parents'
        ).execute()

        return updated_file
    except HttpError as error:
        print(f"An error occurred while moving the file: {error}")
        return {"error": f"An error occurred while moving the file: {error}"}


# To get any type of file types
def get_mime_type(file_type):
    mime_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'txt': 'text/plain',
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'png': 'image/png',
    }
    return mime_types.get(file_type, 'application/octet-stream')


# API which gets file from the Google Drive and save it in Temp folder
@api_view(['POST'])
def list_drive_files(request):
    try:

        # request_data = json.loads(request.body.decode('utf-8'))
        request_data = request.data

    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON data in request body"}, status=400)

    folder_id = request_data.get('folder_id')

    if not folder_id:
        return Response({"error": "folder_id parameter is required"}, status=400)

    file_type = request_data.get('file_type')

    completed_folder_id = request_data.get('completed_folder_id')
    drive_service = get_google_drive_service()

    query = f"'{folder_id}' in parents"

    if file_type:
        mime_type = get_mime_type(file_type)
        query += f" and mimeType='{mime_type}'"

    try:
        results = drive_service.files().list(q=query).execute()

    except HttpError as error:
        return Response({"error": f"An error occurred: {error}"}, status=400)

    items = results.get('files', [])

    files = []
    for item in items:
        file_id = item['id']
        file_name = item['name']
        temp_file_path = download_file(drive_service, file_id, file_name)
        if isinstance(temp_file_path, dict) and "error" in temp_file_path:
            return Response(temp_file_path, status=400)

        try:
            moved_file = move_file(drive_service, file_id, completed_folder_id)
            if not moved_file:
                return Response({"error": f"An error occurred while moving the file: {file_name}"}, status=400)

        except HttpError as error:
            return Response({"error": f"An error occurred while moving the file: {error}"}, status=400)

        file_schema = {
            'file_name': file_name,
            'file_id': file_id,
            # 'mimeType': item['mimeType'],
            'temp_data': temp_file_path,

        }
        print("file_schema ", file_schema)
        files.append(file_schema)
        return JsonResponse(file_schema, safe=False)


@api_view(['POST'])
def convert_excel_to_json(request):
    try:
        # Get the JSON data from the request
        input_data = json.loads(request.body.decode('utf-8'))

        # Validate input data
        if 'file_name' not in input_data or 'column_definitions' not in input_data:
            logger.error('Missing required fields in input JSON')
            return JsonResponse({"error": "Missing required fields in input JSON"}, status=400)

        file_name = input_data['file_name']
        sheet_name = input_data.get('sheet_name')
        column_definitions = input_data['column_definitions']
        file_path = input_data['file_path']

        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # Initialize a new dictionary to hold the final column names
        final_columns = {}
        files = []
        # Process the column definitions to map the columns
        for definition in column_definitions:
            column_key = definition['column_key']
            field_labels = definition['field_labels']

            for col in df.columns:
                if col in field_labels:
                    final_columns[col] = column_key
                    break

        # Check if all required columns are mapped
        if len(final_columns) != len(column_definitions):
            missing_columns = set([d['column_key'] for d in column_definitions]) - set(final_columns.values())
            logger.error(f'Missing columns in Excel: {missing_columns}')
            return JsonResponse({"error": f"Missing columns in Excel: {missing_columns}"}, status=400)

        # Rename the columns based on the mapping found
        df = df.rename(columns=final_columns)

        # Select only the columns specified in the final mapping
        df = df[list(final_columns.values())]

        # Convert DataFrame to JSON
        json_data = df.to_json(orient='records', date_format='iso')

        # Update the JSON data in the BotData entry
        # bot_data_entry.data_schema = json.loads(json_data)
        # bot_data_entry.save()

        # Transform JSON data into the desired format
        transformed_data = []
        for record in json.loads(json_data):
            for key, value in record.items():
                value_type = "String"
                if isinstance(value, bool):
                    value_type = "Boolean"
                elif isinstance(value, (int, float)):
                    value_type = "Number"
                elif isinstance(value, pd.Timestamp):
                    value_type = "Date"
                transformed_data.append({
                    "field_id": key,
                    "value": value,
                    "value_type": value_type
                })

        logger.info(f"Updated BotData entry for file: {file_name}")
        # Return the JSON data
        # return JsonResponse(json.loads(json_data), safe=False)
        response_data = {
            "data": transformed_data
        }
        files.append(response_data)
        return JsonResponse(response_data, safe=False)
        # Return the JSON data
        # return JsonResponse({"files": files}, safe=False)

    except json.JSONDecodeError as e:
        logger.error(f'Error decoding JSON: {str(e)}')
        return JsonResponse({"error": f"Error decoding JSON: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


########################## Google Drive END ##########################


##################### API Integration and screen scraping BGN #############


class Inputdata_Converter:
    @staticmethod
    def convert_to_dict(data):
        result = {}
        for item in data:
            result[item['field_id']] = item['value']
        return result


class Customize_Input:
    @staticmethod
    def customize_input_data(input_data, schema_config, view_id):
        """Customize input data based on request fields."""
        customized_data = []
        if view_id == "api":
            request_fields = schema_config.get('request', [])
            for field in request_fields:
                request_field_id = field.get('field_id')
                request_value_type = field.get('value_type')
                request_value = field.get('value')
                for item in input_data:
                    if request_value == item.get('field_id'):
                        request_value = item.get('value')
                        break
                if request_value and request_value_type == "field_id":
                    customized_data.append({
                        'field_id': request_field_id,
                        'value': request_value,
                        'value_type': request_value_type
                    })
        elif view_id == "screen_scraping":
            for form_data in schema_config:
                forms = form_data.get('forms', [])
                for form in forms:
                    form_values = form.get('form_value', [])
                    for form_value in form_values:
                        form_field_id = form_value.get('field_id')
                        form_value_type = form_value.get('value_type')
                        form_value = None
                        for item in input_data:
                            if item.get('field_id') == form_field_id:
                                form_value = item.get('value')
                                break
                        if value and form_value_type == "field_id":
                            customized_data.append({
                                'field_id': form_field_id,
                                'value': form_value,
                                'value_type': form_value_type
                            })
        return customized_data


class AutomationSetting:
    """This class handles the setup, navigation, and interaction with web pages using Selenium WebDriver."""
    driver = None  # Class-level variable to hold the WebDriver instance

    @staticmethod
    def initialize_driver(form_status):
        """Initialize the WebDriver and store it as a class attribute."""
        try:
            if AutomationSetting.driver is None:
                # s = Service(executable_path=ChromeDriverManager().install())
                # s = Service(ChromeDriverManager().install())
                # s = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
                driver = webdriver.Chrome(ChromeDriverManager().install())

                AutomationSetting.driver = webdriver.Chrome(service=driver)
                AutomationSetting.driver.maximize_window()
                logger.info("WebDriver initialized successfully.")

            form_status['initialized'] = True  # Update form_status

        except WebDriverException as wde:
            form_status['error'] = f"Error initializing WebDriver: {wde}"
            logger.error(form_status['error'])
            raise

    @staticmethod
    def navigate_to(url, form_status):
        """Navigate to the specified URL."""
        try:
            if AutomationSetting.driver is not None:
                AutomationSetting.driver.get(url)
                logger.info(f"Navigated to URL: {url}")

            # Update form_status

        except WebDriverException as wde:
            form_status['error'] = f"Error navigating to URL {url}: {wde}"
            logger.error(form_status['error'])
            raise

    @staticmethod
    def close_driver(form_status):
        """Close the WebDriver."""
        try:
            if AutomationSetting.driver is not None:
                AutomationSetting.driver.quit()
                AutomationSetting.driver = None
                logger.info("WebDriver closed successfully.")

            # Update form_status

        except WebDriverException as wde:
            form_status['error'] = f"Error closing WebDriver: {wde}"
            logger.error(form_status['error'])
            raise

    @staticmethod
    def setting(url, forms, input_data, form_status):
        """Set up the WebDriver, navigate to the login URL, and fill the forms."""
        get_element_result = None
        print("##############Set up the WebDriver, navigate to the login URL, and fill the forms.")
        try:
            print("____________________form_status ", form_status)
            print("____________________url ", form_status)
            AutomationSetting.initialize_driver(form_status)
            AutomationSetting.navigate_to(url, form_status)
            sleep(5)  # Allow time for the page to load

            processed_forms_count = 0
            for form in forms:
                print(form.get('form_value', []))
                print(form.get('form_value', []))
                try:
                    form_values = {fv['field_id']: {'value': fv['value'], 'value_type': fv.get('value_type')} for fv in
                                   form.get('form_value', [])}
                    element_details = {el['efield_id']: {'evalue': el['evalue'], 'evalue_type': el.get('evalue_type'),
                                                         'eaction': el['eaction']} for el in
                                       form['form_element_details']}
                    print(form_values)
                    print(element_details)
                    form_status, get_element_result = AutomationSetting.fill_form(form_values, element_details,
                                                                                  input_data, form_status,
                                                                                  get_element_result)
                    sleep(2)  # Wait for any form submission processing

                    processed_forms_count += 1
                    form_status['processed_forms_count'] = processed_forms_count
                    logger.info(f"Processed {processed_forms_count} forms successfully for URL: {url}")

                except KeyError as ke:
                    form_status['error'] = f"Missing key in form data: {ke}"
                    logger.error(form_status['error'])
                    raise ValidationError(form_status['error'])
                except Exception as e:
                    form_status['error'] = f"An error occurred while processing the form: {e}"
                    logger.error(form_status['error'])
                    raise ValidationError(form_status['error'])

            sleep(10)  # Allow time for the process to complete
        except Exception as e:
            form_status['error'] = f"An error occurred during the setting process: {e}"
            logger.error(form_status['error'])
            raise
        finally:
            AutomationSetting.close_driver(form_status)

        form_status['updated'] = True
        return form_status, get_element_result

    @staticmethod
    def fill_form(form_values, element_details, input_data, form_status, get_element_result):
        """Fill the form using the provided API configuration and input data."""

        for form_field_id, details in element_details.items():
            try:
                evalue = details['evalue']
                evalue_type = details['evalue_type']
                eaction = details['eaction']
                logger.info(f"Locating element '{form_field_id}' using {evalue_type}: {evalue}")
                print(f"Locating element '{form_field_id}' using {evalue_type}: {evalue}")
                print("form_status=============", form_status)
                retries = 3  # Number of retries for stale element
                while retries > 0:
                    try:
                        if evalue_type == "XPATH":
                            element = WebDriverWait(AutomationSetting.driver, 100).until(
                                EC.presence_of_element_located((By.XPATH, evalue))
                            )
                        elif evalue_type == "ID":
                            element = WebDriverWait(AutomationSetting.driver, 100).until(
                                EC.presence_of_element_located((By.ID, evalue))
                            )
                        elif evalue_type == "CLASS_NAME":
                            element = WebDriverWait(AutomationSetting.driver, 100).until(
                                EC.presence_of_element_located((By.CLASS_NAME, evalue))
                            )

                        if eaction == "send_keys":
                            element.clear()
                            if form_field_id in form_values:
                                form_value = form_values[form_field_id]
                                value = form_value['value']
                                value_type = form_value['value_type']

                                if value_type == "value":
                                    logger.info(f"Filling value for '{form_field_id}' with value: {value}")
                                    element.send_keys(value)
                                elif value_type == "field_id":
                                    input_field_id = value
                                    input_value = None
                                    for data in input_data:
                                        if input_field_id in data:
                                            input_value = data[input_field_id]
                                            break
                                    if input_value:
                                        logger.info(
                                            f"Filling value for '{form_field_id}' with value from input_data: {input_value}")
                                        element.send_keys(input_value)
                                    else:
                                        logger.warning(
                                            f"No value found for '{input_field_id}' in API response. Skipping...")
                                else:
                                    logger.warning(
                                        f"Unsupported value type '{value_type}' for '{form_field_id}'. Skipping...")


                        elif eaction == "date_send_keys":
                            element.clear()
                            if form_field_id in form_values:
                                form_value = form_values[form_field_id]
                                value = form_value['value']
                                value_type = form_value['value_type']

                                if value_type == "value":
                                    logger.info(f"Filling value for '{form_field_id}' with value: {value}")
                                    element.send_keys(value)
                                elif value_type == "field_id":
                                    input_field_id = value
                                    input_value = None
                                    for data in input_data:
                                        if input_field_id in data:
                                            input_value = data[input_field_id]
                                            break
                                    if input_value:
                                        # Convert to datetime object
                                        dt = datetime.strptime(input_value, "%Y-%m-%dT%H:%M:%S.%f")

                                        # Format to desired output
                                        formatted_date = dt.strftime("%m-%d-%Y")
                                        logger.info(
                                            f"Filling value for '{form_field_id}' with value from input_data: {formatted_date}")
                                        print(
                                            f"Filling value for '{form_field_id}' with value from input_data: {formatted_date}")
                                        element.send_keys(formatted_date)
                                    else:
                                        logger.warning(
                                            f"No value found for '{input_field_id}' in API response. Skipping...")
                                else:
                                    logger.warning(
                                        f"Unsupported value type '{value_type}' for '{form_field_id}'. Skipping...")
                        elif eaction == "click":
                            logger.info(f"Clicking button '{form_field_id}'")
                            element.click()

                        elif eaction == "wait_click":
                            sleep(30)  # Adjust as per your requirement
                            logger.info(f"Waiting for '{form_field_id}' action. Timeout in 30 seconds.")
                            element.click()

                        elif eaction == "wait_loading":
                            sleep(30)
                            logger.info(f"Waiting for loading completion.")

                        elif eaction == "switch_to_iframe":
                            AutomationSetting.driver.switch_to.frame(element)
                            logger.info(f"Switched to iframe '{form_field_id}'")

                        elif eaction == "switch_to_window":
                            window_handles = AutomationSetting.driver.window_handles
                            AutomationSetting.driver.switch_to.window(window_handles[1])
                            logger.info("Switched to new window.")

                        elif eaction == "clear":
                            element.clear()
                            logger.info(f"Cleared input for '{form_field_id}'.")

                        elif eaction == "get_element_text":
                            if form_field_id in form_values:
                                form_value = form_values[form_field_id]
                                value = form_value['value']
                                value_type = form_value['value_type']
                                extracted_text = element.text

                                logger.info(f"Extracted element text '{extracted_text}'")
                                get_element_result = {'field_id': form_field_id, 'value': extracted_text,
                                                      'value_type': value_type}
                                print("get_element_result", get_element_result)
                                logger.info(f"Processed text for '{form_field_id}': '{extracted_text}'")

                        else:
                            logger.warning(f"Unsupported action '{eaction}' for '{form_field_id}'. Skipping...")

                        form_status['updated'] = True
                        form_status['processed_forms_count'] += 1
                        logger.info(f"Performed action '{eaction}' on element '{form_field_id}' successfully.")
                        break  # Break out of retry loop if successful

                    except StaleElementReferenceException as sere:
                        logger.warning(
                            f"StaleElementReferenceException encountered. Retrying... ({retries} retries left)")
                        retries -= 1
                        sleep(2)  # Small delay before retrying

            except TimeoutException as te:
                form_status['error'] = f"Timeout occurred while locating element '{form_field_id}': {te.msg}"
                logger.error(form_status['error'])
                raise ValueError(form_status['error'])

            except WebDriverException as wde:
                form_status[
                    'error'] = f"WebDriverException occurred while processing element '{form_field_id}': {wde.msg}"
                logger.error(form_status['error'])
                raise ValueError(form_status['error'])

            except Exception as e:
                form_status['error'] = f"An error occurred while processing element '{form_field_id}': {e}"
                logger.error(form_status['error'])
                raise ValueError(form_status['error'])

        return form_status, get_element_result


class AutomationView(APIView):
    """This class handles sending the Requests to automate form submissions using Selenium WebDriver"""
    print("(((((((((((((((((((((((((((((((((((((((((((((")

    def post(self, request):
        logger.info("Received a new request in AutomationView")
        print("************************************")
        try:
            print(type(request.data))
            data = json.loads(request.data)
            print("data", data.get('schema_config'))
            schema_config = data.get('schema_config', [])
            print("schema_config====================", schema_config)
            input_data = data.get("input_data", {})
            print("input_data====================", input_data)
            # Customize input data based on schema_config and view_id
            # input_data = Customize_Input.customize_input_data(input_data, schema_config, "screen_scraping")
            # input_data = [Inputdata_Converter.convert_to_dict(input_data)]
            # print("input_data====================", input_data)
            # Initialize form_status
            # form_status = {
            #     'initialized': False,
            #     'updated': False,
            #     'processed_forms_count': 0,
            #     'error': None
            # }
            form_status = schema_config[0].get('form_status')[0]

            try:
                url = schema_config[0].get('url')
                print(url)
                forms = schema_config[0].get('forms')
                print(forms)
                logger.info(f"Processing URL: {url}")

                # Call AutomationSetting.setting and pass form_status
                process_status, get_element_result = AutomationSetting.setting(url, forms, input_data, form_status)
                print("process_status========================", process_status)
                print("get_element_result", get_element_result)
            except KeyError as ke:
                process_status = f"Missing key in form data: {ke}"
                logger.error(process_status)
                raise ValidationError(process_status)

            logger.info("Successfully processed the request")
            return Response({"data": [get_element_result], "status": process_status}, status=status.HTTP_200_OK)
            # return Response(process_status, status=status.HTTP_200_OK)

        except json.JSONDecodeError as je:
            process_status = f"Invalid JSON format in request body: {je}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as ve:
            process_status = f"Validation error: {ve}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            process_status = f"An error occurred while processing the JSON data: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APISetting:
    """This class handles the preparation, formatting, and execution of API requests, as well as the extraction and
    comparison of JSON keys in API responses """

    @staticmethod
    def find_key_in_response(res_field_id, response_dict):
        logger.debug(f"Finding key '{res_field_id}' in response.")
        keys = res_field_id.split('.')
        data = response_dict

        try:
            for key in keys:
                if isinstance(data, dict):
                    data = data.get(key)
                elif isinstance(data, list):
                    temp_data = [item.get(key) for item in data if isinstance(item, dict)]
                    data = temp_data
                else:
                    logger.warning(f"Unexpected data type encountered: {type(data)}")
                    return None

            if isinstance(data, list) and len(data) == 1:
                data = data[0]

            if data is None:
                logger.warning(f"Key '{res_field_id}' not found in response.")
            else:
                logger.debug(f"Key '{res_field_id}' found with value: {data}")

            return data

        except Exception as e:
            logger.error(f"Error while finding key '{res_field_id}' in response: {str(e)}")
            return None

    @staticmethod
    def compare_json_keys_and_extract(response_data, all_responses):
        logger.info("Comparing JSON keys and extracting values.")
        for json1 in response_data:
            if 'field_id' in json1:
                res_field_id = json1['field_id']
                for response_dict in all_responses:
                    if isinstance(response_dict, dict):
                        value = APISetting.find_key_in_response(res_field_id, response_dict)
                        if value is not None:
                            json1['field_id'] = json1['value']
                            json1['value'] = value
                            logger.debug(f"Extracted value '{value}' for key '{res_field_id}'.")
                            break  # Stop searching once the value is found
        return response_data

    @staticmethod
    def prepare_payload(item, request_data):
        logger.info("Preparing payload.")
        payload = {}
        for data in request_data:
            request_field_id = data['field_id']
            request_value_type = data['value_type']
            if request_value_type == "value":
                payload[request_field_id] = data['value']
            elif request_value_type == "field_id":
                payload[request_field_id] = item.get(data['value'], None)
                if payload[request_field_id] is None:
                    logger.warning(f"Field '{data['value']}' not found in item. Setting payload to None.")
        logger.debug(f"Prepared payload: {payload}")
        return payload

    @staticmethod
    def format_data(payload):
        logger.info("Formatting payload data.")
        formatted_data = {}
        for field_id, value in payload.items():
            keys = field_id.split('.')
            d = formatted_data
            for key in keys[:-1]:
                if key not in d:
                    d[key] = [{}]
                d = d[key][0]
            d[keys[-1]] = value
        json_formatted_data = json.dumps(formatted_data)
        logger.debug(f"Formatted data: {json_formatted_data}")
        return json_formatted_data

    @staticmethod
    def make_request(input_data, schema_config, process_status, max_retries=3):
        logger.info("Starting request process.")
        print("input_data-----???????????????????????????", input_data)
        print("schema_config----------???????????????????????????", schema_config)
        basic_url = schema_config['basic_url']
        endpoint_template = schema_config['end_point']
        headers = schema_config['header'][0]
        method = schema_config['method'].lower()
        auth_info = schema_config['auth'][0]
        timeout = (10, 150)

        request_data = schema_config['request']
        response_data = schema_config['response']
        all_responses = []
        print("request_data+++++++++++++++++++++++++++++++", request_data)
        process_status = "started"  # Update status to started

        try:
            for item in input_data:
                payload = APISetting.prepare_payload(item, request_data)
                formatted_data = APISetting.format_data(payload)
                print("formatted_data", formatted_data)
                request_url = basic_url + endpoint_template
                for key, value in payload.items():
                    request_url = request_url.replace(f"{{{key}}}", str(value))
                request_url = request_url.split("/{")[0]
                logger.info(f"Request URL: {request_url}")

                for attempt in range(max_retries):
                    try:
                        auth = None
                        if auth_info['auth_type'] == 'basic':
                            auth = HTTPBasicAuth(auth_info['username'], auth_info['password'])
                        elif auth_info['auth_type'] == 'oauth':
                            headers['Authorization'] = f"Bearer {auth_info['oauth_token']}"
                        elif auth_info['auth_type'] == 'bearer':
                            headers['Authorization'] = f"Bearer {auth_info['bearer_token']}"
                        elif auth_info['auth_type'] == "header":
                            headers['authorization'] = auth_info['authorization']

                        response = getattr(requests, method)(request_url, headers=headers, data=formatted_data,
                                                             auth=auth, timeout=timeout)
                        response.raise_for_status()
                        all_responses.append(response.json())
                        logger.info("Request successful.")
                        logger.debug(f"Response: {response.json()}")
                        response_data_updated = APISetting.compare_json_keys_and_extract(response_data, all_responses)
                        logger.debug(f"Updated response fields: {response_data_updated}")
                        process_status = "completed"  # Update status to completed
                        return response_data_updated, process_status  # Return response_data and status
                    except (requests.exceptions.SSLError, requests.exceptions.Timeout) as e:
                        logger.error(f"Request error on attempt {attempt + 1}: {e}")
                        process_status = f"retrying ({attempt + 1}/{max_retries})"
                        if attempt < max_retries - 1:
                            logger.info("Retrying...")
                            sleep(2)
                            continue
                        else:
                            if e.response:
                                logger.error(f"Final request error: {e.response.status_code} {e.response.content}")
                                process_status = f"Final request error: {e.response.status_code} {e.response.content}"
                            raise Exception(process_status) if e.response else e
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 400:
                            logger.error(f"Error Request Issues: {e.response.content}")
                            process_status = f"Error Request Issues: {e.response.content}"
                            return response_data, process_status
                        logger.error(f"Final request error: {e.response.status_code} {e.response.content}")
                        process_status = f"Request error: {e.response.status_code} {e.response.content}"
                        raise Exception(process_status) if e.response else e
            # If no exception is raised, status remains completed
            process_status = "completed"
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            process_status = f"error: {str(e)}"
            return response_data, process_status

        return response_data, process_status


class APIIntegrationView(APIView):
    """This class handles sending requests and processing responses based on the provided input data and
    configuration. """

    def post(self, request):
        logger.info("Received a new request in APIIntegrationView")

        try:
            data = json.loads(request.body)

            input_data = data.get("input_data", [])
            schema_config = data.get('schema_config')
            process_status = schema_config.get('status')
            print("input_data-----???????????????????????????", input_data)
            print("schema_config----------???????????????????????????", schema_config)
            # input_data = Customize_Input.customize_input_data(input_data, schema_config, "api")
            # print("input_data111----------", input_data)

            # input_data = [Inputdata_Convert er.convert_to_dict(input_data)]
            # print("input_data----------", input_data)

            # print(process_status)Customize_Input
            if not input_data or not schema_config:
                process_status = "Invalid input data or Schema configuration."
                logger.warning(process_status)
                return Response({"error": process_status}, status=status.HTTP_400_BAD_REQUEST)

            response_data, schema_config_status = APISetting.make_request(input_data, schema_config, process_status)
            print("response_data", response_data)
            print("schema_config_status", schema_config_status)
            logger.info(schema_config_status)

            return Response({"data": response_data, "status": schema_config_status}, status=status.HTTP_200_OK)

        except json.JSONDecodeError as e:
            process_status = f"JSON decode error: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_400_BAD_REQUEST)
        except SSLError as e:
            process_status = f"SSL error occurred while processing the request: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Timeout as e:
            process_status = f"Request timed out: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except RequestException as e:
            process_status = f"An error occurred while processing the request: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            process_status = f"An unexpected error occurred: {e}"
            logger.error(process_status)
            return Response({"error": process_status}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


##################### API Integration and screen scraping END #############


def initiate_password_reset(request):
    return auth_views.PasswordResetView.as_view()(request=request)


########################## creating organization starts ##############################################
######################### organization based process alone starts ##################################
# class OrganizationBasedProcess(APIView):
#     """
#     Organization based Process list
#     """
#
#     def get(self, request, *args, **kwargs):
#         processes = CreateProcess.objects.all()  # Adjust this as needed to filter processes
#         serializer = CreateProcessResponseSerializer(processes, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
class OrganizationBasedProcess(APIView):
    """
    Organization based Process list
    """

    def get(self, request, *args, **kwargs):
        organization_id = kwargs.get('organization_id')
        if not organization_id:
            return Response({"detail": "Organization ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        processes = CreateProcess.objects.filter(organization_id=organization_id)  # Filter by organization_id
        serializer = CreateProcessResponseSerializer(processes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrganizationDetailsAPIView(APIView):
    """
    Organization based details starts
    """

    def get(self, request, organization_id):
        forms = FormDataInfo.objects.filter(organization=organization_id)
        dms_records = Dms.objects.filter(organization=organization_id)
        user_groups = UserGroup.objects.filter(organization=organization_id)
        bots = BotSchema.objects.filter(organization=organization_id)
        integrations = Integration.objects.filter(organization=organization_id)

        forms_serializer = FormDataInfoSerializer(forms, many=True)
        dms_serializer = DmsSerializer(dms_records, many=True)
        user_groups_serializer = UserGroupSerializer(user_groups, many=True)
        bots_serializer = BotSchemaSerializer(bots, many=True)
        integrations_serializer = IntegrationSerializer(integrations, many=True)

        bots_data = []
        for bot in bots_serializer.data:
            bot_data = {
                "id": bot["id"],
                "bot_schema_json": bot["bot_schema_json"],
                "flow_id": bot["flow_id"],
                "organization": bot["organization"],
            }
            if "bot" in bot:
                bot_data.update({
                    "name": bot["bot"]["name"],
                    "bot_name": bot["bot"]["bot_name"],
                    "bot_description": bot["bot"]["bot_description"],
                    "bot_uid": bot["bot"].get("bot_uid"),
                })
            bots_data.append(bot_data)

        data = {
            'forms': forms_serializer.data,
            'dms': dms_serializer.data,
            'user_groups': user_groups_serializer.data,
            'bots': bots_data,
            'integrations': integrations_serializer.data,
        }

        return Response(data, status=status.HTTP_200_OK)


############### organization based details ends #######################################


class OrganizationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            organization = serializer.save()

            # Create or update super admin user
            super_admin_email = request.data.get('email')
            print("super_admin_email", super_admin_email)  # Adjust based on your request structure
            if super_admin_email:
                print("Creating or retrieving user...")  # Debugging line
                user, created = User.objects.get_or_create(email=super_admin_email)
                print("User object:", user)
                print("Created:", created)

                if created:
                    # Generate a unique username if needed
                    base_username = super_admin_email.split('@')[0]
                    username = base_username
                    counter = 1

                    # Ensure username is unique
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    user.username = username
                    user.is_superuser = True
                    user.is_staff = True
                    user.set_unusable_password()  # Ensures the user must set a password
                    user.save()
                    logger.info(f"Super admin user created with email: {super_admin_email}")
                else:
                    logger.info(f"Super admin user already exists with email: {super_admin_email}")
                # Save email and role in UserData model
                # UserData.objects.create(username=super_admin_email, role='Admin', organization=organization)
                # print("userrrrrrrrrrrrrrr",user.email)

                # Create or update UserData with user_id
                user_data, created = UserData.objects.get_or_create(mail_id=super_admin_email,user_name = username)
                user_data.user_id = user.id  # Assuming user_id is a field in UserData to store User's ID
                user_data.role = 'Admin'  # Assign role as needed
                user_data.organization = organization  # Assign organization
                user_data.save()

                # Send password reset email to the user's email address
                self.send_password_reset_email(user_data)

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating organization: {str(e)}")
            return Response({"error": "Failed to create organization"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_password_reset_email(self, user_data):
        try:
            user_id = user_data.user_id  # Assuming user_id is a field in UserData
            user = User.objects.get(id=user_id)

            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            # Constructing reset URL without encoding user_id
            reset_url = reverse('password_reset_confirm', kwargs={'user_id': user_id, 'token': token})
            reset_link = self.request.build_absolute_uri(reset_url)
            subject = 'Password Reset'
            body = f'Here is your password reset link: {reset_link}'

            send_mail(subject, body, settings.EMAIL_HOST_USER, [user.email])

            logger.info(f"Password reset email sent to {user.email}")
            return Response({"message": "Password reset email sent successfully."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} does not exist.")
            return Response({"error": "User does not exist."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return Response({"error": "Failed to send password reset email."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing organizations: {str(e)}")
            return Response({"error": "Failed to list organizations"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    def get_object(self):
        lookup_url_kwarg_id = 'pk'
        lookup_url_kwarg_code = 'org_code'
        if lookup_url_kwarg_id in self.kwargs:
            return self.queryset.get(pk=self.kwargs[lookup_url_kwarg_id])
        elif lookup_url_kwarg_code in self.kwargs:
            return self.queryset.get(org_code=self.kwargs[lookup_url_kwarg_code])
        else:
            raise Organization.DoesNotExist()

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving organization: {str(e)}")
            return Response({"error": "Failed to retrieve organization"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating organization: {str(e)}")
            return Response({"error": "Failed to update organization"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        try:
            organization = serializer.save()
            # Optionally send email to organization email for super admin
            # self.generate_password_link_email(organization.email)
        except Exception as e:
            logger.error(f"Error performing update on organization: {str(e)}")
            raise

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class CreatePermissionsView(APIView):
    def post(self, request):
        permissions = [
            {'code': 'read', 'description': 'Read permission'},
            {'code': 'write', 'description': 'Write permission'},
            {'code': 'delete', 'description': 'Delete permission'},
            {'code': 'execute', 'description': 'Execute permission'}
        ]

        created_permissions = []
        for perm in permissions:
            permission, created = Permission.objects.get_or_create(
                code=perm['code'], defaults={'description': perm['description']}
            )
            created_permissions.append(permission)

        return Response(
            {"created_permissions": [perm.code for perm in created_permissions]},
            status=status.HTTP_201_CREATED
        )


###################### create user permission ends ##############################################


######################### creating UserGroups[ADD,EDIT,LIST,DELETE] BGN #############################

class UserGroupListCreateAPIView(generics.ListCreateAPIView):
    # queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer

    def get_queryset(self):
        org_id = self.kwargs['org_id']  # Retrieve org_id from URL parameters
        if org_id is None:
            return UserData.objects.none()  # Return an empty queryset if org_id is not provided
        queryset = UserGroup.objects.filter(organization_id=org_id)
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            logger.error(f"Validation error creating user group: {str(e)}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error creating user group: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserGroupRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    # queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        org_id = self.kwargs['org_id']
        return UserGroup.objects.filter(organization_id=org_id)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error updating user group: {str(e)}")
            return Response({"error": "Failed to update user group"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting user group: {str(e)}")
            return Response({"error": "Failed to delete user group"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


######################### creating UserGroups ENDS ##################################################


########################## Password reset function ############################################
@method_decorator(csrf_exempt, name='dispatch')
class PasswordResetConfirmView(generics.UpdateAPIView):
    serializer_class = PasswordResetSerializer

    def update(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get('user_id')
            token = kwargs.get('token')
            logger.info(f"Password reset requested for user_id: {user_id} with token: {token}")

            user = get_object_or_404(User, id=user_id)
            user_data = get_object_or_404(UserData, user_id=user_id)

            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                logger.error("Invalid token provided.")
                return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            password = serializer.validated_data['password']

            # Set the new password in the User model
            user.set_password(password)
            user.save()
            logger.info(f"Password for user {user_id} has been reset successfully in User model.")

            # Update the password in UserData
            user_data.password = make_password(password)  # Store hashed password
            user_data.save()
            logger.info(f"Password for user {user_id} has been updated successfully in UserData model.")

            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} does not exist.")
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except UserData.DoesNotExist:
            logger.error(f"UserData with user ID {user_id} does not exist.")
            return Response({"error": "UserData does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return Response({"error": "Failed to reset password."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


########################## Password reset function ends ############################################

########################## Login function starts ###########################################

# @method_decorator(csrf_exempt, name='dispatch')
# class UserLoginView(generics.GenericAPIView):
#     serializer_class = UserLoginSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         username = serializer.validated_data['username']
#         print("username",username)
#         password = serializer.validated_data['password']
#         print("password", password)
#
#         logger.debug(f"Attempting to authenticate user: {username}")
#
#         user = authenticate(username=username, password=password)
#         logger.debug(f"Authenticated user: {user}")
#
#         if user is not None:
#             if user.is_active:
#                 try:
#                     user_data = UserData.objects.get(username=user.email)
#                 except UserData.DoesNotExist:
#                     logger.error(f"User data not found for username: {username}")
#                     return Response({"error": "User data not found"}, status=status.HTTP_404_NOT_FOUND)
#
#                 token, created = Token.objects.get_or_create(user=user)
#
#                 response_data = {
#                     "username": user.username,
#                     "role": user_data.role,
#                     "token": token.key,
#                 }
#
#                 logger.info(f"User {username} logged in successfully.")
#                 return Response(response_data, status=status.HTTP_200_OK)
#             else:
#                 logger.error(f"Inactive user attempted to log in: {username}")
#                 return Response({"error": "User account is inactive"}, status=status.HTTP_401_UNAUTHORIZED)
#         else:
#             logger.error(f"Failed login attempt for username: {username}")
#             return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


########################## Login function ends ##########################################


######################### API for OCR Components Starts ###################################

# class PancardExtractionSetting:
#
#     @staticmethod
#     def detect_objects_on_image(image, obj_det=None):
#         model_path = os.path.join(settings.BASE_DIR, 'static/pancard_model/New_result_08_07_24/weights/best.pt')
#         model = YOLO(model_path)
#         results = model.predict(image)
#         result = results[0]
#         output = []
#         for box in result.boxes:
#             x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]
#             class_id = box.cls[0].item()
#             prob = round(box.conf[0].item(), 2)
#             if obj_det is None or obj_det == result.names[class_id]:
#                 output.append([x1, y1, x2, y2, result.names[class_id], prob])
#         logger.info(f"Object detection completed on image with {len(output)} objects.")
#         return output
#
#     @staticmethod
#     def draw_boxes(image, boxes):
#         draw = ImageDraw.Draw(image)
#         for box in boxes:
#             x1, y1, x2, y2, label, prob = box
#             draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
#             text = f"{label} {prob:.2f}"
#             draw.text((x1, y1 - 10), text, fill="red")
#         logger.info("Bounding boxes drawn on image.")
#         return image
#
#     @staticmethod
#     # def crop_and_extract_text(image, boxes):
#     #     reader = easyocr.Reader(['en'])
#     #     extracted_texts = {}
#     #     for box in boxes:
#     #         x1, y1, x2, y2, label, prob = box
#     #         cropped_image = image.crop((x1, y1, x2, y2))
#     #         cropped_image = cropped_image.convert('RGB')
#     #         img_array = np.array(cropped_image)
#     #         try:
#     #             text = reader.readtext(img_array, detail=0, paragraph=True)
#     #             extracted_text = " ".join(text).strip()
#     #             if label in extracted_texts:
#     #                 extracted_texts[label] += " " + extracted_text
#     #             else:
#     #                 extracted_texts[label] = extracted_text
#     #         except Exception as e:
#     #             logger.error(f"Error extracting text from box: {str(e)}")
#     #             return {"error": str(e)}
#     #     logger.info("Text extraction completed.")
#
#     #     return extracted_texts
#     @staticmethod
#     def crop_and_extract_text(image, boxes):
#         reader = easyocr.Reader(['en'])
#         extracted_texts = {}
#         field_mappings = {
#             "IT": "",
#             "IT_emblem": "",  # Assuming you want to remove this field
#             "panHolder_Name": "Name",
#             "panHolder_photo": "",  # Assuming you want to remove this field
#             "panHolder_Number": "Number",
#             "panHolder_CO": "Father name",
#             "panHolder_Signature": "",  # Assuming you want to remove this field
#             "panHolder_DOB": "DOB"
#         }
#
#         for box in boxes:
#             x1, y1, x2, y2, label, prob = box
#             cropped_image = image.crop((x1, y1, x2, y2))
#             cropped_image = cropped_image.convert('RGB')
#             img_array = np.array(cropped_image)
#
#             try:
#                 text = reader.readtext(img_array, detail=0, paragraph=True)
#                 extracted_text = " ".join(text).strip()
#
#                 # Map label to desired field name and add to extracted_texts
#                 if label in field_mappings and field_mappings[label]:
#                     field_name = field_mappings[label]
#                     if field_name in extracted_texts:
#                         extracted_texts[field_name] += " " + extracted_text
#                     else:
#                         extracted_texts[field_name] = extracted_text
#
#             except Exception as e:
#                 logger.error(f"Error extracting text from box: {str(e)}")
#                 return {"error": str(e)}
#
#         logger.info("Text extraction completed.")
#         return extracted_texts
#
#
# class PancardExtractionView(APIView):
#     # parser_classes = [MultiPartParser, FormParser]
#
#     def post(self, request, *args, **kwargs):
#         files = request.FILES.getlist('file')
#         if not files:
#             return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)
#
#         all_extracted_texts = {}
#         for file in files:
#             try:
#                 image = Image.open(file)
#                 detected_objects = PancardExtractionSetting.detect_objects_on_image(image)
#                 image_with_boxes = PancardExtractionSetting.draw_boxes(image.copy(), detected_objects)
#                 extracted_texts = PancardExtractionSetting.crop_and_extract_text(image, detected_objects)
#                 all_extracted_texts[file.name] = extracted_texts
#             except Exception as e:
#                 logger.error(f"Error processing file {file.name}: {str(e)}")
#
#         response_data = {
#             "extracted_info": all_extracted_texts,
#         }
#         logger.info("succesfully extracted: {response_data}")
#         return Response(response_data, status=status.HTTP_200_OK)
#
#
# class AadharcardExtractionSetting:
#
#     @staticmethod
#     def detect_objects_on_image(image, obj_det=None):
#         model_path = os.path.join(settings.BASE_DIR, 'static/aadharcard_model/weights/best.pt')
#         model = YOLO(model_path)
#         results = model.predict(image)
#         result = results[0]
#         output = []
#         for box in result.boxes:
#             x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]
#             class_id = box.cls[0].item()
#             prob = round(box.conf[0].item(), 2)
#             if obj_det is None or obj_det == result.names[class_id]:
#                 output.append([x1, y1, x2, y2, result.names[class_id], prob])
#         logger.info(f"Object detection completed on image with {len(output)} objects.")
#         return output
#
#     @staticmethod
#     def draw_boxes(image, boxes):
#         draw = ImageDraw.Draw(image)
#         for box in boxes:
#             x1, y1, x2, y2, label, prob = box
#             draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
#             text = f"{label} {prob:.2f}"
#             draw.text((x1, y1 - 10), text, fill="red")
#         logger.info("Bounding boxes drawn on image.")
#         return image
#
#     @staticmethod
#     def crop_and_extract_text(image, boxes):
#         reader = easyocr.Reader(['en'])
#         extracted_texts = {}
#         for box in boxes:
#             x1, y1, x2, y2, label, prob = box
#             cropped_image = image.crop((x1, y1, x2, y2))
#             cropped_image = cropped_image.convert('RGB')
#             img_array = np.array(cropped_image)
#             try:
#                 text = reader.readtext(img_array, detail=0, paragraph=True)
#                 extracted_text = " ".join(text).strip()
#                 if label in extracted_texts:
#                     extracted_texts[label] += " " + extracted_text
#                 else:
#                     extracted_texts[label] = extracted_text
#             except Exception as e:
#                 logger.error(f"Error extracting text from box: {str(e)}")
#                 return {"error": str(e)}
#         logger.info("Text extraction completed.")
#         return extracted_texts
#
#
# class AadharcardExtractionView(APIView):
#     # parser_classes = [MultiPartParser, FormParser]
#
#     def post(self, request, *args, **kwargs):
#         files = request.FILES.getlist('file')
#         if not files:
#             return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
#
#         all_extracted_texts = {}
#         for file in files:
#             try:
#                 image = Image.open(file)
#                 detected_objects = AadharcardExtractionSetting.detect_objects_on_image(image)
#                 image_with_boxes = AadharcardExtractionSetting.draw_boxes(image.copy(), detected_objects)
#                 extracted_texts = AadharcardExtractionSetting.crop_and_extract_text(image, detected_objects)
#                 all_extracted_texts[file.name] = extracted_texts
#             except Exception as e:
#                 logger.error(f"Error processing file {file.name}: {str(e)}")
#
#         response_data = {
#             "extracted_info": all_extracted_texts,
#         }
#         logger.info("successfully extracted: {response_data}")
#         return Response(response_data, status=status.HTTP_200_OK)
#
#
# class OCRExtractionSetting:
#     @staticmethod
#     def extract_text(input_file_name):
#         logger.info(f"Starting text extraction from {input_file_name}")
#         reader = PdfReader(input_file_name)
#         number_of_pages = len(reader.pages)
#         all_text = []
#
#         for i in range(number_of_pages):
#             page = reader.pages[i]
#             text = page.extract_text()
#             all_text.append(text)
#             if text:
#                 logger.info(f"Text extracted from page {i}")
#             else:
#                 logger.warning(f"No text found on page {i}")
#
#         return all_text
#
#     @staticmethod
#     def editable_pdf(input_file_name, output_file_name):
#         if os.path.isfile(input_file_name):
#             logger.info(f"Creating editable PDF: {output_file_name}")
#             ocrmypdf.ocr(input_file_name, output_file_name, skip_text=True)
#             if os.path.isfile(output_file_name):
#                 logger.info(f"Editable PDF created: {output_file_name}")
#             else:
#                 logger.error(f"Failed to create editable PDF: {output_file_name}")
#         else:
#             logger.error(f"Input file not found: {input_file_name}")
#
#         return output_file_name
#
#
# class OCRExtractionView(APIView):
#     # parser_classes = [MultiPartParser, FormParser]
#
#     def post(self, request, *args, **kwargs):
#         files = request.FILES.getlist('file')
#         if not files:
#             return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
#
#         all_extracted_texts = {}
#         for file in files:
#             try:
#                 # Save the uploaded file to a temporary file
#                 with tempfile.NamedTemporaryFile(delete=False) as temp_file:
#                     for chunk in file.chunks():
#                         temp_file.write(chunk)
#                     input_file_name = temp_file.name
#
#                 output_file_name = f"{os.path.splitext(input_file_name)[0]}_output.pdf"
#
#                 text = OCRExtractionSetting.extract_text(input_file_name)
#                 if not text:
#                     logger.info(f"No text found in {input_file_name}, converting to editable PDF.")
#                     edit_file_name = OCRExtractionSetting.editable_pdf(input_file_name, output_file_name)
#                     text = OCRExtractionSetting.extract_text(edit_file_name)
#
#                 all_extracted_texts[file.name] = text
#                 logger.info(f"Text successfully extracted from {file.name}")
#             except Exception as e:
#                 logger.error(f"Error processing file {file.name}: {str(e)}")
#             finally:
#                 if os.path.exists(input_file_name):
#                     os.remove(input_file_name)
#                 if os.path.exists(output_file_name):
#                     os.remove(output_file_name)
#
#         response_data = {
#             "extracted_info": all_extracted_texts,
#         }
#
#         logger.info(f"Extraction completed successfully: {response_data}")
#         return Response(response_data, status=status.HTTP_200_OK)


######################### API for OCR Components Ends ###################################


######################## API for DMS components starts ##################################


class GoogleDrive(APIView):

    @staticmethod
    def get_gdrive_credentials(access_token, refresh_token, client_id, client_secret, token_uri):
        """Gets valid user credentials from access token, client ID, and client secret."""
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret
        )

        # Refresh the token if it has expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        return credentials

    @staticmethod
    def upload_to_gdrive(folder_name, file_obj, gdrive_metadata, access_token, refresh_token, client_id, client_secret,
                         token_uri):
        """Uploads the specified file object to Google Drive with a renamed file name."""
        try:
            credentials = GoogleDrive.get_gdrive_credentials(access_token, refresh_token, client_id, client_secret,
                                                             token_uri)
            service = build('drive', 'v3', credentials=credentials)

            current_date = datetime.now().strftime("%d_%b_%Y")
            current_time = datetime.now().strftime("%H_%M_%S")
            file_name, file_extension = os.path.splitext(file_obj.name)
            modified_filename = f"{file_name}_{current_date}_{current_time}{file_extension}"
            print("folder_name", folder_name)
            # Check if folder exists
            results = service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            print("results ", results)
            if results.get('files'):
                folder_id = results['files'][0]['id']
                logger.info(f"Found existing folder '{folder_name}' with ID {folder_id}.")
            else:
                # Create folder if it doesn't exist
                gdrive_file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'description': gdrive_metadata
                }
                folder = service.files().create(body=gdrive_file_metadata, fields='id').execute()
                print("folder ", folder)
                folder_id = folder.get('id')
                logger.info(f"Created new folder '{folder_name}' with ID {folder_id}.")

            # Convert InMemoryUploadedFile to BytesIO
            file_stream = io.BytesIO(file_obj.read())

            # Upload file to the folder
            media = MediaIoBaseUpload(
                file_stream, mimetype=file_obj.content_type, resumable=True
            )

            gdrive_file_metadata = {
                'name': modified_filename,
                'parents': [folder_id],
                'description': gdrive_metadata
            }

            file = service.files().create(
                body=gdrive_file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print("file", file)
            logger.info(f'File "{modified_filename}" uploaded successfully to folder "{folder_name}".')
            return JsonResponse({'file_name': modified_filename, 'file': file,
                                 'status': f'File "{modified_filename}" uploaded successfully to Google Drive.'},
                                status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"An error occurred during upload: {e}")
            return Response({'error': f'An error occurred during upload: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def download_from_gdrive(file_name, access_token, refresh_token, client_id, client_secret, token_uri):
        """Downloads the specified file from Google Drive by name."""
        credentials = GoogleDrive.get_gdrive_credentials(access_token, refresh_token, client_id, client_secret,
                                                         token_uri)
        service = build('drive', 'v3', credentials=credentials)

        try:
            # Search for file by name
            results = service.files().list(
                q=f"name='{file_name}'",
                fields="files(id, name)"
            ).execute()
            downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
            # local_file_path = os.path.join(downloads_folder, file_name)
            if results.get('files'):
                file_id = results['files'][0]['id']
                request = service.files().get_media(fileId=file_id)
                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)
                done = False

                while not done:
                    _, done = downloader.next_chunk()

                # Save the file to the specified download path
                file_stream.seek(0)
                local_file_path = os.path.join(downloads_folder, file_name)
                with open(local_file_path, 'wb') as f:
                    f.write(file_stream.read())

                logger.info(f'File "{file_name}" downloaded successfully from Google Drive.')
                return JsonResponse({'file_name': file_name,
                                     'status': f'File "{file_name}" downloaded successfully from Google Drive.'},
                                    status=status.HTTP_200_OK)
            else:
                logger.error(f"File '{file_name}' not found in Google Drive.")
                return Response({'error': f"File '{file_name}' not found in Google Drive."},
                                status=status.HTTP_404_NOT_FOUND)

        except HttpError as error:
            logger.error(f"An error occurred during download: {error}")
            return Response({'error': f'An error occurred during download: {error}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class S3Bucket:
    @staticmethod
    def initialize_client(aws_access_key_id, aws_secret_access_key):
        try:
            return boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        except NoCredentialsError:
            logger.error('Credentials not available')
            return None

    @staticmethod
    def upload_to_S3Bucket(files, aws_access_key_id, aws_secret_access_key, bucket_name, s3_bucket_metadata):
        s3_client = S3Bucket.initialize_client(aws_access_key_id, aws_secret_access_key)
        print("s3_bucket_metadata", s3_bucket_metadata)
        if not s3_client:
            return Response({'error': 'Credentials not available'}, status=status.HTTP_403_FORBIDDEN)

        try:
            current_date = datetime.now().strftime("%d_%b_%Y")
            current_time = datetime.now().strftime("%H_%M_%S")
            file_name, file_extension = files.name.split('.')
            modified_filename = f"{file_name}_{current_date}_{current_time}.{file_extension}"
            print("modified_filename ", modified_filename)
            s3_client.upload_fileobj(files, bucket_name, modified_filename, ExtraArgs={'Metadata': s3_bucket_metadata})
            print("modified_filename ")
            logger.info('Files uploaded successfully')
            return JsonResponse({'file_name': modified_filename,
                                 'status': f'Files {modified_filename} uploaded successfully to S3Buckets'},
                                status=status.HTTP_200_OK)

        except ClientError as e:
            logger.error(f'Failed to upload to S3: {e}')
            return Response({'error': f'Failed to upload to S3: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def download_from_S3Bucket(file_name, aws_access_key_id, aws_secret_access_key, bucket_name):
        s3_client = S3Bucket.initialize_client(aws_access_key_id, aws_secret_access_key)
        if not s3_client:
            return Response({'error': 'Credentials not available'}, status=status.HTTP_403_FORBIDDEN)

        try:
            downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
            local_file_path = os.path.join(downloads_folder, file_name)
            s3_client.download_file(Bucket=bucket_name, Key=file_name, Filename=local_file_path)
            logger.info(f'File {file_name} downloaded successfully')
            return JsonResponse(
                {'file_name': file_name, 'status': f'File {file_name} downloaded successfully from S3Buckets'},
                status=status.HTTP_200_OK)
        except ClientError as e:
            logger.error(f'Failed to download from S3: {e}')
            return Response({'error': f'Failed to download from S3: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadView(APIView):
    # parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        print("data")

        drive_type = request.data.get('drive_types')
        print("drive_type", drive_type)
        if drive_type == "S3 Bucket":

            bucket_name = request.data.get('bucket_name')
            print("bucket_name", bucket_name)
            aws_access_key_id = request.data.get('aws_access_key_id')
            aws_secret_access_key = request.data.get('aws_secret_access_key')
            s3_bucket_metadata = json.loads(request.data.get('metadata', '{}'))

            if not (bucket_name and aws_access_key_id and aws_secret_access_key):
                logger.error("Incomplete S3 credentials")
                return Response({"error": "Incomplete S3 credentials"}, status=status.HTTP_400_BAD_REQUEST)

            files = request.FILES.get('files')

            if not files:
                logger.error("No files provided")
                return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)
            return S3Bucket.upload_to_S3Bucket(files, aws_access_key_id, aws_secret_access_key, bucket_name,
                                               s3_bucket_metadata)

        elif drive_type == "Google Drive":
            access_token = request.data.get('access_token')
            refresh_token = request.data.get('refresh_token')
            client_id = request.data.get('client_id')
            client_secret = request.data.get('client_secret')
            token_uri = request.data.get('token_uri')
            folder_name = request.data.get('folder_name')
            gdrive_metadata = request.data.get('metadata')
            print("gdrive_metadata", gdrive_metadata)

            if not (access_token and refresh_token and client_id and client_secret and token_uri and folder_name):
                logger.error("Incomplete Google Drive upload data")
                return Response({"error": "Incomplete Google Drive upload data"}, status=status.HTTP_400_BAD_REQUEST)

            files = request.FILES.get('files')
            if not files:
                logger.error("No files provided")
                return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)
            return GoogleDrive.upload_to_gdrive(folder_name, files, gdrive_metadata, access_token, refresh_token,
                                                client_id, client_secret, token_uri)



        else:
            logger.error("Invalid drive_type")

            return Response({"error": "Invalid drive_type"}, status=status.HTTP_400_BAD_REQUEST)


class FileDownloadView(APIView):
    # parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):

        drive_type = request.data.get('drive_types')
        print("drive_type",drive_type)
        data = request.data
        print("data",data)
        if drive_type == "S3 Bucket":
            bucket_name = request.data.get('bucket_name')
            aws_access_key_id = request.data.get('aws_access_key_id')
            aws_secret_access_key = request.data.get('aws_secret_access_key')

            if not (bucket_name and aws_access_key_id and aws_secret_access_key):
                logger.error("Incomplete S3 credentials")
                return Response({"error": "Incomplete S3 credentials"}, status=status.HTTP_400_BAD_REQUEST)

            file_name = request.data.get('filename')
            if not file_name:
                logger.error("No file_name provided")
                return Response({"error": "No file_name provided"}, status=status.HTTP_400_BAD_REQUEST)
            return S3Bucket.download_from_S3Bucket(file_name, aws_access_key_id, aws_secret_access_key, bucket_name)


        elif drive_type == "Google Drive":
            access_token = request.data.get('access_token')
            refresh_token = request.data.get('refresh_token')
            client_id = request.data.get('client_id')
            client_secret = request.data.get('client_secret')
            token_uri = request.data.get('token_uri')
            folder_name = request.data.get('folder_name')

            if not (access_token and refresh_token and client_id and client_secret and token_uri and folder_name):
                logger.error("Incomplete Google Drive upload data")
                return Response({"error": "Incomplete Google Drive upload data"}, status=status.HTTP_400_BAD_REQUEST)

            file_name = request.data.get('filename')
            print("file_name",file_name)
            if not file_name:
                logger.error("No file_name provided")
                return Response({"error": "No file_name provided"}, status=status.HTTP_400_BAD_REQUEST)
            return GoogleDrive.download_from_gdrive(file_name, access_token, refresh_token, client_id, client_secret,
                                                    token_uri)



        # elif drive_type == "OneDrive":
        #     files = request.FILES.get('files')
        #     client_id = request.data.get('client_id')
        #     client_secret = request.data.get('client_secret')
        #     authority = request.data.get('authority')
        #     folder_name = request.data.get('folder_name')
        #     onedrive_metadata = request.data.get('onedrive_metadata')
        #     token_url = request.data.get('token_url')
        #     scopes = ['https://graph.microsoft.com/.default']

        #     if not (client_id and client_secret and authority and folder_name and token_url):
        #         logger.error("Incomplete OneDrive upload data")
        #         return Response({"error": "Incomplete OneDrive upload data"}, status=status.HTTP_400_BAD_REQUEST)

        #     upload_result = OneDrive.upload_to_onedrive(folder_name, files, onedrive_metadata, client_id, client_secret, authority, scopes, token_url)

        #     # if upload_result == "success":
        #     #     return Response({"message": "Files uploaded to OneDrive"}, status=status.HTTP_200_OK)
        #     # else:
        #     #     return Response({"error": "Failed to upload files to OneDrive"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            logger.error("Invalid drive_type")
            return Response({"error": "Invalid drive_type"}, status=status.HTTP_400_BAD_REQUEST)
######################## API for DMS components ends ##################################
