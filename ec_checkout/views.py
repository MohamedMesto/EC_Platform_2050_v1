from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from .forms import EC_OrderForm
from .models import EC_Order, EC_OrderLineItem
from ec_products.models import EC_Product
from ec_profiles.forms import EC_UserProfileForm
from ec_profiles.models import EC_UserProfile
from ec_bag.contexts import ec_bag_contents

import stripe
import json
import os

@require_POST
def cache_checkout_data(request):
    try:
        pid = request.POST.get('client_secret').split('_secret')[0]
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.PaymentIntent.modify(pid, metadata={
            'ec_bag': json.dumps(request.session.get('ec_bag', {})),
            'save_info': request.POST.get('save_info'),
            'username': request.user,
        })
        return HttpResponse(status=200)
    except Exception as e:
        messages.error(request, 'Sorry, your payment cannot be \
            processed right now. Please try again later.')
        return HttpResponse(content=e, status=400)
    
def ec_checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == 'POST':
        ec_bag = request.session.get('ec_bag', {})
    
        form_data = {
            'full_name': request.POST['full_name'],
            'email': request.POST['email'],
            'phone_number': request.POST['phone_number'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
            'town_or_city': request.POST['town_or_city'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'county': request.POST['county'],
        }
        ec_order_form = EC_OrderForm(form_data)
        if ec_order_form.is_valid():
            ec_order = ec_order_form.save(commit=False)
            pid = request.POST.get('client_secret').split('_secret')[0]
            ec_order.stripe_pid = pid
            ec_order.original_ec_bag = json.dumps(ec_bag)
            ec_order.save()
            for item_id, item_data in ec_bag.items():
                try:
                    ec_product = EC_Product.objects.get(id=item_id)
                    if isinstance(item_data, int):
                        ec_order_line_item = EC_OrderLineItem(
                        ec_order=ec_order,
                        ec_product=ec_product,
                        quantity=item_data,
                        )
                        ec_order_line_item.save()
                    else:
                        for size, quantity in item_data['items_by_size'].items():
                            ec_order_line_item = EC_OrderLineItem(
                                ec_order=ec_order,
                                ec_product=ec_product,
                                quantity=quantity,
                                ec_product_size=size,
                            )
                            ec_order_line_item.save()
                except EC_Product.DoesNotExist:
                    messages.error(request, (
                        "One of the ec_products in your ec_bag wasn't found in our database. "
                        "Please call us for assistance!")
                    )
                    ec_order.delete()
                    return redirect(reverse('view_ec_bag'))

            request.session['save_info'] = 'save-info' in request.POST
            return redirect(reverse('checkout_success', args=[ec_order.ec_order_number]))
        else:
            messages.error(request, 'There was an error with your form. \
                            Please double check your information.')
    else:
        ec_bag = request.session.get('ec_bag', {})
        if not ec_bag:
            messages.error(request, "There's nothing in your ec_bag at the moment")
            return redirect(reverse('ec_products'))

        current_ec_bag = ec_bag_contents(request)
        total = current_ec_bag['grand_total']
        stripe_total = round(total * 100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )
       
        if request.user.is_authenticated:
            try:
                ec_profile = EC_UserProfile.objects.get(user=request.user)
                ec_order_form = EC_OrderForm(initial={
                    'full_name': ec_profile.user.get_full_name(),
                    'email': ec_profile.user.email,
                    'phone_number': ec_profile.default_phone_number,
                    'country': ec_profile.default_country,
                    'postcode': ec_profile.default_postcode,
                    'town_or_city': ec_profile.default_town_or_city,
                    'street_address1': ec_profile.default_street_address1,
                    'street_address2': ec_profile.default_street_address2,
                    'county': ec_profile.default_county,
                })
            except EC_UserProfile.DoesNotExist:
                ec_order_form = EC_OrderForm()
        else:
            ec_order_form = EC_OrderForm()


    if not stripe_public_key:
        messages.warning(request, 'Stripe public key is missing. \
            Did you forget to set it in your environment?')

    template = 'ec_checkout/ec_checkout.html'
    context = {
        'ec_order_form': ec_order_form,
        'stripe_public_key': stripe_public_key,
       ## 'client_secret': intent.stripe_secret_key,
        'client_secret': intent.client_secret,
    }
    return render(request, template, context)


def checkout_success(request, ec_order_number):
    """
    Handle successful checkouts
    """
    save_info = request.session.get('save_info')
    ec_order = get_object_or_404(EC_Order, ec_order_number=ec_order_number)

    if request.user.is_authenticated:
        ec_profile = EC_UserProfile.objects.get(user=request.user)
        # Attach the user's profile to the ec_order
        ec_order.ec_user_profile = ec_profile
        ec_order.save()

        # Save the user's info
        if save_info:
            ec_profile_data = {
                'default_phone_number': ec_order.phone_number,
                'default_country': ec_order.country,
                'default_postcode': ec_order.postcode,
                'default_town_or_city': ec_order.town_or_city,
                'default_street_address1': ec_order.street_address1,
                'default_street_address2': ec_order.street_address2,
                'default_county': ec_order.county,
            }
            user_profile_form = EC_UserProfileForm(ec_profile_data, instance=ec_profile)
            if user_profile_form.is_valid():
                user_profile_form.save()


    messages.success(request, f'EC_Order successfully processed! \
        Your ec_order number is {ec_order_number}. A confirmation \
        email will be sent to {ec_order.email}.')
    
    if 'ec_bag' in request.session:
        del request.session['ec_bag']

    template = 'ec_checkout/checkout_success.html'
    context = {
        'ec_order': ec_order,
    }

    return render(request, template, context)