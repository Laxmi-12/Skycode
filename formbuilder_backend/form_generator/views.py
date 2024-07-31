"""
author : mohan
app_name : form_generator
"""
import threading
from sqlite3 import IntegrityError

import requests
from django.db import transaction
from django.urls import reverse
from django.utils.crypto import get_random_string

from .serializer import *
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes  # function based api_view decorator
from rest_framework.views import APIView  # class based APIView
from rest_framework import status  # status codes
from django.core.mail import send_mail  # mail service
from django.conf import settings  # import host user from settings.py for mail service
from django.contrib.auth import authenticate, login  # user authentication
from django.core.exceptions import ObjectDoesNotExist  # error handling
from django.shortcuts import redirect  # redirect
import traceback
# pdf imports bgn
import os
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from .models import FilledFormData  # Import your model
from reportlab.pdfgen import canvas
from reportlab.lib import colors, styles
from reportlab.graphics.shapes import Rect
from reportlab.lib.colors import Color, black, blue, red, darkblue, midnightblue, navy
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph, PageTemplate, Frame
from django.http import HttpResponse, FileResponse, JsonResponse
from reportlab.lib.styles import getSampleStyleSheet
from django.core.files.base import ContentFile
# pdf imports end
import json
from django.core.mail import EmailMessage  # mail service 2 for file attachment

from rest_framework.authtoken.models import Token  # login_authentication
from django.contrib.auth.mixins import LoginRequiredMixin  # login required decorator

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from datetime import datetime, date, time, timedelta  # add date in created date and eta date comparison
from django.shortcuts import get_object_or_404
# cron schedule imports bgn
# import datetime
# import time
import schedule
# cron schedule imports end


import logging  # log messages

from custom_components.models import Bot, BotSchema, BotData, Integration, IntegrationDetails, Organization, UserGroup, \
    Ocr, Dms, Dms_data, Ocr_Details
from custom_components.serializer import IntegrationDetailsSerializer, BotDataSerializer, OrganizationSerializer, \
    OcrSerializer, Ocr_DetailsSerializer, DmsDataSerializer
import json
from django.contrib.auth.backends import ModelBackend
import operator
from rest_framework import generics, status

from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserData
from .serializer import UserDataSerializer
from django.contrib.auth.tokens import default_token_generator

