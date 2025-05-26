from django.db import models

class ItemMaster(models.Model):
    item_name=models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    has_expiry=models.BooleanField(default=False)
    has_entry_number=models.BooleanField(default=False)

class GoodsIn(models.Model):
    ITEM = models.ForeignKey(ItemMaster, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    net_quantity = models.IntegerField(null=True)
    expiry_date = models.DateField(null=True, blank=True)
    entry_number = models.CharField(max_length=100, null=True, blank=True)  # <-- use CharField
    date_added = models.DateTimeField(auto_now_add=True)


class GoodsOut(models.Model):
    ITEM = models.ForeignKey(ItemMaster, on_delete=models.CASCADE)
    quantity=models.IntegerField()
    date_removed=models.DateTimeField(auto_now_add=True)

from myapp.models import ItemMaster  # or from myapp.models if needed

class StockForecast(models.Model):
    ITEM = models.ForeignKey(ItemMaster, on_delete=models.CASCADE)
    prediction_date = models.DateField(auto_now_add=True)
    predicted_quantity = models.IntegerField()

    def __str__(self):
        return f"{self.ITEM} - {self.predicted_quantity} on {self.prediction_date}"
