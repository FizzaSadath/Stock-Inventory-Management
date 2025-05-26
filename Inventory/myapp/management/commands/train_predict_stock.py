import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from django.core.management.base import BaseCommand
from myapp.models import ItemMaster, GoodsIn, GoodsOut, StockForecast  # Replace 'myapp' with your app name

class Command(BaseCommand):
    help = 'Train model to predict incoming stock based on GoodsIn history for all items.'

    def handle(self, *args, **kwargs):
        # Optional: Clear old predictions
        StockForecast.objects.all().delete()

        items = ItemMaster.objects.all()
        if not items.exists():
            self.stdout.write(self.style.WARNING("⚠️ No items found in ItemMaster."))
            return

        for item in items:
            # Group incoming quantities by date
            goods_in_qs = GoodsIn.objects.filter(ITEM=item)
            if goods_in_qs.count() < 2:
                self.stdout.write(self.style.WARNING(f"⚠️ Not enough GoodsIn data for item {item.item_name}. Skipping."))
                continue

            df = pd.DataFrame.from_records(
                goods_in_qs.values('date_added', 'quantity')
            )

            df['date'] = df['date_added'].dt.date
            daily_incoming = df.groupby('date')['quantity'].sum().reset_index()
            daily_incoming['day_num'] = np.arange(len(daily_incoming))

            X = daily_incoming[['day_num']]
            y = daily_incoming['quantity']

            model = LinearRegression()
            model.fit(X, y)

            next_day_num = [[len(daily_incoming)]]
            predicted_quantity = model.predict(next_day_num)[0]

            StockForecast.objects.create(
                ITEM=item,
                predicted_quantity=int(round(predicted_quantity))
            )

            self.stdout.write(self.style.SUCCESS(
                f"✅ {item.item_name}: Predicted {int(round(predicted_quantity))} units for next day."
            ))

        self.stdout.write(self.style.SUCCESS("🎯 All item predictions completed."))
