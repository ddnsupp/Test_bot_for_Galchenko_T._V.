from django.db import models
from django.contrib.postgres.fields import ArrayField


class User(models.Model):
    t_id = models.BigIntegerField()
    username = models.CharField(max_length=255, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    user_type = models.CharField(max_length=20, default='Customer')
    messages_to_delete = ArrayField(models.IntegerField(), default=list)


class Product(models.Model):
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100)
    product_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    quantity = models.IntegerField()


class ProductPhoto(models.Model):
    url = models.CharField(max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class CartProduct(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()


class Newsletter(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

