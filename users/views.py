from django.shortcuts import render
from .models import Farmer, Farm_Tag, Farm_Image, Subscribe
from products.models import Category
from django.db.models import Count
from math import ceil

def farmers_page(request):
    page=int(request.GET.get('page', 1))
    page_size = 15
    limit = page_size * page
    offset = limit - page_size
    farmers_count = Farmer.objects.all().count()

    farmers = Farmer.objects.annotate(sub_counts=Count('subs')) # 구독자 수 필드 임의 추가
    best_farmers = farmers.order_by('-sub_counts')[:3]
    # farmers = Farmer.objects.all()
    # best_farmers = farmers.order_by('-sub_count')[:3]
    
    page_total = ceil(farmers_count/page_size)

    categories = Category.objects.filter(parent=None)
    for farmer in farmers:
        print(farmer)
        print(farmer.farm_images)

    ctx = {
        'page':page,
        'page_total':page_total,
        'page_range':range(1, page_total),
        'farmers': farmers,
        'best_farmers': best_farmers,
        "categories": categories,
    }
    return render(request, 'users/farmers_page.html', ctx)



def farmer_detail(request, pk):
    farmer = Farmer.objects.get(pk=pk)
    ctx = {
        'farmer':farmer,
    }
    return render(request, 'users/farmer_detail.html', ctx)