"""
author : mohan
app_name : form_generator
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import *
from .views import CustomPasswordResetView
urlpatterns = [

    # mohan_dev class based
    path('create_form/', FormGeneratorAPIView.as_view(), name='form_generator_create'),
    # create forms and get all records
    path('create_form/organization/<int:organization_id>/<int:form_id>/', FormGeneratorAPIView.as_view(),
         name='form_data_edit'),  # to edit,delete and list the form
    path('create_form/organization/<int:organization_id>/', FormGeneratorAPIView.as_view(),
         name='forms_by_organization'),  # to list the form based on organization
    # path('get/<int:pk>/', FormGeneratorAPIView.as_view(), name='form_generator_get'),  # get ID based form records
    # path('edit/<int:pk>/', FormGeneratorAPIView.as_view(), name='form_generator_edit'),  # edit ID based form records
    path('form_data_count/', get_form_data_count, name='form_data_count'),  # get form data count
    path('send_mail/<int:pk>/', FormGeneratorAPIView.as_view(), name='form_generator_send_mail'),
    # edit ID based form records

    # User created by Admin based on organization and usergroup starts
    path('create-user/', UserCreateView.as_view(), name='create-user'), # to create a user by Admin
    path('users_list/<int:organization_id>/', UserCreateView.as_view(), name='user-list-by-organization'),
    path('user_list/<int:organization_id>/<int:user_id>/', UserCreateView.as_view()),  # For retrieve, update, delete
    # User created by Admin based on organization and usergroup ends

    # # List and create users for a specific organization
    # path('organization/<int:organization_id>/users/', UserDataListCreateView.as_view(), name='user-data-list-create'),
    #
    # # Retrieve and update a specific user for a given organization
    # path('organization/<int:organization_id>/users/<int:pk>/', UserDataUpdateView.as_view(), name='user-data-update'),

    # tws bgn
    # mohan_dev
    path('start_process/', CreateProcessView.as_view(), name='create_process'),
    path('start_process/<int:pk>/', CreateProcessView.as_view(), name='get_process'),  # to initiate the process

    path('api/login/', LoginView.as_view(), name='login'),
    path('api/login/<organization_id>/', LoginView.as_view(), name='login'),

    path('password-reset/<int:user_id>/<str:token>/', CustomPasswordResetView.as_view(), name='password_reset'),
    # praba_dev
    path('organizations/<int:organization_id>/cases/', OrganizationCasesView.as_view(), name='organization_cases'),
    path('case_details/<int:organization_id>/<int:process_id>/<int:case_id>/', CaseDetailView.as_view(),
         name='case-detail'),
    path('process_related_cases/', CaseRelatedFormView.as_view(), name='case_related_forms'),
    # path('get_case_related_forms/<int:pk>/<str:token>/', CaseRelatedFormView.as_view(), name='case_related_forms'),  # token
    path('cases/<int:organization_id>/<int:process_id>/', CaseRelatedFormView.as_view(), name='case-list'),  # get
    # cases related to process
    path('cases_related_form/<int:organization_id>/<int:process_id>/<int:pk>/', CaseRelatedFormView.as_view(),
         name='case-detail'),  # get particular cases related to process
    path('process_related_cases/<int:pk>/', CaseRelatedFormView.as_view(), name='case_related_forms'),
    path('send_sla_email/', sla_email, name='sla_email'),
    # tws end

    # praba_dev
    path('filled_data/', UserFilledDataView.as_view(), name='filled_form_list'),  # List all filled data
    path('filled_data/<int:organization_id>/', UserFilledDataView.as_view(), name='filled_form_by_org'),
    # Filter by organization
    path('filled_data/<int:organization_id>/<int:pk>/', UserFilledDataView.as_view(), name='filled_form_detail'),
    # Filter by organization and pk


    path('filled_data/', UserFilledDataView.as_view(), name='filled_form'),  # to get and post user filled form data
    path('filled_data/<int:pk>/', UserFilledDataView.as_view(), name='filled_data-save'),  # to edit,update and delete



    path('coredata/', CoreData.as_view(), name='core_data'),
    path('coredata/<int:pk>/', CoreDataFilledForm.as_view(), name='core_data_save'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
