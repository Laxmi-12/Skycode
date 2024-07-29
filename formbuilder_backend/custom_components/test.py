import unittest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory, TestCase
from django.conf import settings
from django.core.wsgi import get_wsgi_application
import json
import os
from django.test import TestCase, Client
from django.urls import reverse
import pandas as pd

# from .serializers import FilledDataInfoSerializer, CaseSerializer

# Import the functions to be tested from views.py
from custom_components.views import (
    get_google_drive_service, download_file, move_file, get_mime_type, list_drive_files
)

# Ensure the settings module is set
os.environ['DJANGO_SETTINGS_MODULE'] = 'formbuilder_backend.settings'
application = get_wsgi_application()

class TestGoogleDriveFunctions(TestCase):
    @patch('custom_components.views.build')
    @patch('custom_components.views.service_account.Credentials.from_service_account_file')
    def test_get_google_drive_service(self, mock_from_service_account_file, mock_build):
        mock_credentials = MagicMock()
        mock_from_service_account_file.return_value = mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        service = get_google_drive_service()

        mock_from_service_account_file.assert_called_once_with(
            settings.SERVICE_ACCOUNT_KEY_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_credentials)
        self.assertEqual(service, mock_service)

    @patch('custom_components.views.build')
    @patch('custom_components.views.service_account')
    @patch('custom_components.views.settings', spec=True)
    def test_download_file(self, mock_settings, mock_service_account, mock_build):
        # Mock settings
        mock_settings.MEDIA_ROOT = 'D:\\SKYCODE_FORM_BUILDER\\skycode_main\\skycode\\skycode\\formbuilder_backend\\media'

        # Mock Google Drive service and file data
        drive_service = MagicMock()
        mock_build.return_value = drive_service
        file_id = 'test_file_id'
        file_name = 'test_file_name.docx'

        # Mock the get().execute() call
        mock_get = drive_service.files().get.return_value
        mock_get.execute.return_value = {'mimeType': 'application/vnd.google-apps.docx'}

        # Mock the export_media call
        mock_export = drive_service.files().export_media.return_value

        # Mock the MediaIoBaseDownload
        with patch('custom_components.views.MediaIoBaseDownload') as mock_media_download:
            mock_downloader = mock_media_download.return_value
            mock_downloader.next_chunk.return_value = (None, True)

            # Call the function under test
            temp_file_path = download_file(drive_service, file_id, file_name)

            # Assert the expected temp file path
            expected_temp_file_path = os.path.join(mock_settings.MEDIA_ROOT, 'tmp', 'test_file_name.docx')
            self.assertEqual(temp_file_path, expected_temp_file_path)

    def test_get_mime_type(self):
        self.assertEqual(get_mime_type('xlsx'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertEqual(get_mime_type('csv'), 'text/csv')
        self.assertEqual(get_mime_type('txt'), 'text/plain')
        self.assertEqual(get_mime_type('pdf'), 'application/pdf')
        self.assertEqual(get_mime_type('jpg'), 'image/jpeg')
        self.assertEqual(get_mime_type('png'), 'image/png')
        self.assertEqual(get_mime_type('unknown'), 'application/octet-stream')

    @patch('custom_components.views.download_file')
    # @patch('custom_components.views.move_file')
    @patch('custom_components.views.get_google_drive_service')
    @patch('custom_components.views.get_mime_type')
    def test_list_drive_files(self, mock_get_mime_type, mock_get_google_drive_service, mock_download_file):
        # Mock the Google Drive service and dependencies
        mock_drive_service = MagicMock()
        mock_get_google_drive_service.return_value = mock_drive_service

        # Mock request data
        request_data = {
            'folder_id': 'test_folder_id',
            'file_type': 'xlsx',
            'completed_folder_id': 'completed_folder_id'
        }

        # Mock the response of list_drive_files
        mock_drive_service.files().list().execute.return_value = {
            'files': [{'id': 'test_file_id', 'name': 'test_file_name'}]
        }

        # Mock the return values of dependencies
        mock_download_file.return_value = '/path/to/temp_file'
        # mock_move_file.return_value = {'id': 'moved_file_id'}
        mock_get_mime_type.return_value = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # Create a mock request
        request = RequestFactory().post('/api/list_drive_files', data=json.dumps(request_data), content_type='application/json')

        # Call the function under test
        response = list_drive_files(request)

        # Assert the response status code
        self.assertEqual(response.status_code, 200)

        # Mock the expected file_schema response
        expected_file_schema = {
            'file_id': 'test_file_id',
            'file_name': 'test_file_name',
            'temp_data': '/path/to/temp_file'
        }

        # Assert the response content matches the expected file schema
        self.assertEqual(json.loads(response.content), expected_file_schema)

    # @patch('custom_components.views.HttpError')
    # def test_move_file(self, mock_http_error):
    #     # Mock Google Drive service and data
    #     drive_service = MagicMock()
    #     file_id = 'test_file_id'
    #     new_parent_id = 'new_parent_id'
    #     drive_service.files().get.return_value.execute.return_value = {'parents': ['old_parent_id']}
    #     drive_service.files().update.return_value.execute.return_value = {'id': file_id, 'parents': [new_parent_id]}
    #
    #     # Call the function under test
    #     updated_file = move_file(drive_service, file_id, new_parent_id)
    #
    #     # Assert the expected method calls
    #     drive_service.files().get.assert_called_once_with(fileId=file_id, fields='parents')
    #     drive_service.files().update.assert_called_once_with(
    #         fileId=file_id,
    #         addParents=new_parent_id,
    #         removeParents='old_parent_id',
    #         fields='id, parents'
    #     )
    #
    #     # Assert the returned file matches the expected structure
    #     self.assertEqual(updated_file, {'id': file_id, 'parents': [new_parent_id]})







if __name__ == '__main__':
    unittest.main()
