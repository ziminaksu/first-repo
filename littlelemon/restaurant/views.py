from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse
from .forms import BookingForm
from .models import Menu,Booking, Rating,MenuItem, Order,Cart,CartItem
from django.core import serializers
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt, api_view, permission_classes
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated,IsAdminUser, AllowAny
from .serializers import RatingSerializer, MenuItemSerializer, OrderSerializer,CartItemSerializer
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login

# Create your views here.
def home(request):
    return render(request, 'index.html')
    
def index(request):
    return render(request, 'index.html', {})
    
def about(request):
    return render(request, 'about.html')

def reservations(request):
    date = request.GET.get('date',datetime.today().date())
    bookings = Booking.objects.all()
    booking_json = serializers.serialize('json', bookings)
    return render(request, 'bookings.html',{"bookings":booking_json})

def book(request):
    form = BookingForm()
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
    context = {'form':form}
    return render(request, 'book.html', context)

# Add your code here to create new views
def menu(request):
    menu_data = Menu.objects.all()
    main_data = {"menu": menu_data}
    return render(request, 'menu.html', {"menu": main_data})

def display_menu_item(request, pk=None): 
    if pk: 
        menu_item = Menu.objects.get(pk=pk) 
    else: 
        menu_item = "" 
    return render(request, 'menu_item.html', {"menu_item": menu_item}) 

@csrf_exempt
def bookings(request):
    if request.method == 'POST':
        data = json.load(request)
        exist = Booking.objects.filter(reservation_date=data['reservation_date']).filter(
            reservation_slot=data['reservation_slot']).exists()
        if exist==False:
            booking = Booking(first_name=data['first_name'],
                reservation_date=data['reservation_date'],
                reservation_slot=data['reservation_slot'],
            )
            booking.save()
        else:
            return HttpResponse("{'error':1}", content_type='application/json')
    
    date = request.GET.get('date',datetime.today().date())
    bookings = Booking.objects.all().filter(reservation_date=date)
    booking_json = serializers.serialize('json', bookings)

    return HttpResponse(booking_json, content_type='application/json')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def managers(request):
    username = request.data['username']
    if username:
        user = get_object_or_404(User, username=username)
        managers = Group.objects.get(name="Manager")
        if request.method == 'POST':
            managers.user_set.add(user)
        elif request.method == 'DELETE':
            managers.user_set.remove(user)
        return Response({"message": "ok"})
    return Response({"message": "error"}, status.HTTP_400_BAD_REQUEST)

@api_view()
@permission_classes([IsAdminUser])
def manager_view(request):
    return Response({"message": "Only Admin should see this"}) 


@api_view(['POST'])
@permission_classes([AllowAny])
def manager_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if username and password:
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.groups.filter(name='Manager').exists():
                login(request, user)
                return Response({"message": "Login successful", "username":user.username})
            else:
                return Response({"message":"You are not authorized to log in as a manager. "}, status=403)
        else:
            return Response({"message": "Invalid credentials."}, status=401)
    return Response({"message": "Username and password required. "}, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_menu_item(request):
    serializer = MenuItemSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"detail": "Menu item added successfully."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view()
def single_item(request, id):
    items = get_object_or_404(MenuItem, pk=id)
    serialized_item = MenuItemSerializer(items)
    return Response(serialized_item.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    serializer = OrderSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Order placed successfully"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_customer_orders(request):
    customer = request.user
    orders = Order.objects.filter(customer=customer)
    if not orders.exists():
        return Response({"detail": "No orders found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    customer = request.user
    cart, created = Cart.objects.get_or_create(customer=customer)
    serializer = CartItemSerializer(data=request.data)
    if serializer.is_valid():
        menu_item = serializer.validated_data['menu_item']
        quantity = serializer.validated_data['quantity']
        cart_item, created = CartItem.objects.get_or_create(cart=cart, menu_item=menu_item)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()
        return Response({'detail': 'Item added !'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RatingsView(generics.ListCreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    def get_permissions(self):
        if(self.request.method=='GET'):
            return []
        return [IsAuthenticated()]
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])  
def update_item_of_the_day(request):
    if request.user.groups.filter(name='Manager').exists():
        item_id = request.data.get('item_id') 
        if item_id is not None:
            item_of_the_day = get_object_or_404(MenuItem, id=item_id)
            item_of_the_day.item_of_the_day = True
            item_of_the_day.save()
            return Response({"message": f"{item_of_the_day.title} is now the item of the day!"}, status=status.HTTP_200_OK)
        return Response({"message": "Item ID not provided"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "You are not authorized to perform this action"}, status=status.HTTP_403_FORBIDDEN)

