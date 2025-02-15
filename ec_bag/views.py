 

from django.shortcuts import render, redirect, HttpResponse,reverse
from django.contrib import messages
from ec_products.models import EC_Product

# from django.urls import reverse

# Create your views here.

def view_ec_bag(request):
    """ A view to renders the ec_bag contents page """

    return render(request, 'ec_bag/ec_bag.html')


def add_to_ec_bag(request, item_id):
    """ Add a quantity of the specified ec_product to the shopping ec_bag """

    ec_product = EC_Product.objects.get(pk=item_id)
    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    size = None
    if 'ec_product_size' in request.POST:
        size = request.POST['ec_product_size']
    ec_bag = request.session.get('ec_bag', {})

    if size:
        if item_id in list(ec_bag.keys()):
            if size in ec_bag[item_id]['items_by_size'].keys():
                ec_bag[item_id]['items_by_size'][size] += quantity
            else:
                ec_bag[item_id]['items_by_size'][size] = quantity
        else:
            ec_bag[item_id] = {'items_by_size': {size: quantity}}
    else:
        if item_id in list(ec_bag.keys()):
            ec_bag[item_id] += quantity
        else:
            ec_bag[item_id] = quantity
            messages.success(request, f'Added {ec_product.name} to your bag')

    request.session['ec_bag'] = ec_bag
    # print(request.session['ec_bag'])
    return redirect(redirect_url)



def adjust_ec_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount"""
    
    quantity = int(request.POST.get('quantity'))
    size = None
    if 'ec_product_size' in request.POST:
        size = request.POST['ec_product_size']
    ec_bag = request.session.get('ec_bag', {})
    if size:
        if quantity > 0:
            ec_bag[item_id]['items_by_size'][size] = quantity
        else:
            del ec_bag[item_id]['items_by_size'][size]
            if not ec_bag[item_id]['items_by_size']:
                ec_bag.pop(item_id)
    else:
        if quantity > 0:
            ec_bag[item_id] = quantity
        else:
            ec_bag.pop(item_id)
    request.session['ec_bag'] = ec_bag
    return redirect(reverse('view_ec_bag'))

def remove_from_ec_bag(request, item_id):
    """Remove the item from the shopping ec_bag"""
    try:
        size = None
        if 'ec_product_size' in request.POST:
            size = request.POST['ec_product_size']
        ec_bag = request.session.get('ec_bag', {})
        if size:
            del ec_bag[item_id]['items_by_size'][size]
            if not ec_bag[item_id]['items_by_size']:
                ec_bag.pop(item_id)
        else:
            ec_bag.pop(item_id)
        request.session['ec_bag'] = ec_bag
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(status=500)
 
    