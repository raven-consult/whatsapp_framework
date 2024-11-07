import os
from typing import List

from whatsapp import Conversation, instruction
from whatsapp._datastore import SQLiteDatastore

from restaurant_attendant.database import Products
from restaurant_attendant.payments import Paystack
from restaurant_attendant.tasks import job_thread, collection


WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")


class RestaurantAttendantConversation(Conversation):
    token = WHATSAPP_TOKEN
    whatsapp_number = WHATSAPP_NUMBER
    payments = Paystack(PAYSTACK_SECRET_KEY)

    datastore = SQLiteDatastore("restaurant_attendant.db")

    system_message = """\
You are a sales representative for The place restaurant, Your job is to do the following:
- Process orders from a customer
- Help the customer check if a product is available

If there's any data that you need always ask the customer for it.
    """

    @instruction
    def get_product_info(self, product_id: str):
        try:
            product = Products.from_id(product_id)

            return {
                "name": product.name,
                "price": product.price,
                "image": product.image,
                "labels": product.labels,
                "id": product.product_id,
                "description": product.description,
            }
        except Exception as e:
            print(e)
            return str(e)

    @instruction
    def create_payment_link(self, email: str, product_ids: List[str]):
        """Create a payment link to pay for a list of products. Returns a link to the payment page."""

        price = float(0)
        for product_id in product_ids:
            product = Products.from_id(product_id)
            price += float(product.price or 0.00)
        price_kobo = int(price * 100)

        try:
            res = self.payments.initialize_payment(price_kobo, email)
            return res
        except Exception as e:
            print(e)
            return str(e)

    @instruction
    def verify_payment_status(self, reference: str):
        """Verify that a payment is successful or failed. Returns True if successful, False otherwise."""

        try:
            res = self.payments.verify_payment(reference)
            return res["data"]["status"] == "success"
        except Exception as e:
            print(e)
            return str(e)

    @instruction
    def check_inventory(self, query: str = ""):
        """Executes a semantic search for products in the inventory that matches the query. Returns a list of products."""

        try:
            results = collection.query(
                n_results=5,
                query_texts=[query],
            )

            products = []
            for product_id in results["ids"][0]:
                product = Products.from_id(product_id)
                products.append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "labels": product.labels,
                    "payment_id": product.product_id,
                    "description": product.description,
                })

            return products
        except Exception as e:
            print(e)
            return str(e)


def main():
    chat_handler = RestaurantAttendantConversation(
        debug=True, start_proxy=False,
        gemini_model_name="models/gemini-1.5-pro",
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
    # job_thread.start()
    chat_handler.start(5000)
