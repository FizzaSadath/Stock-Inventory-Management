from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-item/', views.add_item, name='add_item'),
    path('add_item_post/', views.add_item_post, name='add_item_post'),
    path('delete-item/', views.delete_item, name='delete_item'),
    path('delete-item-post/', views.delete_item_post, name='delete_item_post'),
    path('add_stock/', views.add_stock, name='add_stock'),  # for GET (show form)
    path('add_stock_post/', views.add_stock_post, name='add_stock_post'),  # for POST (process form)
    path('remove_stock/', views.remove_stock, name='remove_stock'),
    path('remove_stock_post/', views.remove_stock_post, name='remove_stock_post'),
    path('view_stock/', views.view_stock, name='view_stock'),

]
