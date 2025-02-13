from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import EC_Product

# Create your views here.

def all_ec_products(request):
    """ A view to show all ec products, including sorting and search queries """

    ec_products = EC_Product.objects.all()
    query = None

    if request.GET:
        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(request, "You didn't enter any search criteria!")
                return redirect(reverse('ec_products'))
            
            queries = Q(name__icontains=query) | Q(description__icontains=query)
            ec_products = ec_products.filter(queries)







    context = {
        'ec_products': ec_products,
    }

    return render(request, 'ec_products/ec_products.html', context)


def ec_product_detail(request, ec_product_id):
    """ A view to show individual product details """

    ec_product = get_object_or_404(EC_Product, pk=ec_product_id)

    context = {
        'ec_product': ec_product,
    }

    return render(request, 'ec_products/ec_product_detail.html', context)