from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class FormGeneratorAPIView(APIView):
    """
    1.1
    form-generator begins here.
    Users can create multiple forms and perform actions such as retrieving, updating, and deleting them.
    """

    def get(self, request, organization_id, form_id=None):
        try:
            if form_id:
                form = FormDataInfo.objects.get(organization_id=organization_id, id=form_id)
                serializer = FormDataInfoSerializer(form)
                form_data = serializer.data

                # Get related permissions
                form_permissions = FormPermission.objects.filter(form_id=form.id).values('user_group', 'read', 'write',
                                                                                         'edit')
                form_data['permissions'] = list(form_permissions) if form_permissions else None

                return Response(form_data, status=status.HTTP_200_OK)
            else:
                forms = FormDataInfo.objects.filter(organization_id=organization_id).values()
                for form in forms:
                    form_permissions = FormPermission.objects.filter(form_id=form['id']).values('user_group', 'read',
                                                                                                'write', 'edit')
                    form['permissions'] = list(form_permissions) if form_permissions else None

                return Response(list(forms), status=status.HTTP_200_OK)
        except FormDataInfo.DoesNotExist:
            return Response({"error": "Form(s) not found for the organization"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        data = request.data

        form_name = data.get('form_name')
        form_json_schema = data.get('form_json_schema')
        form_description = data.get('form_description')
        organization_id = data.get('organization')
        user_permissions = data.get('permissions')
        print("user_permissions", user_permissions)

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        form_data_instance, created = FormDataInfo.objects.update_or_create(
            organization=organization,
            form_name=form_name,  # Add form_name to the query parameters
            defaults={
                'form_json_schema': form_json_schema,
                'form_description': form_description
            }
        )

        if user_permissions is not None:
            # Clear existing permissions to avoid duplicates
            FormPermission.objects.filter(form=form_data_instance).delete()

            # Create or update FormPermissions
            for permission in user_permissions:
                user_group_id = permission['user_group']
                read = permission['read']
                write = permission['write']
                edit = permission['edit']

                try:
                    user_group = UserGroup.objects.get(id=user_group_id)
                except UserGroup.DoesNotExist:
                    return Response({"error": f"User group with ID {user_group_id} not found"},
                                    status=status.HTTP_404_NOT_FOUND)

                FormPermission.objects.create(
                    form=form_data_instance,
                    user_group=user_group,
                    read=read,
                    write=write,
                    edit=edit
                )

        return Response({"message": "Form data and permissions saved successfully"}, status=status.HTTP_201_CREATED)

    def put(self, request, organization_id, form_id):
        data = request.data
        print("dataaaaa", data)

        try:
            form_data_instance = FormDataInfo.objects.get(pk=form_id, organization_id=organization_id)
        except FormDataInfo.DoesNotExist:
            return Response({"error": "Form data not found for the given organization and form ID"},
                            status=status.HTTP_404_NOT_FOUND)

        form_name = data.get('form_name', form_data_instance.form_name)
        form_json_schema = data.get('form_json_schema', form_data_instance.form_json_schema)
        form_description = data.get('form_description', form_data_instance.form_description)
        organization_id = data.get('organization', form_data_instance.organization.id)
        user_permissions = data.get('permissions', None)

        organization = Organization.objects.get(id=organization_id)

        form_data_instance.form_name = form_name
        form_data_instance.form_json_schema = form_json_schema
        form_data_instance.form_description = form_description
        form_data_instance.organization = organization
        form_data_instance.save()

        if user_permissions is not None:
            # Clear existing permissions to avoid duplicates
            FormPermission.objects.filter(form=form_data_instance).delete()

            # Create or update FormPermissions
            for permission in user_permissions:
                user_group_id = permission['user_group']
                read = permission['read']
                write = permission['write']
                edit = permission['edit']

                user_group = UserGroup.objects.get(id=user_group_id)

                FormPermission.objects.create(
                    form=form_data_instance,
                    user_group=user_group,
                    read=read,
                    write=write,
                    edit=edit
                )

        return Response({"message": "Form data and permissions updated successfully"}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, form_id):
        try:
            form_data_instance = FormDataInfo.objects.get(pk=form_id, organization_id=organization_id)
            form_data_instance.delete()
            return Response({"message": "Form data and permissions deleted successfully"},
                            status=status.HTTP_204_NO_CONTENT)
        except FormDataInfo.DoesNotExist:
            return Response({"error": "Form data not found for the given organization and form ID"},
                            status=status.HTTP_404_NOT_FOUND)


class UserFilledDataView(APIView):
    """
    1.2
    user filled data get,post,update and delete function
    """

    def get(self, request, pk=None):
        """
        list all the user data and can retrieve particular data
        """
        if pk is None:
            filled_data = FilledFormData.objects.all()
            serializer = FilledDataInfoSerializer(filled_data, many=True)

        else:
            filled_data = FilledFormData.objects.get(pk=pk)
            serializer = FilledDataInfoSerializer(filled_data)
        return Response(serializer.data)

    def post(self, request):  # store ths data in db
        # input = request.data
        # print("input", input)
        if request.method == 'POST':
            try:
                # Extract jsonData, formId, organization
                json_data_str = request.POST.get('jsonData', '[]')
                print(" json_data_str", json_data_str)
                form_id = request.POST.get('formId')
                print(" form_id", form_id)
                organization_id = request.POST.get('organization')
                print(" organization_id", organization_id)
                json_data = json.loads(json_data_str)
                print(" json_data_str", json_data)

                # Validate and get organization
                try:
                    organization = Organization.objects.get(id=organization_id)
                except Organization.DoesNotExist:
                    return JsonResponse({'error': 'Organization not found'}, status=404)

                # Extract the field id for file, if present in jsonData
                file = None
                for item in json_data:
                    if item.get('field_id') and item.get('value'):
                        file_field_id = item['field_id']
                        break

                if file:
                    # Handle file if present in request.FILES
                    file = None
                    for field_name, uploaded_file in request.FILES.items():
                        file = uploaded_file
                        print("file", type(file))
                        break  # Assuming only one file is expected; remove break if multiple files need handling

                    # Fetch drive types and configurations for the specific organization
                    dms_entries = Dms.objects.filter(organization=organization)

                    # drive_types = list(dms_entries.values_list('drive_types', flat=True))
                    drive_types = dms_entries.first().drive_types if dms_entries.exists() else {}

                    configurations = dms_entries.first().config_details_schema
                    print("configurations type", type(configurations))
                    # configurations.update("drive_type": drive_types)
                    configurations['drive_types'] = drive_types
                    # configurations['s3_bucket_metadata'] = drive_types
                    print("configurations-------------2", configurations)

                    metadata = {'form_id': form_id, 'organization_id': organization_id}
                    # Send file and additional data to another API if file is available
                    # Extract the file from the request
                    configurations['metadata'] = json.dumps(metadata)
                    print("configurations-------------------3", configurations)
                    # data_config = {
                    #
                    #     'drive_types': drive_types,
                    #     'bucket_name': bucket_name,
                    #     'aws_access_key_id': access_key_id,
                    #     'aws_secret_access_key': aws_secret_access_key,
                    #     's3_bucket_metadata' : json.dumps(s3_bucket_metadata)
                    #
                    #     # 'configurations': configurations
                    # }
                    # Prepare the file for the request
                    files = {'files': (file.name, file.file, file.content_type)}

                    print("inside file")
                    external_api_url = 'http://192.168.0.106:8000/custom_components/FileUploadView/'
                    response = requests.post(
                        external_api_url,
                        data=configurations, files=files

                    )
                    print("response", response)
                # Save the data to the database
                form_data = FilledFormData(
                    data_json=json_data,
                    formId=form_id,
                    organization=organization,

                )
                form_data.save()

                return JsonResponse({'status': 'success', 'form_data_id': form_data.id})

            except (json.JSONDecodeError, KeyError) as e:
                return JsonResponse({'error': 'Invalid data or missing fields'}, status=400)

        return JsonResponse({'error': 'Invalid request method'}, status=405)
        # serializer = FilledDataInfoSerializer(data=request.data)
        # if serializer.is_valid():
        #     serializer.save()
        #     return Response(serializer.data)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # if serializer.is_valid():
        #     instance = serializer.save()
        #
        #     # PDF generation begins here
        #     # Form data
        #     user_data_form_id = FilledFormData.objects.filter(pk=instance.id).values('form_id')
        #     form_id = user_data_form_id[0]['form_id']
        #     us = FormDataInfo.objects.get(pk=form_id)
        #
        #     data = {
        #         'heading': us.heading,
        #         'subheading': us.subheading,
        #         'logo': us.logo,
        #         'menu_name': us.menu_name,
        #         'form_id': form_id,
        #         'form_name': us.form_name
        #     }
        #
        #     # Filled form data
        #     user_data = FilledFormData.objects.get(pk=instance.id)
        #     try:
        #         json_data = user_data.data_json  # Parse JSON data as a dictionary
        #     except json.JSONDecodeError:
        #         return Response({'detail': 'Invalid JSON data'}, status=status.HTTP_400_BAD_REQUEST)
        #
        #     # Generate the PDF
        #     response = BytesIO()
        #
        #     # Create a PDF document
        #     # Create a canvas object
        #     pdf = canvas.Canvas(response, pagesize=letter)
        #
        #     # constants for layout
        #     page_width = letter[0]
        #     page_height = letter[1]
        #     top_nav_height = 150
        #     bottom_nav_height = 40
        #     logo_width = 220
        #     logo_height = 220
        #     margin = 15
        #     max_text_width = page_width - (2 * margin)
        #
        #     #  background color bgn
        #     # top nav bgn
        #     x = 0  # X-coordinate of the top-left corner
        #     y = 650  # Y-coordinate of the top-left corner (adjust to align the top)
        #     width = 700  # Width of the rectangle
        #     height = 200
        #     pdf.setFillColor(midnightblue)
        #     pdf.rect(0, y, width, height, fill=True, stroke=False)
        #     # top nav end
        #
        #     #  bottom nav bgn
        #     x = 0  # X-coordinate of the top-left corner
        #     y = 0  # Y-coordinate of the top-left corner (adjust to align the top)
        #     width = 700  # Width of the rectangle
        #     height = 40  # Height of the rectangle
        #     pdf.setFillColor(midnightblue)
        #     pdf.rect(x, y, width, height, fill=True, stroke=False)
        #     #  bottom nav end
        #     #  background color end
        #
        #     # image file path
        #     image_path = us.logo
        #
        #     # image in the top-left corner
        #     pdf.drawImage(image_path, margin, page_height - top_nav_height - 30, width=logo_width, height=logo_height,
        #                   preserveAspectRatio=True, mask='auto')
        #
        #     # Add heading and subheading
        #     pdf.setFont("Helvetica-Bold", 14)
        #     pdf.setFillColor(colors.white)
        #     pdf.drawString(300, page_height - top_nav_height + 80, us.heading)
        #
        #     pdf.setFont("Helvetica", 12)
        #     pdf.setFillColor(colors.white)
        #     pdf.drawString(300, page_height - top_nav_height + 60, us.subheading)
        #
        #     # pdf.setFont("Helvetica", 11)
        #     # pdf.setFillColor(colors.white)
        #     # pdf.drawString(300, page_height - top_nav_height + 100, ' REG ID : ' + str(instance.id))
        #
        #     # list to hold table data
        #     table_data = [['REG ID : ' + str(instance.id)]]
        #
        #     # JSON data to the table
        #     for key, value in json_data.items():
        #         table_data.append([key, f': {value}'])
        #
        #     # Create the table
        #     table = Table(table_data)
        #
        #     # table style
        #     table_style = TableStyle([
        #         ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        #         ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        #         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        #         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        #         ('FONTSIZE', (0, 0), (-1, 0), 15),
        #         ('BOTTOMPADDING', (0, 0), (-2, 0), 10),
        #         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        #         ('GRID', (2, 0), (0, 0), 0, colors.lightgrey),
        #     ])
        #
        #     table.setStyle(table_style)
        #
        #     # Draw table
        #     table.wrapOn(pdf, max_text_width, page_height - top_nav_height - 200)
        #     table.drawOn(pdf, margin, page_height - top_nav_height - 210)
        #
        #     # form name with a custom font size
        #     pdf.setFont("Helvetica", 15)  # font and size
        #     pdf.setFillColor(colors.white)
        #     pdf.drawString(230, 15, us.form_name)
        #
        #     # Save PDF
        #     pdf.save()
        #
        #     # pdf downloader bgn
        #     pdf_file_path = os.path.join(f"{data['form_name']}.pdf")
        #     pdf_content = response.getvalue()
        #     with open(pdf_file_path, 'wb') as pdf_file:
        #         pdf_file.write(pdf_content)
        #     # pdf downloader end
        #     # PDF generation ends here
        #
        #     # email bgn
        #     # email content
        #     subject = 'New Form Submission Received!'
        #     message = 'Hi, Thanks for getting in touch with MHA. ' \
        #               'Attached is a copy of the online form you submitted with the registration ID.' \
        #               'Please use the registration id for any further communication.' \
        #               'Thanks,' \
        #               ' MHA Admin Team'
        #     email_from = settings.EMAIL_HOST_USER
        #     recipient_email = 'mohansaravanan111@gmail.com'
        #
        #     # email Message with the PDF as an attachment
        #     email = EmailMessage(subject, message, email_from, [recipient_email])
        #     email.attach_file(pdf_file_path)  # Attach the PDF file
        #     email.send()  # Send the email
        #     # email end
        #
        #     # Return the PDF as a response
        #     response.seek(0)
        #     return FileResponse(response, content_type='application/pdf')
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):  # edit the particular filled form
        filled_data = FilledFormData.objects.get(pk=pk)
        serializer = FilledDataInfoSerializer(filled_data, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):  # delete the particular filled form
        filled_data = FilledFormData.objects.get(pk=pk)
        filled_data.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_form_data_count(request):
    """
    filled form data
    """
    form = FormDataInfo.objects.filter(form_status=True)
    response_data = []
    for f in form:
        filled_form_data = FilledFormData.objects.filter(form_id=f.pk)
        filled_form_serializer = FilledDataInfoSerializer(filled_form_data, many=True)
        response_data.extend(filled_form_serializer.data)
    return Response(response_data)


# adding this for process and case management (TWS):
class CreateProcessView(APIView):
    """
    2.1
    process begins with the use of a default JSON configuration, where users fill out an initial form.
    Subsequently, the case is generated, initiating the workflow.
    """

    def get(self, request, pk=None):
        if pk is None:
            filled_data = CreateProcess.objects.all().values('id', 'process_name')
            return Response(filled_data)
        elif pk is not None:
            # get the process id
            try:
                id_based_form_record = CreateProcess.objects.get(pk=pk)
                print("id_based_form_record ", id_based_form_record)
                organization = id_based_form_record.organization
                print("organization", organization.id)
            except CreateProcess.DoesNotExist:
                return Response({'error': 'Process not found'}, status=status.HTTP_404_NOT_FOUND)

            # target_form_name = id_based_form_record.first_step  # initial form
            # print("target_form_name",target_form_name)

            process_data = id_based_form_record.participants  # get overall json form data

            # # Load JSON data
            # parsed_data = json.loads(process_data)

            # Extract the first currentStepId from flow_1 in the executionFlow
            first_current_step_id = process_data["executionFlow"]["flow_1"]["currentStepId"]

            form = FormDataInfo.objects.filter(Form_uid=first_current_step_id).first()
            # ocr = Ocr.objects.filter(ocr_uid=first_current_step_id).first()
            # print("ocrdddddddddddddddddddddd",ocr)
            # if ocr:
            #     print('--- OCR starts --- 1')
            if form:
                print('--- Activity starts --- 1')
                form_id_ref = form.id
                print("form_id_ref", form_id_ref)
                form_input_data = form.form_json_schema

                # Convert the string representation of the JSON array into a JSON object
                # json_data = json.loads(form_input_data)

                return Response(form_input_data)

            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk=None):

        global dms_data
        if pk is None:
            process_data = CreateProcess.objects.all()
        elif pk is not None:
            # get the process id
            id_based_form_record = CreateProcess.objects.get(pk=pk)
            organization_id = id_based_form_record.organization.id
            print("organization_iddddddddddddddddddddddddddd", organization_id)

            if not id_based_form_record:
                return Response({'error': 'Process not found'}, status=status.HTTP_404_NOT_FOUND)

            # target_form_name = id_based_form_record.first_step  # Initial form
            process_data = id_based_form_record.participants  # get overall json form data
            process_id = id_based_form_record.pk
            print("process_id", process_id)
            # Load JSON data
            # parsed_data = json.loads(process_data)
            # Get the first key in the executionFlow dictionary
            first_key = next(iter(process_data["executionFlow"]))

            flows = []
            # Iterate over the executionFlow to get currentStepId and nextStepId
            for flow_key, flow_value in process_data["executionFlow"].items():
                print(f"Processing flow: {flow_key}")
                start_form_id = flow_value["currentStepId"]
                end_form_id = flow_value["nextStepId"]
                flows.append({"start": start_form_id, "end": end_form_id})

                # field data (request)
                userId = None  # request.data['userId']

                if 'data_json' in request.data and request.data['data_json']:
                    data_json_str = request.data['data_json']
                    print("data_json_str", data_json_str)
                    data_json = json.loads(data_json_str)
                    print(" json_data_str", data_json)

                    # Extract the field id for file, if present in jsonData
                    file_field_id = None
                    for item in data_json:
                        if item.get('field_id') and item.get('value'):
                            file_field_id = item['field_id']
                            break
                    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
                    # Handle file if present in request.FILES
                    file = None
                    for field_name, uploaded_file in request.FILES.items():
                        file = uploaded_file
                        print("file", type(file))
                        break  # Assuming only one file is expected; remove break if multiple files need handling

                    # Prepare the file for the request

                    if file:
                        # Fetch drive types and configurations for the specific organization
                        dms_entries = Dms.objects.filter(organization=organization_id)
                        # drive_types = list(dms_entries.values_list('drive_types', flat=True))
                        drive_types = dms_entries.first().drive_types if dms_entries.exists() else {}

                        configurations = dms_entries.first().config_details_schema
                        print("configurations type", type(configurations))
                        # configurations.update("drive_type": drive_types)
                        configurations['drive_types'] = drive_types
                        # configurations['s3_bucket_metadata'] = drive_types
                        print("configurations", configurations)

                        metadata = {'form_id': start_form_id, 'organization_id': organization_id}
                        # Send file and additional data to another API if file is available
                        # Extract the file from the request
                        configurations['metadata'] = json.dumps(metadata)
                        print("configurations", configurations)
                        print("inside file")
                        files = {'files': (file.name, file.file, file.content_type)}
                        external_api_url = 'http://192.168.0.106:8000/custom_components/FileUploadView/'
                        response = requests.post(
                            external_api_url,
                            data=configurations, files=files

                        )
                        print("response", response)
                        if response.status_code == 200:
                            # responses.append(response.json())  # Store the response
                            response_json = response.json()
                            print("response_json", response_json)
                            file_name = response_json.get('file_name')
                            file_id = response_json.get('file', {}).get('id')

                            print("File Name:", file_name)
                            print("File ID:", file_id)
                            try:
                                organization_instance = Organization.objects.get(id=organization_id)
                            except Organization.DoesNotExist:
                                # Handle the case where the organization does not exist
                                organization_instance = None
                            try:
                                process_instance = CreateProcess.objects.get(id=process_id)
                            except Organization.DoesNotExist:
                                # Handle the case where the organization does not exist
                                organization_instance = None
                            try:
                                dms_data, created = Dms_data.objects.get_or_create(
                                    folder_id=file_id,
                                    filename=file_name,
                                    case_id=None,
                                    flow_id=process_instance,

                                    organization=organization_instance,
                                    defaults={'meta_data': configurations['metadata']}
                                )

                            except Exception as e:
                                print("Error during get_or_create:", e)

                                # Print details of integration_data to see if it is None or has unexpected values
                            if dms_data is None:
                                print("dms_data is None")
                            else:
                                print(f"dms_data details: {dms_data.__dict__}")

                                # If BotData was found, update the data_schema field
                            if not created:
                                try:
                                    dms_data.meta_data = dms_data
                                    dms_data.save()  # Ensure you call save on the correct object

                                except Exception as e:
                                    print("Error during integration_data save:", e)

                            # responses.append(response_json)

                    # data_json = data_json_str
                    form_status = "In Progress"
                    caseId = None  # request.data['caseId']
                    process_id = id_based_form_record.pk
                    print("process_id ", process_id)

                    Filled_data_json = {
                        'formId': start_form_id,
                        'userId': userId,
                        'processId': process_id,
                        'data_json': data_json,  # json list (need to change)
                        'caseId': caseId,
                        'status': form_status,
                        'organization': organization_id
                    }

                    # FilledFormData
                    serializer = FilledDataInfoSerializer(data=Filled_data_json)

                    if serializer.is_valid():
                        instance = serializer.save()

                        # Case field data (caseSerializer request)
                        today = str(date.today())
                        created_on = today  # request.data.get('created_on', today)
                        created_by = 'admin'  # request.data.get('created_by', 'admin')
                        updated_on = today  # request.data.get('updated_on', today)
                        updated_by = ''  # request.data.get('updated_by', '')
                        process_id = id_based_form_record.pk
                        # Store filled form id in case as json (array)
                        filled_form_id = instance.pk
                        filled_form_ids = [filled_form_id]
                        filled_form_id_data = filled_form_ids
                        filled_form_id_data_json = json.dumps(filled_form_id_data)

                        # Case field data
                        data_json = {
                            'processId': process_id,
                            'organization': organization_id,
                            'created_on': created_on,
                            'created_by': created_by,
                            'status': 'In Progress',
                            'updated_on': updated_on,
                            'updated_by': updated_by,
                            'next_step': '',
                            'data_json': filled_form_id_data_json,  # json list (need to change)
                            'path_json': ''
                        }

                        # Case
                        case_serializer = CaseSerializer(data=data_json)

                        if case_serializer.is_valid():
                            print('if works---')
                            case_instance = case_serializer.save()
                            print('case_instance--', case_instance)

                            # Apply rule bgn
                            # current filled form data (for apply rule) bgn
                            filled_form_data = FilledFormData.objects.filter(pk=instance.pk).first()
                            filled_form_data_schema_form_id = filled_form_data.formId
                            print('filled_form_data_schema_form_id----', filled_form_data_schema_form_id)

                            actual_data = None

                            print('++++++++++++++++++++++++ BGN 1++++++++++++++++++++++++')

                            start = []

                            for flow_key, flow_value in process_data["executionFlow"].items():
                                # start_value = flow_value.get("currentStepId")
                                # end_value = flow_value.get("nextStepId")
                                start_value = flow_value["currentStepId"]
                                print("start_value", start_value)
                                end_value = flow_value["nextStepId"]

                                print(f"--------Start: {start_value}, ---------End: {end_value}")
                                break

                            case_instance.next_step = end_value
                            case_instance.save()

                            # 3. Update the Dms_data instance with the new case_id
                            dms_data.case_id = case_instance

                            # 4. Save the Dms_data instance to update the record in the database
                            dms_data.save()

                            # Verify the updated next_step
                            updated_case = Case.objects.get(pk=case_instance.pk)
                            print("Updated next_step:", updated_case.next_step)

                            print('+++++++++++++++++++++++ END 1+++++++++++++++++++++++++')
                            # find where end form stored in participants from json data  end
                            # Apply rule end

                            # store case id in filled form
                            get_case_id = case_instance.pk
                            print('get_case_id---', get_case_id)
                            submitted_form_queryset = FilledFormData.objects.filter(pk=instance.pk)
                            print('submitted_form_queryset---1', submitted_form_queryset)

                            # Update the attributes of the retrieved object
                            submitted_form_queryset.update(caseId=get_case_id, status="Completed")

                            # Get the first object from the queryset (assuming there's only one)
                            submitted_form_instance = submitted_form_queryset.first()
                            print('submitted_form_instance---2', submitted_form_instance)

                            # Access the formId attribute of the retrieved object
                            get_form_schema_id = submitted_form_instance.formId
                            print('get_form_schema_id--3', get_form_schema_id)

                            # Update the case id in DMS

                            print('+++++++++++++++++++++++ END 2+++++++++++++++++++++++++')

                            trigger_url = f"http://192.168.0.106:8000/process_related_cases/{get_case_id}/"
                            payload = {'case_id': get_case_id}  # Adjust the payload as needed

                            try:
                                trigger_response = requests.post(trigger_url, data=payload)
                                print("trigger_response ", trigger_response)
                                trigger_response.raise_for_status()
                                if trigger_response.status_code == 200:
                                    print("Successfully triggered the URL")
                                else:
                                    print(f"Failed to trigger the URL, status code: {trigger_response.status_code}")
                            except requests.RequestException as e:
                                # Log the error message
                                print(f"An error occurred while triggering the URL: {e}")
                                # Return an error response
                                return Response({'error': 'Failed to trigger the URL', 'details': str(e)},
                                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                            #
                            # # if updated_case
                            # Trigger the get_case_related_forms URL after returning the case_id
                            response = Response({'id': case_instance.pk}, status=status.HTTP_201_CREATED)
                            return response

            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


############################## to display case related data ######################################


class CaseDetailView(APIView):

    def get(self, request, organization_id, process_id, case_id):
        try:
            # Fetch the specific case
            case = Case.objects.get(id=case_id, organization_id=organization_id, processId=process_id)
        except Case.DoesNotExist:
            return Response({'error': 'Case not found'}, status=404)

        # Fetch filled form data associated with this case
        filled_form_data = FilledFormData.objects.filter(caseId=case_id, organization_id=organization_id,
                                                         processId=process_id)

        if filled_form_data.exists():
            # Serialize the case
            case_data = CaseSerializer(case).data

            # Retrieve form details and append to filled form data
            filled_form_data_list = []
            for filled_data in filled_form_data:
                form_id = str(filled_data.formId)

                form_info = FormDataInfo.objects.filter(Form_uid=form_id).first()
                filled_data_serialized = FilledDataInfoSerializer(filled_data).data
                if form_info:
                    filled_data_serialized['form_name'] = form_info.form_name
                    filled_data_serialized['form_description'] = form_info.form_description
                filled_form_data_list.append(filled_data_serialized)
        else:
            return Response({'error': 'No filled form data found for this case'}, status=404)
        # Fetch and serialize bot data
        bot_data = BotData.objects.filter(case_id=case_id, organization=organization_id, flow_id=process_id)
        if bot_data.exists():
            serialized_bot_data = BotDataSerializer(bot_data, many=True).data
        else:
            serialized_bot_data = []

        # Fetch and serialize integration data
        integration_data = IntegrationDetails.objects.filter(case_id=case_id, organization=organization_id,
                                                             flow_id=process_id)
        if integration_data.exists():
            serialized_integration_data = IntegrationDetailsSerializer(integration_data, many=True).data
        else:
            serialized_integration_data = []

        # Fetch and serialize OCR data
        ocr_data = Ocr_Details.objects.filter(case_id=case_id, organization=organization_id,
                                              flow_id=process_id)
        if ocr_data.exists():
            serialized_ocr_data = Ocr_DetailsSerializer(ocr_data, many=True).data
        else:
            serialized_ocr_data = []

        # Fetch and serialize DMS data
        dms_data_qs = Dms_data.objects.filter(case_id=case_id, organization=organization_id,
                                              flow_id=process_id)
        if dms_data_qs.exists():
            serialized_dms_data = DmsDataSerializer(dms_data_qs, many=True).data
        else:
            serialized_dms_data = []

            response_data = {
                'case': case_data,
                'filled_form_data': filled_form_data_list,
                'bot_data': serialized_bot_data,
                'integration_data': serialized_integration_data,
                'ocr_data': serialized_ocr_data,
                'dms_data': serialized_dms_data,
            }
            return Response(response_data)


############################## case releted data ends ################################################


class CaseRelatedFormView(APIView):
    """
    getting case related filled form and form schema
    """

    def get(self, request, organization_id, process_id, pk=None):
        if pk is None:
            cases = Case.objects.filter(organization_id=organization_id, processId=process_id)
            serializer = CaseSerializer(cases, many=True)
            serialized_data = serializer.data

            for data_item in serialized_data:
                data_json_ids = [int(id.strip()) for id in data_item['data_json'].strip('[]').split(',') if
                                 id.strip().isdigit()]
                data_json_id = data_json_ids[0] if data_json_ids else None

                try:
                    filled_form_data = FilledFormData.objects.get(pk=data_json_id)
                except FilledFormData.DoesNotExist:
                    filled_form_data = None

                dt = FilledDataInfoSerializer(filled_form_data).data
                data_json_value = dt.get('data_json', None)
                data_item['data_json'] = data_json_value

            return Response(serializer.data)
        else:
            try:
                case = Case.objects.get(pk=pk, organization_id=organization_id, processId=process_id)
            except Case.DoesNotExist:
                return Response({'error': 'Case not found'}, status=404)

            next_step = case.next_step
            print("next_step", next_step)

            try:
                form_json_schema = FormDataInfo.objects.get(Form_uid=next_step, organization=organization_id,
                                                            processId=process_id)
            except FormDataInfo.DoesNotExist:
                form_json_schema = None

            try:
                ocr_data = Ocr.objects.get(ocr_uid=next_step, organization=organization_id, flow_id=process_id)
            except Ocr.DoesNotExist:
                ocr_data = None

            # Initialize response data with case information
            response_data = {
                'caseid': case.id,
                'createdby': case.created_by,
                'createdon': case.created_on,
                'updatedon': case.updated_on,
                'updatedby': case.updated_by,
                'status': case.status,
            }

            # Include OCR data if it exists
            if ocr_data:
                ocr_data_list = Ocr.objects.filter(organization=organization_id, flow_id=process_id)
                serializer = OcrSerializer(ocr_data_list, many=True)
                response_data['ocr_schema'] = serializer.data[0]  # Assuming only one OCR schema is needed

            # Include form data if it exists
            elif form_json_schema:
                response_data['form_schema'] = form_json_schema.form_json_schema

            # If neither OCR nor form data is present, include form and bot data if available
            else:
                cs_id = case.id
                form_schema22 = FilledFormData.objects.filter(caseId=cs_id)
                bot_data = BotData.objects.filter(case_id=cs_id)
                bot_names = [bot_data.bot.bot_name for bot_data in bot_data]

                integration_data = IntegrationDetails.objects.filter(case_id=cs_id)
                integration_names = [integration_data.integration.integration_type for integration_data in
                                     integration_data]
                ocr_data = Ocr_Details.objects.filter(case_id=cs_id)
                ocr_names = [ocr_data.ocr.ocr_type for ocr_data in
                             ocr_data]
                dms_data_qs = Dms_data.objects.filter(case_id=cs_id)
                dms_names = [dms.dms.drive_types for dms in dms_data_qs if dms.dms is not None]

                serialized_bot_data = BotDataSerializer(bot_data, many=True).data
                serialized_integration_data = IntegrationDetailsSerializer(integration_data, many=True).data
                serialized_dms_data = DmsDataSerializer(dms_data_qs, many=True).data
                serialized_ocr_data = Ocr_DetailsSerializer(ocr_data, many=True).data

                form_data_list = []
                form_schemas = []
                for form_data_id in form_schema22:
                    f_id = form_data_id.formId
                    form_data = FormDataInfo.objects.filter(Form_uid=f_id).first()
                    if form_data:
                        serializer = FormDataInfoSerializer(form_data)
                        form_data_list.append(serializer.data)
                    form_schemas.append(form_data_id)

                if form_schemas:
                    serializer_data = FilledDataInfoSerializer(form_schemas, many=True)

                    response_data.update({
                        'form_schema': form_json_schema,
                        # 'data_schema': data_schema,
                        'form_data_list': form_data_list,
                        'bot_data': serialized_bot_data,
                        'integration_data': serialized_integration_data,
                        'dms_data': serialized_dms_data,
                        'ocr_data': serialized_ocr_data
                    })
                else:
                    return Response({'error': 'No form data found for this case'}, status=404)

            return Response(response_data)

    def post(self, request, pk=None):
        return self.handle_case_step(request, pk)

    def handle_case_step(self, request, pk):
        global responses, dms_data
        try:
            case = Case.objects.get(pk=pk)
            process_id = case.processId
            case_id = case.id
            organization_name = case.organization
            organization_id = organization_name.id
            print("organization_id", organization_id)

            # get next step 'start' and 'end' from participants json schema BGN
            cs_next_step = case.next_step
            print("cs_next_step", cs_next_step)
            process_data = CreateProcess.objects.get(pk=process_id.pk)
            participants_data = process_data.participants
            # parsed_data = json.loads(participants_data)
            execution_flow = participants_data.get('executionFlow', [])
            steps = {flow['currentStepId']: flow for flow in execution_flow.values()}
            print("steps", steps)

            # Load JSON data

            # Get the first key in the executionFlow dictionary
            first_key = next(iter(participants_data["executionFlow"]))

            flows = []
            # Iterate over the executionFlow to get currentStepId and nextStepId
            for flow_key, flow_value in participants_data["executionFlow"].items():
                print(f"Processing flow: {flow_key}")
                if cs_next_step.strip() == flow_value.get("currentStepId"):
                    start_form_id = flow_value.get("currentStepId")
                    end_form_id = flow_value.get("nextStepId")
                    if start_form_id and end_form_id:
                        flows.append({"start": start_form_id, "end": end_form_id})

                    # start_form_id = flow_value["currentStepId"]
                    # end_form_id = flow_value["nextStepId"]
                    # flows.append({"start": start_form_id, "end": end_form_id})

                    print("Flows:", flows)
            if not flows:
                return Response({"message": "No flows found for the given next step"},
                                status=status.HTTP_400_BAD_REQUEST)

            current_step_id = flows[0]['start']
            next_step_id = flows[0]['end']

            ############ execution flow modified according to case[starts] by Praba###############

            responses = []  # List to store responses by Praba
            while current_step_id and current_step_id != "null":
                current_step = steps.get(current_step_id)
                if not current_step:
                    break
                # Check if current step ID corresponds to a bot or integration
                bot = Bot.objects.filter(bot_uid=current_step_id).first()
                integrations = Integration.objects.filter(Integration_uid=current_step_id)

                # Check if current step ID corresponds to a form or rule
                form = FormDataInfo.objects.filter(Form_uid=current_step_id).first()
                # Check if current step ID corresponds to a rule
                rule = Rule.objects.filter(ruleId=current_step_id).first()
                # Check if current step ID corresponds to a OCR
                ocr = Ocr.objects.filter(ocr_uid=current_step_id).first()

                if bot:
                    bot_schema = get_object_or_404(BotSchema, bot=bot)  # Assuming using the first one
                    bot_type = bot.bot_name
                    bot_id_ref = bot.id

                    bot_input_data = bot_schema.bot_schema_json
                    # if isinstance(bot_input_data, str):
                    #     bot_input_data = json.loads(bot_input_data)  # Ensure JSON string is parsed

                    dynamic_input_data = request.data.get(current_step_id, {})
                    input_data = {**bot_input_data, **dynamic_input_data}

                    if bot_type == 'google_drive':
                        print('--- GOOGLE DRIVE --- 1')
                        payload = {
                            'folder_id': input_data['folder_id'],
                            'file_type': input_data['file_type'],
                            'completed_folder_id': input_data['completed_folder_id']
                        }
                        url = settings.BASE_URL + reverse('drive_files_api')  # base URL + endpoint using reverse

                        try:
                            response = requests.post(url, json=payload)  # POST request with the payload as JSON data
                            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
                        except requests.exceptions.RequestException as e:
                            print(f"HTTP Request failed: {e}")
                            responses.append({'error': 'Failed to execute Google Drive bot'})
                        else:
                            response_data = response.json()

                            # Extracting data from the response
                            file_name = response_data.get('file_name')
                            file_id = response_data.get('file_id')
                            temp_data = response_data.get('temp_data')

                            if not (file_name and file_id and temp_data):
                                print("Incomplete response data")
                                responses.append({'error': 'Incomplete response data from Google Drive bot'})
                            else:
                                print("case.id", case.id)
                                print("flow_id", process_data.id)

                                # Check if BotData exists, if not create a new one
                                try:
                                    bot_data, created = BotData.objects.get_or_create(
                                        case_id=case,
                                        flow_id=process_data,
                                        organization=organization_id,
                                        defaults={'file_name': file_name,
                                                  'file_id': file_id,
                                                  'temp_data': temp_data}
                                    )

                                    print("created:", created)
                                except Exception as e:
                                    print("Error during get_or_create:", e)
                                    responses.append({'error': 'Database error during get_or_create'})
                                    return

                                if not created:
                                    try:
                                        bot_data.file_name = file_name
                                        bot_data.file_id = file_id
                                        bot_data.temp_data = temp_data
                                        bot_data.save()
                                        responses.append(response_data)  # Ensure you call save on the correct object
                                        print("bot_data updated successfully")
                                    except Exception as e:
                                        print("Error during bot_data save:", e)
                                        responses.append({'error': 'Database error during save'})
                        # else:
                        #     responses.append({'error': 'Invalid bot type'})

                    elif bot_type == 'file_extractor':
                        print('--- FILE EXTRACTOR --- 2')
                        file_extractor_bots = Bot.objects.filter(bot_name='file_extractor', bot_uid=current_step_id)
                        print("file_extractor_bots", file_extractor_bots)
                        if file_extractor_bots:
                            for file_extractor_bot in file_extractor_bots:
                                bot_schemas = BotSchema.objects.filter(bot=file_extractor_bot)

                                if bot_schemas:
                                    for bot_schema in bot_schemas:
                                        file_extractor_input_data = bot_schema.bot_schema_json
                                        # if isinstance(file_extractor_input_data, str):
                                        #     file_extractor_input_data = json.loads(file_extractor_input_data)
                                        file_name = file_extractor_input_data['file_name']

                                        # Fetch the file from the database
                                        try:
                                            bot_data_entry = BotData.objects.get(file_name=file_name, case_id=case_id,
                                                                                 flow_id=process_data,
                                                                                 organization=organization_id)

                                        except BotData.DoesNotExist:
                                            logger.error(f'File not found in the database: {file_name}')
                                            return JsonResponse(
                                                {"error": f"File not found in the database: {file_name}"}, status=404)

                                        # Construct the file path
                                        file_path = os.path.join(settings.MEDIA_ROOT, bot_data_entry.temp_data.name)

                                        logger.debug(f"File path: {file_path}")  # Debug statement

                                        if not os.path.exists(file_path):
                                            logger.error(f'File path does not exist: {file_path}')
                                            return JsonResponse({"error": f"File path does not exist: {file_path}"},
                                                                status=404)

                                        # Merge dynamic input data
                                        file_extractor_input_data = {**file_extractor_input_data, **dynamic_input_data}

                                        payload = {
                                            'file_name': file_extractor_input_data['file_name'],
                                            'sheet_name': file_extractor_input_data.get('sheet_name'),
                                            'column_definitions': file_extractor_input_data['column_definitions'],
                                            'file_path': file_path

                                        }

                                        url = settings.BASE_URL + reverse('convert_excel_to_json')

                                        response = requests.post(url, json=payload)

                                        if response.status_code == 200:

                                            response_json = response.json()  # Get the JSON response
                                            data = response_json.get('data')  # Extract 'data' from the response

                                            bot_data = get_object_or_404(BotData,
                                                                         id=bot_data_entry.id)  # Replace with the correct identifier

                                            bot_data.data_schema = data  # Update the data_schema with the new data
                                            # bot_data.case_id = case  # Update the case_id
                                            bot_data.bot_id = bot_id_ref  # Update the bot_id
                                            bot_data.save()  # Save the updated BotData instance
                                            responses.append(response_json)  # Store the response
                                        else:
                                            print("Failed to get response from convert_excel_to_json function:",
                                                  response.text)
                                else:
                                    print('Bot schema not found for file extractor bot:', file_extractor_bot)
                        else:
                            print('File extractor bot not found with UID:', current_step_id)

                        # return responses
                    elif bot_type == 'screen_scraping':
                        print('--- SCREEN SCRAPING --- 4')

                        screen_scraping_bot = get_object_or_404(Bot, bot_uid=current_step_id)
                        print("screen_scraping_bot", screen_scraping_bot)

                        # api_config = screen_scraping_bot.bot_schema_json
                        # print('api_config---', api_config)

                        bot_schema = get_object_or_404(BotSchema, bot=screen_scraping_bot)

                        schema_config = bot_schema.bot_schema_json

                        # Initialize combined_data as an empty dictionary
                        try:
                            bot_data_entries = BotData.objects.filter(case_id=pk)
                            input_data_bot = {}
                            if bot_data_entries.exists():
                                for entry in bot_data_entries:
                                    data_schema = entry.data_schema
                                    print("data_schema:", data_schema)
                                    if isinstance(data_schema, list):
                                        for item in data_schema:
                                            if isinstance(item, dict):
                                                input_data_bot.update({item['field_id']: item['value']})
                                            else:
                                                print(f"Warning: Non-dictionary item in data_schema list: {item}")
                                    elif isinstance(data_schema, dict):
                                        input_data_bot.update({data_schema['field_id']: data_schema['value']})
                                    else:
                                        print(
                                            f"Warning: BotData entry {entry.id} has a non-list, non-dict data_schema: {data_schema} (type: {type(data_schema)})")
                            print("input_data_bot:", input_data_bot)
                        except BotData.DoesNotExist:
                            print(f"No BotData found for case_id {pk}")
                            input_data_bot = {}

                            # Attempt to fetch IntegrationDetails, handle if not found
                        try:
                            integration_data_entries = IntegrationDetails.objects.filter(case_id=pk)
                            input_data_api = {}
                            if integration_data_entries.exists():
                                for entry in integration_data_entries:
                                    data_schema = entry.data_schema
                                    if isinstance(data_schema, list):
                                        for item in data_schema:
                                            if isinstance(item, dict):
                                                input_data_api.update({item['field_id']: item['value']})
                                            else:
                                                print(f"Warning: Non-dictionary item in data_schema list: {item}")
                                    else:
                                        print(
                                            f"Warning: IntegrationDetails entry {entry.id} has a non-list data_schema: {data_schema} (type: {type(data_schema)})")
                            print("input_data_api:", input_data_api)
                        except IntegrationDetails.DoesNotExist:
                            print(f"No IntegrationDetails found for case_id {pk}")
                            input_data_api = {}

                            # Combine input data if both are available
                        if input_data_bot and input_data_api:
                            combined_data = {**input_data_bot, **input_data_api}
                        elif input_data_bot:
                            combined_data = input_data_bot
                        elif input_data_api:
                            combined_data = input_data_api
                        else:
                            combined_data = {}

                        print("combined_data", combined_data)
                        # Convert combined_data list to the desired list format

                        payload = {
                            'schema_config': [schema_config],
                            'input_data': [combined_data],
                        }
                        payload_json_bytes = json.dumps(payload)
                        print("payload_json_bytes", payload_json_bytes)

                        url = settings.BASE_URL + reverse('screen_scraping')
                        response = requests.post(url, json=payload_json_bytes)
                        print("response", response)

                        if response.status_code == 200:
                            response_json = response.json()
                            botdata = response_json.get('data')  # Extract 'data' from the response

                            try:
                                bot_data, created = BotData.objects.get_or_create(
                                    bot=bot,
                                    case_id=case,
                                    flow_id=process_data,
                                    organization=organization_id,
                                    defaults={'data_schema': botdata}
                                )
                                print(" botdata:", botdata)
                                print("created:", created)
                            except Exception as e:
                                print("Error during get_or_create:", e)

                            if bot_data is None:
                                print("response_data is None")
                            else:
                                print(f"response_data details: {bot_data.__dict__}")

                                # If BotData was found, update the data_schema field
                            if not created:
                                try:
                                    bot_data.data_schema = bot_data
                                    bot_data.save()  # Ensure you call save on the correct object
                                    print("Updated integration_data successfully")
                                except Exception as e:
                                    print("Error during integration_data save:", e)

                            responses.append(response_json)

                            # responses.append(
                            #     {"bot": bot.bot_name,
                            #      "message": "Screen scraping executed"})  # Store the required message
                        else:
                            responses.append({'error': 'Failed to execute Screen Scraping bot'})

                        print(' ---- screen_scraping_executed ---')

                    else:
                        return Response({"error": f"Unsupported bot type: {bot_type}"},
                                        status=status.HTTP_400_BAD_REQUEST)


                elif integrations:
                    for integration in integrations:
                        integration_type = integration.integration_type

                        integration_id_ref = integration.id

                        integration_input_data = integration.integration_schema

                        if isinstance(integration_input_data, str):
                            integration_input_data = json.loads(integration_input_data)  # Ensure JSON string is parsed

                        dynamic_input_data = request.data.get(current_step_id, {})

                        # input_data = {**integration_input_data, **dynamic_input_data}
                        # print("input_data", input_data)
                        if integration_type == 'api':
                            print('--- API INTEGRATION --- 3')

                            integration_obj = get_object_or_404(Integration,
                                                                Integration_uid=integration.Integration_uid)
                            integration_schema = integration_obj.integration_schema

                            # if isinstance(integration_obj.data_schema, str):
                            #     integration_schema = json.loads(integration_obj.integration_schema)
                            #     print("integration_schema",integration_schema)
                            # else:
                            #     integration_schema = integration_obj.data_schema

                            try:
                                bot_data_entries = BotData.objects.filter(case_id=pk)
                                input_data_bot = {}
                                if bot_data_entries.exists():
                                    for entry in bot_data_entries:
                                        data_schema = entry.data_schema

                                        if isinstance(data_schema, list):
                                            for item in data_schema:
                                                if isinstance(item, dict):
                                                    input_data_bot.update({item['field_id']: item['value']})
                                                else:
                                                    print(f"Warning: Non-dictionary item in data_schema list: {item}")
                                        else:
                                            print(
                                                f"Warning: BotData entry {entry.id} has a non-list data_schema: {data_schema} (type: {type(data_schema)})")
                                print("input_data_bot:", input_data_bot)
                            except BotData.DoesNotExist:
                                print(f"No BotData found for case_id {pk}")
                                input_data_bot = {}

                            # Attempt to fetch IntegrationDetails, handle if not found
                            try:
                                integration_data_entries = IntegrationDetails.objects.filter(case_id=pk)
                                input_data_api = {}
                                if integration_data_entries.exists():
                                    for entry in integration_data_entries:
                                        data_schema = entry.data_schema
                                        if isinstance(data_schema, list):
                                            for item in data_schema:
                                                if isinstance(item, dict):
                                                    input_data_api.update({item['field_id']: item['value']})
                                                else:
                                                    print(f"Warning: Non-dictionary item in data_schema list: {item}")
                                        else:
                                            print(
                                                f"Warning: IntegrationDetails entry {entry.id} has a non-list data_schema: {data_schema} (type: {type(data_schema)})")
                                print("input_data_api:", input_data_api)
                            except IntegrationDetails.DoesNotExist:
                                print(f"No IntegrationDetails found for case_id {pk}")
                                input_data_api = {}

                            # Combine input data if both are available
                            if input_data_bot and input_data_api:
                                combined_data = {**input_data_bot, **input_data_api}
                            elif input_data_bot:
                                combined_data = input_data_bot
                            elif input_data_api:
                                combined_data = input_data_api
                            else:
                                combined_data = {}

                            # Convert combined_data list to the desired list format
                            # formatted_combined_data = [
                            #     {"field_id": key, "value": value, "value_type": "String"}
                            #     for key, value in combined_data.items()
                            # ]
                            # print("formatted_combined_data", formatted_combined_data)

                            input_data_dict = {
                                "input_data": [combined_data],
                                "schema_config": integration_schema,

                            }

                            url = settings.BASE_URL + reverse('api_integration')
                            print("url", url)
                            payload = input_data_dict

                            payload_json_bytes = json.dumps(payload)
                            print("payload_json_bytes", payload_json_bytes)

                            # print("payload_json_bytes##############################", response)
                            response = requests.post(url, data=payload_json_bytes)  # api call
                            print("response", response)
                            if response.status_code == 200:
                                # responses.append(response.json())  # Store the response
                                response_json = response.json()
                                integrationdata = response_json.get('data')  # Extract 'data' from the response
                                try:
                                    organization_instance = Organization.objects.get(id=organization_id)
                                except Organization.DoesNotExist:
                                    # Handle the case where the organization does not exist
                                    organization_instance = None
                                # Check if BotData exists, if not create a new one
                                try:
                                    integration_data, created = IntegrationDetails.objects.get_or_create(
                                        integration_id=integration_obj.id,
                                        case_id=case,
                                        flow_id=process_data,
                                        organization=organization_instance,
                                        defaults={'data_schema': integrationdata}
                                    )

                                except Exception as e:
                                    print("Error during get_or_create:", e)

                                    # Print details of integration_data to see if it is None or has unexpected values
                                if integration_data is None:
                                    print("integration_data is None")
                                else:
                                    print(f"integration_data details: {integration_data.__dict__}")

                                    # If BotData was found, update the data_schema field
                                if not created:
                                    try:
                                        integration_data.data_schema = integrationdata
                                        integration_data.save()  # Ensure you call save on the correct object

                                    except Exception as e:
                                        print("Error during integration_data save:", e)

                                responses.append(response_json)
                                print("API Integration successful")
                            else:
                                print("Failed to execute API integration:", response.text)
                                return response.append(
                                    {
                                        "error": f"Failed to execute {integration_type} integration. Response: {response.text}"},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                elif form:
                    # form_schema = get_object_or_404(FormDataInfo, Form_uid=form.Form_uid)
                    # integration_type = integration.integration_type
                    print('--- Activity starts --- ')

                    # Convert the form UID to string
                    form_id_ref = str(form.Form_uid)
                    print("form_id_ref:", form_id_ref)

                    # Attempt to retrieve the form JSON schema using the form UID
                    try:
                        form_json_schema = FormDataInfo.objects.get(Form_uid=form_id_ref)
                        print("form_json_schema:", form_json_schema)
                    except FormDataInfo.DoesNotExist:
                        form_json_schema = None
                    if isinstance(process_data, CreateProcess):
                        process_id = process_data.id
                        print("Extracted process_id:", process_id)
                    else:
                        print("process_data is not an instance of CreateProcess")

                    if form_json_schema:
                        form_schema = form_json_schema.form_json_schema
                        print("form_schema:", form_schema)
                        response_data = {
                            'caseid': case.id,
                            'processId': process_id,
                            'organization': organization_id,
                            'createdby': case.created_by,
                            'createdon': case.created_on,
                            'updatedon': case.updated_on,
                            'updatedby': case.updated_by,
                            'form_schema': form_schema,
                            'status': case.status
                        }
                        print("response_data", response_data)

                        # Check if form data is provided to be filled
                        if 'data_json' in request.data and request.data['data_json']:
                            data_json_str = request.data['data_json']
                            organization_id_value = request.data['organization']
                            print("organization_id", organization_id_value)

                            data_json = json.loads(data_json_str)
                            print("json_data_str", data_json)

                            # Extract the field id for file, if present in jsonData
                            file_field_id = None
                            for item in data_json:
                                if item.get('field_id') and item.get('value'):
                                    file_field_id = item['field_id']
                                    break

                            # Handle file if present in request.FILES
                            file = None
                            for field_name, uploaded_file in request.FILES.items():
                                file = uploaded_file
                                print("file", type(file))
                                break  # Assuming only one file is expected; remove break if multiple files need handling

                            if file:
                                # Fetch drive types and configurations for the specific organization
                                dms_entries = Dms.objects.filter(organization=organization_id)
                                drive_types = dms_entries.first().drive_types if dms_entries.exists() else {}

                                configurations = dms_entries.first().config_details_schema
                                print("configurations type", type(configurations))
                                configurations['drive_types'] = drive_types
                                # configurations['s3_bucket_metadata'] = drive_types
                                print("configurations", configurations)

                                metadata = {'form_id': form_id_ref, 'organization_id': organization_id}
                                configurations['metadata'] = json.dumps(metadata)
                                print("configurations", configurations)
                                files = {'files': (file.name, file.file, file.content_type)}
                                print("inside file")
                                external_api_url = 'http://192.168.0.106:8000/custom_components/FileUploadView/'
                                response = requests.post(external_api_url, data=configurations, files=files)

                                print("response", response)
                                if response.status_code == 200:
                                    # responses.append(response.json())  # Store the response
                                    response_json = response.json()
                                    print("response_json", response_json)
                                    file_name = response_json.get('file_name')
                                    file_id = response_json.get('file', {}).get('id')

                                    print("File Name:", file_name)
                                    print("File ID:", file_id)
                                    try:
                                        organization_instance = Organization.objects.get(id=organization_id)
                                    except Organization.DoesNotExist:
                                        # Handle the case where the organization does not exist
                                        organization_instance = None
                                    try:
                                        dms_instance = Dms.objects.get(id=organization_id)
                                    except Organization.DoesNotExist:
                                        # Handle the case where the organization does not exist
                                        organization_instance = None
                                    # Check if there are any Dms entries
                                    if dms_entries.exists():
                                        # Get the first Dms instance from the queryset
                                        dms_instance = dms_entries.first()
                                        dms_id = dms_instance.id  # Retrieve the Dms ID
                                    else:
                                        dms_instance = None
                                        print("No Dms entries found for the given organization_id.")
                                    try:
                                        dms_data, created = Dms_data.objects.get_or_create(
                                            folder_id=file_id,
                                            filename=file_name,
                                            case_id=case,
                                            flow_id=process_data,
                                            dms=dms_instance,

                                            organization=organization_instance,
                                            defaults={'meta_data': configurations['metadata']}
                                        )

                                    except Exception as e:
                                        print("Error during get_or_create:", e)

                                        # Print details of integration_data to see if it is None or has unexpected values
                                    if dms_data is None:
                                        print("dms_data is None")
                                    else:
                                        print(f"dms_data details: {dms_data.__dict__}")

                                        # If BotData was found, update the data_schema field
                                    if not created:
                                        try:
                                            dms_data.meta_data = dms_data
                                            dms_data.save()  # Ensure you call save on the correct object

                                        except Exception as e:
                                            print("Error during integration_data save:", e)

                                    responses.append(response_json)

                                else:
                                    print("Failed to execute API integration:", response.text)
                                    return response.append(
                                        {
                                            "error": f"Failed to execute {dms_data} integration. Response: {response.text}"},
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                            form_status = "In Progress"
                            caseId = case.id  # Assuming case.id is available

                            Filled_data_json = {
                                'formId': form_id_ref,
                                'processId': process_id,
                                'organization': organization_id_value,
                                'data_json': data_json_str,
                                'caseId': caseId,
                                'status': form_status
                            }
                            print("Filled_data_json", Filled_data_json)

                            # Serialize and save the filled form data
                            serializer = FilledDataInfoSerializer(data=Filled_data_json)

                            if serializer.is_valid():
                                instance = serializer.save()
                                print("Serializer data is valid:", serializer.validated_data)
                                # Prepare the response data with the filled form details
                                response_data.update({
                                    'filled_form_data': serializer.data
                                })
                                print("next_step_id", next_step_id)

                                # Update the case with the next step and save
                                case_data = Case.objects.select_for_update().get(pk=case.id)
                                case_data.data_json = json.dumps(
                                    json.loads(case_data.data_json) + [case_data.next_step])
                                case_data.status = "In Progress"
                                if not isinstance(case_data.path_json, list):
                                    case_data.path_json = []
                                # Append next_step to path_json
                                case_data.path_json.append(case_data.next_step)
                                case_data.save()

                                case_data.next_step = next_step_id  # Assuming next_step_id is determined elsewhere
                                case_data.save()
                                if next_step_id.lower() == "null" or cs_next_step == "null":
                                    case_data.status = "Completed"
                                    case_data.save()
                                    responses.append(case_data.status)

                                # responses.append(response_data)
                                print("Returning successful response")
                                return Response(response_data, status=status.HTTP_201_CREATED)  # Return the response
                            else:
                                # Return error response if serializer is not valid
                                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response(response_data, status=status.HTTP_200_OK)  # Make sure to return a response
                    else:
                        return Response({"error": "Form schema not found."},
                                        status=status.HTTP_404_NOT_FOUND)  # Handle case when form_json_schema is not found



                elif rule:

                    # Define a dictionary to map operator strings to functions
                    operator_map = {
                        '>': operator.gt,
                        '<': operator.lt,
                        '>=': operator.ge,
                        '<=': operator.le,
                        '==': operator.eq,
                        '!=': operator.ne
                    }

                    # Function to evaluate rules
                    def evaluate_rules(rules, extracted_data):
                        actions = []
                        print("extracted_data", extracted_data)

                        print("rules", rules)
                        for rule in rules:
                            source = rule['source']
                            field_id = rule['field_id']
                            op_str = rule['operator']
                            comparison_type = rule['comparison']['type']
                            comparison_value = rule['comparison']['value']
                            # value_source = rule['comparison']['value_source']
                            action = rule['comparison']['action']

                            print(f"Evaluating rule: {rule}")

                            field_value = None

                            try:
                                # Find field_value for field_id
                                for data_group in extracted_data:
                                    for field in data_group:
                                        if isinstance(field, dict) and 'field_id' in field and field[
                                            'field_id'] == field_id:
                                            field_value = field['value']
                                            break
                                        elif field_id in field:  # Handle cases where field_id is a key directly
                                            field_value = field[field_id]
                                            break

                                    if field_value is not None:
                                        break

                                if field_value is None:
                                    print(f"Field value is None for field_id: {field_id}. Skipping rule evaluation.")
                                    continue

                                print(f"Found field value: {field_value} for field_id: {field_id}")

                                # Handle comparison_value based on comparison_type
                                if comparison_type == 'field_id':
                                    comparison_field_id = comparison_value
                                    comparison_value = None

                                    for data_group in extracted_data:
                                        for field in data_group:
                                            if isinstance(field, dict) and 'field_id' in field and field[
                                                'field_id'] == comparison_field_id:
                                                comparison_value = field['value']
                                                break
                                            elif comparison_field_id in field:  # Handle cases where
                                                # comparison_field_id is a key directly
                                                comparison_value = field[comparison_field_id]
                                                break

                                        if comparison_value is not None:
                                            break

                                    if comparison_value is None:
                                        print(
                                            f"Comparison value is None for comparison_field_id: {comparison_field_id}. Skipping rule evaluation.")
                                        continue

                                    print(
                                        f"Found comparison value: {comparison_value} for comparison_field_id: {comparison_field_id}")

                                # Convert values to float for comparison
                                try:
                                    if op_str == '==' or op_str == '!=':
                                        field_value = field_value
                                        comparison_value = comparison_value
                                    else:
                                        field_value = float(field_value)
                                        comparison_value = float(comparison_value)
                                except ValueError as ve:
                                    print(f"Error converting values to float: {ve}")
                                    continue

                                print(
                                    f"Comparing field value: {field_value} with comparison value: {comparison_value} using operator: {op_str}")

                                # Evaluate the rule using the specified operator
                                try:
                                    if operator_map[op_str](field_value, comparison_value):
                                        actions.append(action)
                                except KeyError as ke:
                                    print(f"Unrecognized operator: {op_str}")

                            except Exception as e:
                                print(f"Error evaluating rule: {e}")
                                continue

                        return actions

                    print('--- Rule starts --- 1')
                    rule_id_ref = rule.id

                    rule_input_data = rule.rule_json_schema
                    print("rule_input_data", rule_input_data)
                    # Parse the JSON data
                    # data = json.loads(rule_input_data)
                    # print("dataaaaaaaaaaaaa",data)

                    # Extract sources and value_sources into sets
                    sources = set()

                    value_sources = set()

                    for item in rule_input_data:
                        sources.add(item['source'])
                        print("item", item)
                        # Check if 'comparison' exists and if 'value_source' exists within 'comparison'
                        if 'comparison' in item and 'value_source' in item['comparison']:
                            if item['comparison']['value_source']:
                                value_sources.add(item['comparison']['value_source'])
                        # print("########################")
                        # sources.add(item['source'])
                        # print("item",item)
                        # if item['comparison']['value_source']:
                        #     print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                        #     value_sources.add(item['comparison']['value_source'])
                    print("sources", sources)
                    print("value_sources", value_sources)
                    if value_sources:
                        all_ids = sources.union(value_sources)
                    else:
                        all_ids = sources

                    # all_ids = sources.union(value_sources)
                    print("all_ids", all_ids)

                    # Query all models with the single filter for all_ids and the additional case_id filter
                    try:
                        filtered_filled_form_table = FilledFormData.objects.filter(formId__in=all_ids, caseId=case_id)
                    except Exception as e:
                        print(f"Error filtering FilledFormData: {e}")
                        traceback.print_exc()

                    try:
                        filtered_integration_details = IntegrationDetails.objects.filter(
                            integration__Integration_uid__in=all_ids, case_id=case_id)
                    except Exception as e:
                        print(f"Error filtering IntegrationDetails: {e}")
                        traceback.print_exc()

                    try:
                        filtered_bot_table = BotData.objects.filter(bot__bot_uid__in=all_ids, case_id=case_id)
                    except Exception as e:
                        print(f"Error filtering BotData: {e}")
                        traceback.print_exc()

                    # try:
                    #     filtered_rule_table = Rule.objects.filter(ruleId__in=all_ids, case_id=case_id)
                    # except Exception as e:
                    #     print(f"Error filtering Rule: {e}")
                    #     traceback.print_exc()

                    # Print results
                    print("filtered_filled_form_table:", filtered_filled_form_table)
                    print("filtered_integration_details:", filtered_integration_details)
                    print("filtered_bot_table:", filtered_bot_table)
                    # print("filtered_rule_table:", filtered_rule_table)

                    # Extract data from all relevant tables
                    extracted_data = []

                    # Extract the data JSON from the filtered queryset
                    for form in filtered_filled_form_table:
                        try:
                            extracted_data.append(
                                json.loads(form.data_json) if isinstance(form.data_json, str) else form.data_json)
                        except Exception as e:
                            print(f"Error processing filled form data: {e}")
                            traceback.print_exc()
                    print("extracted_data", extracted_data)
                    for item in filtered_bot_table:
                        try:
                            extracted_data.append(
                                json.loads(item.data_schema) if isinstance(item.data_schema, str) else item.data_schema)
                        except Exception as e:
                            print(f"Error processing bot data: {e}")
                            traceback.print_exc()

                    for item in filtered_integration_details:
                        try:
                            extracted_data.append(
                                json.loads(item.data_schema) if isinstance(item.data_schema, str) else item.data_schema)
                        except Exception as e:
                            print(f"Error processing integration details: {e}")
                            traceback.print_exc()

                    # for item in filtered_rule_table: try: extracted_data.append(json.loads(item.rule_json_schema)
                    # if isinstance(item.rule_json_schema, str) else item.rule_json_schema) except Exception as e:
                    # print(f"Error processing rule table data: {e}") traceback.print_exc()

                    try:
                        actions = evaluate_rules(rule_input_data, extracted_data)
                        # Print the actions to be taken
                        print("Actions to be taken:", actions)
                        final_flow_key = []
                        final_flow_start = []
                        if actions:
                            next_step_id = actions[0]  # Assuming the first action is the next step

                            final_flow_start = []
                            final_flow_key = []

                            # Initialize variables for case update
                            case_next_step = None

                            # Check for next_step_id in participants_data["executionFlow"]
                            if next_step_id in participants_data["executionFlow"]:
                                flow = participants_data["executionFlow"][next_step_id]

                                # Iterate over the flows and find matches
                                for flow_item in flows:
                                    if flow_item['start'] == flow['currentStepId'] or flow_item['end'] == flow[
                                        'nextStepId']:
                                        print(f"Processing flow: {flow_item}")
                                        start = flow_item['start']

                                        end = flow_item['end']

                                        # Update the end key with the nextStepId
                                        flow_item['end'] = flow['nextStepId']

                                        # Set the case_next_step to the updated end value
                                        case_next_step = flow_item['end']

                                if case_next_step:
                                    # Update the case with the next step and save
                                    case_instance = Case.objects.select_for_update().get(pk=case.id)
                                    case_instance.nextstep = case_next_step  # Update with the new end value
                                    case_instance.save()
                                    # break
                                    # return Response( status=status.HTTP_201_CREATED)
                            else:
                                print(f"No matching flow found for next_step_id: {next_step_id}")

                        else:
                            return responses.append({"error": f"No actions found for rule {rule.ruleId}"},
                                                    status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        print("An error occurred:", e)

                # id the stepid is OCR
                elif ocr:
                    print('--- OCR starts --- 1')
                    ocr_id_ref = str(ocr.ocr_uid)
                    print("ocr_id_ref:", ocr_id_ref)
                    try:
                        ocr_details = Ocr.objects.get(ocr_uid=ocr_id_ref)
                        print("ocr_details:", ocr_details)
                    except Ocr.DoesNotExist:
                        ocr_details = None

                    if ocr_details:
                        ocr_data = Ocr.objects.filter(organization=organization_id, flow_id=process_id)
                        serializer = OcrSerializer(ocr_data, many=True)
                        [ocr_serialized_data] = serializer.data

                        # response_data = {
                        #     'caseid': case.id,
                        #     'createdby': case.created_by,
                        #     'createdon': case.created_on,
                        #     'updatedon': case.updated_on,
                        #     'updatedby': case.updated_by,
                        #     'ocr_schema': ocr_serialized_data,
                        #     'status': case.status
                        # }
                        # Return response data immediately
                        # return Response(response_data)

                        if 'data_json' in request.data and request.data['data_json']:
                            data_json_str = request.data['data_json']
                            print("data_json_str", type(data_json_str))

                            data_json = data_json_str
                            caseId = case.id  # Assuming case.id is available
                            print("caseId", caseId)
                            process_id = process_data.id  # Assuming process_data.id is available
                            print("process_id", process_id)
                            organization_id = organization_id
                            print("organization_id", organization_id)
                            filled_ocr_data = {
                                'ocr_uid': ocr_id_ref,
                                'flow_id': process_id,
                                'organization': organization_id,
                                'data_schema': data_json,  # JSON list (need to change)
                                'case_id': caseId,
                            }
                            print("filled_ocr_data", filled_ocr_data)
                            # Serialize and save the filled form data
                            serializer = Ocr_DetailsSerializer(data=filled_ocr_data)
                            if serializer.is_valid():
                                print("filled_ocr_data is valid")
                                instance = serializer.save()
                                print("Serializer data is valid:", serializer.validated_data)
                                response_data.update({
                                    'filled_ocr_data': serializer.data
                                })
                                case_instance = Case.objects.select_for_update().get(pk=case.id)
                                case_instance.next_step = next_step_id  # Assuming next_step_id is determined elsewhere
                                case_instance.save()
                                print("next_step_id ", next_step_id)
                                # responses.append(response_data)
                                print("Returning successful response")
                                return Response(response_data, status=status.HTTP_201_CREATED)  # Return

                            else:
                                # Return error response if serializer is not valid
                                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response({"error": "Form schema not found and no data to fill."},
                                            status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({"error": "Ocr Details not found."},
                                        status=status.HTTP_404_NOT_FOUND)  # Handle case when form_json_schema is not found

                current_step_id = steps[current_step_id]['nextStepId']
                print("current_step_id", current_step_id)

                # Update the case data
                case_data = Case.objects.get(pk=pk)
                case_data.data_json = json.dumps(json.loads(case_data.data_json) + [case_data.next_step])
                case_data.status = "In Progress"
                if not isinstance(case_data.path_json, list):
                    case_data.path_json = []
                # Append next_step to path_json
                case_data.path_json.append(case_data.next_step)
                case_data.save()

                # Check the end form id
                print("next_step_id++++++++++++++++++++++++++++++", next_step_id)
                if next_step_id.lower() == "null" or cs_next_step == "null":
                    case_data.status = "Completed"
                    case_data.save()
                    responses.append(case_data.status)

                    # break
                else:
                    # Find the next flow starting from the end of the current flow
                    final_flow_start = []
                    final_flow_key = []
                    for flow in flows:
                        for flow_key, flow_value in participants_data["executionFlow"].items():
                            print(f"Processing flow: {flow_key}:{flow_value}")
                            # for flow_key, flow_value in process_flow.items():
                            start = flow['start']
                            end = flow['end']
                            if flow_value.get('currentStepId') == flow['end']:
                                start_form_id = flow_value.get('currentStepId')
                                if start_form_id:
                                    final_flow_start.append(start_form_id)
                                    final_flow_key.append(flow_key)
                    if final_flow_start:
                        case_data.next_step = final_flow_start[0]
                    else:
                        return Response({"message": "No next flow found for the end flow"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    case_data.save()
                    if next_step_id:
                        return self.handle_case_step(request, case_id)
                    else:
                        return Response(responses, status=status.HTTP_200_OK)
                    # break
                # return Response({"message": "Form schema saved successfully"}, status=status.HTTP_201_CREATED)

                return Response({"message": "Process executed successfully", "responses": responses},
                                status=status.HTTP_200_OK)
        except Exception as e:
            responses.append({"error": f"Exception occurred while executing step {current_step_id}: {str(e)}"})
            return Response(responses, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # return Response(responses, status=status.HTTP_200_OK)
        # except Case.DoesNotExist:
        #     return Response({"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
        # except FormDataInfo.DoesNotExist:
        #     return Response({"error": "Form schema not found"}, status=status.HTTP_404_NOT_FOUND)
        # except Exception as e:
        #     return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


############ execution flow modified according to case[ends] by Praba
# added by laxmi mam
class CoreData(APIView):
    def get(self, request):

        form_data = CreateProcess.objects.all().values('id', 'process_name')
        if form_data:
            first_id = form_data[0]['id']
        else:
            print("No records in the queryset")
        for item in form_data:
            id_value = item['id']
            print(id_value)

        # Retrieve the 'participants' field for all records
        participants_list = CreateProcess.objects.values('participants')

        formids = set()  # Use a set to ensure unique formids
        for entry in participants_list:
            for participant in entry['participants']:
                if 'formid' in participant:
                    formids.add(participant['formid'])

        # Retrieve all 'id' values from 'SaveFormData'
        save_form_data_ids = FormDataInfo.objects.values_list('id', flat=True)

        # Filter 'id' values from 'save_form_data_ids' that are not in 'formids'
        unique_ids = [id for id in save_form_data_ids if str(id) not in formids]

        # Convert the result to a list if needed
        id_list = list(unique_ids)
        print(id_list)

        # Fetch the associated FormJsonSchema objects using the 'id' values
        form_json_schemas = FormDataInfo.objects.filter(id__in=id_list)

        # Serialize the FormJsonSchema objects into a response format, assuming you have a serializer
        serializer = FormDataInfoSerializer(form_json_schemas, many=True)

        # Return the serialized data in the response
        return Response(serializer.data)


# added by laxmi mam
class CoreDataFilledForm(APIView):
    def get(self, request, pk=None):
        form_json_schema = FormDataInfo.objects.get(id=pk)
        serializer = FormDataInfoSerializer(form_json_schema)
        return Response(serializer.data)

    def post(self, request, pk):
        try:

            try:
                form_data = FormDataInfo.objects.get(id=pk)
                data_json = request.data.get('data_json')

                Filled_data_json = {
                    'formId': pk,
                    'data_json': data_json,  # json list (need to change)

                }
                serializer = FilledDataInfoSerializer(data=Filled_data_json)
                if serializer.is_valid():
                    instance = serializer.save()

                return Response(serializer.data, status=status.HTTP_200_OK)
            except FormDataInfo.DoesNotExist:
                return Response({"error": "The provided form_id does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An error occurred while updating the data."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            filled_data = FormDataInfo.objects.get(id=pk)
            data_json = request.data.get('data_json')

            Filled_data_json = {
                'formId': pk,
                'data_json': data_json,  # json list (need to change)

            }
            serializer = FilledDataInfoSerializer(data=Filled_data_json)
            if serializer.is_valid():
                instance = serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        except FilledFormData.DoesNotExist:
            return Response({"error": "The provided formId does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An error occurred while updating the data."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


################################################# Create User Starts ##################################################

# class CreateUserView(APIView):
#     def post(self, request):
#         serializer = UserinfoSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#
#             # Generate a password reset token and link
#             reset_token = get_random_string(32)
#             reset_link = reverse('password-reset', kwargs={'token': reset_token})
#             full_link = f"{request.scheme}://{request.get_host()}{reset_link}"
#
#             # Optionally, store the reset token in a user profile or separate model
#             # Assuming you have a profile model with a reset_token field
#             user.profile.reset_token = reset_token
#             user.profile.save()
#
#             # Send the reset email
#             send_mail(
#                 'Password Reset Link',
#                 f'Please click the link below to set your password:\n\n{full_link}',
#                 'from@example.com',  # Change to your email
#                 [user.email],
#                 fail_silently=False,
#             )
#
#             return Response({'message': 'User created successfully. Password reset link has been sent.'}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes


@authentication_classes([TokenAuthentication])
class UserCreateView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only admin users can access this view

    def get(self, request, user_id=None):
        if user_id:
            user_data = get_object_or_404(UserData, id=user_id)
            serializer = UserDataSerializer(user_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            user_data = UserData.objects.all()
            serializer = UserDataSerializer(user_data, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        # Check if the request user is a superadmin
        user = request.user
        print("user", user)
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to perform this action."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = UserDataSerializer(data=request.data)
        if serializer.is_valid():
            # Check if email already exists
            mail_id = serializer.validated_data.get('mail_id')
            print("mail_id", mail_id)
            if UserData.objects.filter(mail_id=mail_id).exists():
                return Response({"error": "Email address already in use."}, status=status.HTTP_400_BAD_REQUEST)

            user_data = serializer.save()

            try:
                # Ensure a corresponding User is created
                user = User.objects.create_user(
                    username=user_data.user_name,
                    email=user_data.mail_id,
                    password='temporary_password'  # Set a temporary password or handle as needed
                )
            except IntegrityError as e:
                logger.error(f"User creation failed due to unique constraint: {str(e)}")
                return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)

            # Link the UserData with the created User
            user_data.user_id = user.id
            user_data.save()

            self.send_password_reset_email(user, request)
            return Response({'status': 'User created and reset email sent'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, user_id):
        user_data = get_object_or_404(UserData, id=user_id)
        serializer = UserDataSerializer(user_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user_data = get_object_or_404(UserData, id=user_id)
        user.delete()
        user_data.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def send_password_reset_email(self, user, request):
        try:
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            print("token", token)
            reset_url = reverse('password_reset_confirm', kwargs={'user_id': user.id, 'token': token})
            reset_link = request.build_absolute_uri(reset_url)
            subject = 'Password Reset'
            body = f'Here is your password reset link: {reset_link}'

            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])

            logger.info(f"Password reset email sent to {user.email}")
            return Response({"message": "Password reset email sent successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return Response({"error": "An error occurred while sending the email."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


################################################# Create User Ends ##################################################
# class LoginView(APIView):
#     def post(self, request, format=None):
#         username = request.data.get('username')
#         password = request.data.get('password')
#
#         # Authenticate the user
#         user = authenticate(username=username, password=password)
#
#         if user is not None:
#             # Check if a token already exists
#             token, created = Token.objects.get_or_create(user=user)
#             return Response({"token": token.key}, status=status.HTTP_200_OK)
#         else:
#             return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LoginView(APIView):
    def post(self, request, format=None):
        mail_id = request.data.get('mail_id')
        password = request.data.get('password')

        user = authenticate(request, mail_id=mail_id, password=password)

        if user is not None:
            # Check if a token already exists
            token, created = Token.objects.get_or_create(user=user)

            user_data = UserData.objects.get(mail_id=mail_id)
            # Extracting usergroup data assuming it's a ForeignKey
            usergroup = user_data.usergroup
            usergroup_name = usergroup.group_name if usergroup else "is_super_user"  # Replace 'name' with the correct field

            response_data = {
                "user_id": user.id,
                "usergroup": usergroup_name,
                "token": token.key,
                "mail_id": user_data.mail_id,
            }

            logger.info(f"User {user.id} authenticated successfully.")
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Authentication failed for mail_id: {mail_id}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    # def post(self, request, format=None):
    #     mail_id = request.data.get('mail_id')
    #     password = request.data.get('password')
    #
    #     # Authenticate the user using the custom backend
    #     user = authenticate(mail_id=mail_id, password=password)
    #     print("user",user)
    #     if user is not None:
    #         # Check if a token already exists
    #         token, created = Token.objects.get_or_create(user=user)
    #
    #         # Prepare the response data
    #         user_data = UserData.objects.get(user=user)
    #         response_data = {
    #             "user_id": user.id,
    #             "usergroup": user_data.usergroup,  # Adjust as needed
    #             "token": token.key,
    #             "mail_id": user_data.mail_id,
    #         }
    #
    #         logger.info(f"User {user.id} authenticated successfully.")
    #         return Response(response_data, status=status.HTTP_200_OK)
    #     else:
    #         logger.warning(f"Authentication failed for mail_id: {mail_id}")
    #         return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# class MailIDBackend(ModelBackend):
#     def authenticate(self, request, mail_id=None, password=None, **kwargs):
#         logger.debug(f"Attempting to authenticate user with mail_id: {mail_id}")
#         try:
#             user_data = UserData.objects.get(mail_id=mail_id)
#             user = user_data.user
#             if user.check_password(password):
#                 logger.info(f"Authentication successful for mail_id: {mail_id}")
#                 return user
#             else:
#                 logger.warning(f"Password mismatch for mail_id: {mail_id}")
#                 return None
#         except UserData.DoesNotExist:
#             logger.error(f"UserData with mail_id {mail_id} does not exist")
#             return None
#         except Exception as e:
#             logger.error(f"An unexpected error occurred: {e}")
#             return None


# ............... SLA with Cron bgn .............
# mohan
def sla_email():
    """
    Notify users
    """
    print("SLA Email +++++++++++++++")
    try:
        # get_case = Case.objects.get(pk=233)
        get_case = Case.objects.all()
        for case in get_case:
            next_step = case.next_step
            process_id = case.processId

            # Retrieve the corresponding CreateProcess object
            process_data = CreateProcess.objects.get(pk=process_id.pk)
            # print("Process Data:", process_data)
            participants_data = process_data.participants

            j_data = json.dumps(participants_data)
            data_list = json.loads(j_data)

            # get sla bgn --
            get_sla = Sla.objects.get(processId=process_id)
            sla_jsn = get_sla.sla_json_schema

            if isinstance(sla_jsn, str):
                sla_jsn = json.loads(sla_jsn)

            condition = sla_jsn.get('Condition', {})
            condition_form_id = condition.get('FormId', '')
            check_condition = condition.get('Check', '')
            # get sla end --

            flow_start = []
            for flow in data_list:  # find next start
                if "processFlow" in flow:
                    process_flow = flow["processFlow"]
                    for flow_key, flow_value in process_flow.items():

                        if flow_key == next_step:
                            # print('flow_key---', flow_key)
                            # print('next_step---', next_step)
                            current_flow_key = flow_key
                            current_flow_values = flow_value['Start']
                            flow_start.append(current_flow_values)

            if condition_form_id in flow_start:
                # find eta date bgn --
                current_flow_value = flow_start[0]
                find_eta_form = FilledFormData.objects.get(formId=current_flow_value)
                find_eta_json = find_eta_form.data_json
                data_dict = json.loads(find_eta_json)
                # ETA date
                eta_date_str = data_dict.get("ETA")
                eta_date = datetime.strptime(eta_date_str, "%Y-%m-%d").date()

                current_date = datetime.now().date()
                eta_minus_4 = eta_date - timedelta(days=4)
                # find eta date end --

                if current_date >= eta_minus_4:
                    subject = 'Form Completion Reminder'
                    message = 'You have an assigned form that needs to be completed' \
                              ' within four days. Please complete it as soon as possible.'
                    from_email = settings.EMAIL_HOST_USER
                    recipient_list = ['mohansaravanan111@gmail.com']
                    send_mail(subject, message, from_email, recipient_list)
                else:
                    print("Current date is not greater than ETA date - 4.")
            else:
                print("Condition form ID not found in flow start.")

        return HttpResponse('Email sent successfully.')  # response to indicate success
    except Case.DoesNotExist:
        return HttpResponse('Case with ID 1 does not exist.')  # response to indicate failure


######################################## User Create function starts ###################################


# -- Cron Bgn --
run_time = time(1, 0, 0)


def schedule_job():
    schedule.every().day.at(run_time.strftime('%H:%M')).do(sla_email)


schedule_job()
# while True:
#     import time
#     schedule.run_pending()
#     time.sleep(1)
# -- Cron End --
# ............... SLA with Cron end .............
