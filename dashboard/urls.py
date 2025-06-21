from django.urls import path
from . import views
from .views import  add_category, ProductListView, add_product, categories, dashboard_reviews
urlpatterns = [
    path('', views.dashboard_home, name='dashboard'),
    
    # Category routes
    path('dashboard/categories/', categories, name='categories'),
    path('dashboard/categories/edit/<uuid:pk>/', views.edit_category, name='dashboard_edit_category'),
    path('dashboard/categories/delete/<uuid:pk>/', views.delete_category, name='dashboard_delete_category'),



    path('dashboard/categories/add/', add_category, name='add_category'),  # FIXED: uses working view

    

    # Product routes
    path('products/', ProductListView.as_view(), name='product_list'),  # KEEP ONLY ONE
    path('dashboard/products/edit/<uuid:pk>/', views.edit_product, name='dashboard_edit_product'),
    path('dashboard/products/delete/<uuid:pk>/', views.delete_product, name='dashboard_delete_product'),

    path('add-product/', add_product, name='add_product'),
# Review route
    path('reviews/', dashboard_reviews, name='dashboard_reviews'),
]