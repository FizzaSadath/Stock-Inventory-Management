from django.shortcuts import render, redirect, get_object_or_404
from .models import ItemMaster, GoodsIn, GoodsOut, StockForecast
from django.utils.dateparse import parse_date
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from django.db.models import F
from itertools import zip_longest
from collections import defaultdict
from django.shortcuts import render, redirect

def dashboard(request):
    forecasts = StockForecast.objects.select_related('ITEM').order_by('-prediction_date')[:10]
    return render(request, 'dashboard.html', {'forecasts': forecasts})

def add_item(request):
    return render(request, 'add_item.html')

def add_item_post(request):
    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        description = request.POST.get('description')
        expiry = request.POST.get('expiry')
        entry_number = request.POST.get('entry_number')


        has_expiry = True if expiry == 'Yes' else False
        has_entry_number = True if entry_number == 'Yes' else False


        ob = ItemMaster(
            item_name=item_name,
            description=description,
            has_expiry=has_expiry,
            has_entry_number=has_entry_number
        )
        ob.save()
        return redirect('dashboard')

    return redirect('add_item')



def delete_item(request):
    items = ItemMaster.objects.all()
    return render(request, 'delete_item.html', {'items': items})

def delete_item_post(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        try:
            item = ItemMaster.objects.get(id=item_id)
            item.delete()
        except ItemMaster.DoesNotExist:
            pass
    return redirect('dashboard')


def add_stock(request):
    items = ItemMaster.objects.all()
    item_metadata = {
        str(item.id): {
            'has_expiry': item.has_expiry,
            'has_entry_number': item.has_entry_number
        } for item in items
    }

    return render(request, 'GoodsIn.html', {
        'items': items,
        'item_metadata_json': json.dumps(item_metadata)
    })


def add_stock_post(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        quantity = request.POST.get('quantity')

        raw_expiry = request.POST.get('expiry_date', '').strip()
        raw_entry = request.POST.get('entry_number', '').strip()

        try:
            item = ItemMaster.objects.get(id=item_id)
        except ItemMaster.DoesNotExist:
            return redirect('add_stock')  # or show an error

        # Parse and validate
        expiry_date = parse_date(raw_expiry) if item.has_expiry and raw_expiry else None
        entry_number = raw_entry if item.has_entry_number and raw_entry else None

        goods_in = GoodsIn(
            ITEM=item,
            quantity=int(quantity),
            net_quantity=int(quantity),
            expiry_date=expiry_date,
            entry_number=entry_number
        )
        goods_in.save()

        return redirect('dashboard')


def remove_stock(request):
    items = ItemMaster.objects.all()
    return render(request, 'GoodsOut.html', {'items': items})


@transaction.atomic
def remove_stock_post(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        quantity_to_remove = int(request.POST.get('quantity'))

        item = get_object_or_404(ItemMaster, id=item_id)


        if item.has_expiry:
            batches = GoodsIn.objects.filter(ITEM=item, net_quantity__gt=0).order_by('expiry_date', 'date_added')
        elif item.has_entry_number:
            batches = GoodsIn.objects.filter(ITEM=item, net_quantity__gt=0).order_by('entry_number', 'date_added')
        else:
            batches = GoodsIn.objects.filter(ITEM=item, net_quantity__gt=0).order_by('date_added')

        quantity_left = quantity_to_remove

        for batch in batches:
            if quantity_left <= 0:
                break

            if batch.net_quantity <= quantity_left:

                quantity_left -= batch.net_quantity

                GoodsOut.objects.create(
                    ITEM=item,
                    quantity=batch.net_quantity
                )

                batch.net_quantity = 0
                batch.save()
            else:

                batch.net_quantity -= quantity_left

                GoodsOut.objects.create(
                    ITEM=item,
                    quantity=quantity_left
                )

                quantity_left = 0
                batch.save()

        if quantity_left > 0:

            error = f"Not enough stock to remove. {quantity_left} items could not be removed."
            items = ItemMaster.objects.all()
            return render(request, 'GoodsOut.html', {'items': items, 'error': error})

        return redirect('dashboard')

    return redirect('remove_stock')

from django.db.models import Sum

def view_stock(request):
    search_query = request.GET.get('search', '').strip()
    items = ItemMaster.objects.all()

    goods_in = GoodsIn.objects.select_related('ITEM')
    goods_out = GoodsOut.objects.select_related('ITEM')

    if search_query:
        goods_in = goods_in.filter(ITEM__item_name=search_query)
        goods_out = goods_out.filter(ITEM__item_name=search_query)

    # Use item_name as key to merge data
    combined_data = []

    # Group GoodsOut entries by item name
    goods_out_map = defaultdict(list)
    for out in goods_out:
        goods_out_map[out.ITEM.item_name].append(out)

    for entry in goods_in:
        item_name = entry.ITEM.item_name
        related_out = goods_out_map[item_name].pop(0) if goods_out_map[item_name] else None

        combined_data.append({
            'item_name': item_name,
            'date_added': entry.date_added,
            'quantity_in': entry.quantity,
            'expiry_date': entry.expiry_date,
            'entry_number': entry.entry_number,
            'net_quantity': entry.net_quantity,
            'date_removed': related_out.date_removed if related_out else None,
            'quantity_out': related_out.quantity if related_out else None
        })

    # Add remaining GoodsOut entries that didn't match any GoodsIn
    for leftover in goods_out_map.values():
        for out in leftover:
            combined_data.append({
                'item_name': out.ITEM.item_name,
                'date_added': None,
                'quantity_in': None,
                'expiry_date': None,
                'entry_number': None,
                'net_quantity': None,
                'date_removed': out.date_removed,
                'quantity_out': out.quantity
            })

    # Total stock per item (net_quantity), filtered by search
    filtered_goods_in = GoodsIn.objects.select_related('ITEM')
    if search_query:
        filtered_goods_in = filtered_goods_in.filter(ITEM__item_name=search_query)

    total_stock = filtered_goods_in.values('ITEM__item_name').annotate(total_net=Sum('net_quantity'))
    stock_summary = {entry['ITEM__item_name']: entry['total_net'] for entry in total_stock}

    return render(request, 'StockReport.html', {
        'combined_data': combined_data,
        'items': items,
        'search_query': search_query,
        'stock_summary': stock_summary
    })

def dashboard(request):
    forecasts = StockForecast.objects.select_related('ITEM').order_by('-prediction_date')[:10]
    return render(request, 'dashboard.html', {'forecasts': forecasts})