from django.conf.urls.static import static
from django.urls import path
from django.conf import settings
from .views import *  # class based
from . import views  # function based
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # added by Mohan BGN
    path('processes/', ProcessBuilder.as_view(), name='process_builder'),

    # path('processes/', ListProcesses.as_view(), name='list_processes'),
    path('processes/organization/<int:organization_id>/<int:process_id>/', ListProcessesByOrganization.as_view(),
         name='list-processes'
              '-by-organization'),
    path('processes/organization/<int:organization_id>/', ListProcessesByOrganization.as_view(),
         name='list-processes'
              '-by-organization'),
    path('create_process/<int:process_id>/', CreateProcessView.as_view(), name='create_process'),
    # to list the process based elements
    path('processes/create/', CreateProcessView.as_view(), name='create-process'),  # process create
    path('processes/<int:pk>/', ProcessDetailView.as_view(), name='process-detail'),  # process update
    # path('processes/<int:process_id>/execute/', ExecuteProcess.as_view(), name='execute_process'),
    # path('processes/<int:process_id>/', ExecuteProcess.as_view(), name='get_process'),

    # added by Mohan END

    # bot component URL starts

    path('bots/', BotListCreateView.as_view(), name='bot-list-create'),  # to list and create  the bots
    path('bots/<int:organization_id>/', BotListCreateView.as_view(), name='bot-list-create'),
    # path('bots/<int:id>/', BotDetailView.as_view(), name='bot-detail'), # to update the bot
    # path('bots/<int:organization_id>/', BotDetailView.as_view(), name='bot-detail'),

    path('bots/<int:organization_id>/<int:id>/', BotDetailView.as_view(), name='bot-detail'),  # update and list the bot

    # bot component URL ends

    # integration URL starts
    path('integrations/<int:organization_id>/', views.IntegrationListCreateAPIView.as_view(), name='integration-list-create'),
    path('integrations/<int:organization_id>/<int:pk>/', views.IntegrationDetailAPIView.as_view(), name='integration-detail'),

    # integration URL ends

    # OCR Component URL starts
    path('ocrs/<int:organization_id>/', OcrListCreateView.as_view(), name='ocr-list-create'),  # OCR components
    # create and list
    path('ocrs/<int:organization_id>/<int:pk>/', OcrDetailView.as_view(), name='ocr-detail'),  # OCR components
    # create and list
    # OCR Component URL ends




    # Dashboard URL starts
    path('organizations/<int:organization_id>/process_details/', OrganizationBasedProcess.as_view(), name='organization-details'),
    path('organizations/<int:organization_id>/details/', OrganizationDetailsAPIView.as_view(), name='organization-details'),# organization based details
    path('dashboards/<int:organization_id>/', DashboardListCreateView.as_view(),
         name='dashboard-list-create'),
    path('dashboards/<int:organization_id>/<int:pk>/', DashboardRetrieveUpdateDestroyView.as_view(),
         name='dashboard-detail'),
    # Dashboard URL ends
    # DMS URL starts
    path('dms/<int:organization_id>/', DmsListCreateView.as_view(), name='dms-list-create'),
    path('dms/<int:organization_id>/<int:id>/', DmsRetrieveUpdateView.as_view(),
         name='dms-retrieve-update'),
    # DMS URL ends

    # added by laxmi praba BGN
    path('drive-files/', views.list_drive_files, name='drive_files_api'),
    path('convert/', views.convert_excel_to_json, name='convert_excel_to_json'),
    # added by laxmi praba END

    # added by Raji BGN
    path('screen_scraping/', AutomationView.as_view(), name='screen_scraping'),
    path('api_integration/', APIIntegrationView.as_view(), name='api_integration'),
    # added by Raji END

    # added by Raji BGN for OCR Components
    path('AadharcardExtractionView/', AadharcardExtractionView.as_view(), name='AadharcardExtractionView'),
    path('PancardExtractionView/', PancardExtractionView.as_view(), name='PancardExtractionView'),
    path('OCRExtractionView/', OCRExtractionView.as_view(), name='OCRExtractionView'),
    # added by Raji END for OCR Components
    # added by Raji BGN for DMS components
    path('FileUploadView/',FileUploadView.as_view(),name='FileUploadView'),
    path('FileDownloadView/',FileDownloadView.as_view(),name='FileDownloadView'),
    # added by Raji ENDS for DMS components

    # added by Praba BGN - For Organization
    path('organizations/', views.OrganizationListCreateAPIView.as_view(), name='organization-list-create'),
    path('organizations/<int:pk>/', views.OrganizationRetrieveUpdateAPIView.as_view(),
         name='organization-retrieve-update'),
    path('organization/code/<str:org_code>/', OrganizationRetrieveUpdateAPIView.as_view(), name='organization-detail-by'
                                                                                                '-code'),  # api to get
    # organization using org_code
    # added by Praba END

    # added by Praba BGN - For UserGroups
    path('organizations/<int:org_id>/usergroups/', views.UserGroupListCreateAPIView.as_view(), name='usergroup-list'
                                                                                                    '-create'),  #
    # list the user based on organization

    path('organizations/<int:org_id>/usergroups/<int:pk>/', views.UserGroupRetrieveUpdateDestroyAPIView.as_view(),
         name='usergroup-detail'),  # edit the user based on organization
    path('user-groups/', UserGroupListCreateAPIView.as_view(), name='user-group-list-create'),
    path('user-groups/<int:pk>/', UserGroupRetrieveUpdateDestroyAPIView.as_view(),
         name='user-group-retrieve-update-destroy'),
    # added by Praba END

    # path('create-permissions/', CreatePermissionsView.as_view(), name='create-permissions'),

    path('password-reset/<int:user_id>/<str:token>/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<str:user_id>/<str:token>/', auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    # path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    # other URLs in your application

    path('login/', UserLoginView.as_view(), name='user_login'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
