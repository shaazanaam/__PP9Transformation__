from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_processor_home, name='data_processor_home'),
    path('upload/', views.upload_file, name='upload'),
    path('success/', views.transformation_success, name='transformation_success'),
    path('download/', views.download_excel, name='download_excel'),
    path('download_csv/', views.download_csv, name='download_csv'),
    path('statewide/', views.statewide_view, name='statewide_view'),
    path('tricounty/', views.tri_county_view, name='tri_county_view'),
    path('county_layer/', views.county_layer_view, name='county_layer_view'),
    path('metopio_statewide/', views.metopio_statewide_view, name='metopio_statewide_layer_view'),
    path('metopio_zipcode/', views.metopio_zipcode_view, name='metopio_zipcode_layer_view'),
    path('city_town/', views.city_town_view, name='metopio_city_town_view'),
    path('statewide_removal/', views.statewide_removal, name='statewide_removal'),
    path('tricounty_removal/', views.tri_county_removal_view, name='tri_county_removal_view'),
    path('county_layer_removal/', views.county_layer_removal_view, name='county_layer_removal_view'),
    path('zipcode_layer_removal/', views.zipcode_layer_removal_view, name='zipcode_layer_removal_view'),
    path('city_layer_removal/', views.city_layer_removal_view, name='city_layer_removal_view'),
    path('combined_removal/', views.combined_removal_view, name='combined_removal_view'),
    path('forward_exam/', views.forward_exam_view, name='forward_exam_view'),
    path('forward_exam_statewide_transformation/', views.forward_exam_statewide_transformation_view, name='forward_exam_statewide_transformation_view'),
]
