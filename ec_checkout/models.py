import uuid

from django.db import models
from django.db.models import Sum
from django.conf import settings

from django_countries.fields import CountryField

from ec_products.models import EC_Product
from ec_profiles.models import EC_UserProfile



class EC_Order(models.Model):


    class Meta:
        verbose_name_plural = 'EC_Orders'


    ec_order_number = models.CharField(max_length=32, null=False, editable=False)
    ec_user_profile = models.ForeignKey(EC_UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='ec_orders')
    full_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(max_length=254, null=False, blank=False)
    phone_number = models.CharField(max_length=20, null=False, blank=False)
    country = CountryField(blank_label='Country *', null=False, blank=False)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    town_or_city = models.CharField(max_length=40, null=False, blank=False)
    street_address1 = models.CharField(max_length=80, null=False, blank=False)
    street_address2 = models.CharField(max_length=80, null=True, blank=True)
    county = models.CharField(max_length=80, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    delivery_cost = models.DecimalField(max_digits=6, decimal_places=2, null=False, default=0)
    ec_order_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    original_ec_bag = models.TextField(null=False, blank=False, default='')
    stripe_pid = models.CharField(max_length=254, null=False, blank=False, default='')

    def _generate_ec_order_number(self):
        """
        Generate a random, unique ec_order number using UUID
        """
        return uuid.uuid4().hex.upper()

    def update_total(self):
        """
        Update grand total each time a line item is added,
        accounting for delivery costs.
        """
        self.ec_order_total = self.lineitems.aggregate(Sum('lineitem_total'))['lineitem_total__sum'] or 0
        if self.ec_order_total < settings.FREE_DELIVERY_THRESHOLD:
            self.delivery_cost = self.ec_order_total * settings.STANDARD_DELIVERY_PERCENTAGE / 100
        else:
            self.delivery_cost = 0
        self.grand_total = self.ec_order_total + self.delivery_cost
        self.save()

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the ec_order number
        if it hasn't been set already.
        """
        if not self.ec_order_number:
            self.ec_order_number = self._generate_ec_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ec_order_number


class EC_OrderLineItem(models.Model):
    ec_order = models.ForeignKey(EC_Order, null=False, blank=False, on_delete=models.CASCADE, related_name='lineitems')
    ec_product = models.ForeignKey(EC_Product, null=False, blank=False, on_delete=models.CASCADE)
    ec_product_size = models.CharField(max_length=2, null=True, blank=True) # XS, S, M, L, XL
    quantity = models.IntegerField(null=False, blank=False, default=0)
    lineitem_total = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False, editable=False)

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the lineitem total
        and update the ec_order total.
        """
        self.lineitem_total = self.ec_product.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f'SKU {self.ec_product.sku} on ec_order {self.ec_order.ec_order_number}'