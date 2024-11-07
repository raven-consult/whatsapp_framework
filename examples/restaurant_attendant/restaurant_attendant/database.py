import os
from pyairtable.orm import Model, fields as F


class Products(Model):
    product_id = F.AutoNumberField("Id")
    name = F.TextField("Name")
    price = F.NumberField("Price")
    description = F.TextField("Description")
    is_active = F.CheckboxField("Active")
    image = F.TextField("Image")
    labels = F.MultipleSelectField("Labels")

    class Meta:
        base_id = "appN7fjwVkXIFPx7P"
        table_name = "The Place Restaurant"

        @staticmethod
        def api_key():
            return os.getenv("AIRTABLE_API_KEY")
