from django.shortcuts import render
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Department, Location, Equipment, Component, Accessory, UserDepartment
from .serializers import UserSerializer, DepartmentSerializer, LocationSerializer,EquipmentSerializer, ComponentSerializer, AccessorySerializer,UserDepartmentSerializer
from .permissions import IsCreateRole, IsUpdateDeleteRole


