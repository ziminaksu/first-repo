from rest_framework import serializers
from .models import Rating, MenuItem, Order, OrderAssignment, OrderItem
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Category, CartItem
from django.contrib.auth.models import User


class RatingSerializer (serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
            queryset=User.objects.all(),
            default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Rating
        fields = ['user', 'menuitem_id', 'rating']
        validators = [UniqueTogetherValidator(queryset=Rating.objects.all(),fields=['user', 'menuitem_id'])]
        extra_kwargs = {
            'rating': {'min_value': 0, 'max_value':5},
        }
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']

class MenuItemSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(source='inventory')
    price_after_tax = serializers.SerializerMethodField(method_name='calculate_tax')
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'stock', 'price_after_tax', 'category']
    def calculate_tax(self, product: MenuItem):
        return product.price * Decimal(1.1)
    def create(self, validated_data):
        category = validated_data.pop('category')
        menu_item = MenuItem.objects.create(category=category, **validated_data)
        return menu_item
    
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)
    customer = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'order_items', 'created_at', 'status']
    def create(self, validated_data):
        order_items_data = validated_data.pop('order_items')
        customer = self.context['request'].user
        order = Order.objects.create(customer=customer, **validated_data)
        for order_item_data in order_items_data:
            OrderItem.objects.create(order=order, **order_item_data)
        return order 
    
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['menu_item', 'quantity']
    def validate(self, data):
        menu_item = data['menu_item']
        quantity = data['quantity']
        if menu_item.inventory < quantity:
            raise serializers.ValidationError("Not enough stock available.")
        return data
