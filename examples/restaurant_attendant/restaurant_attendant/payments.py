import requests
from datetime import datetime
from typing import Optional, TypedDict


class PaymentRequest(TypedDict):
    amount: int
    reference: str
    access_code: str
    authorization_url: str


class HistoryEntry(TypedDict):
    type: str
    message: str
    time: int


class Authorization(TypedDict):
    last4: str
    channel: str
    card_type: str
    bank: str
    country_code: str


class Customer(TypedDict):
    email: str
    international_format_phone: Optional[str]


class Data(TypedDict):
    id: int
    domain: str
    status: str
    reference: str
    amount: int
    paid_at: datetime
    created_at: datetime
    channel: str
    currency: str
    fees: int
    customer: Customer
    paidAt: datetime
    createdAt: datetime
    requested_amount: int
    transaction_date: datetime
    authorization: Authorization


class Response(TypedDict):
    status: bool
    message: str
    data: Data


class Paystack:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.base_url = "https://api.paystack.co"

    def initialize_payment(self, amount: int, email: str, reference=None) -> PaymentRequest:
        url = f"{self.base_url}/transaction/initialize"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        data = {
            "email": email,
            "amount": amount,
            "reference": reference
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(response.json())

        response_data = response.json()
        access_code = response_data["data"]["access_code"]
        authorization_url = response_data["data"]["authorization_url"]
        reference = response_data["data"]["reference"] if reference is None else reference

        return {
            "amount": amount,
            "reference": reference,
            "access_code": access_code,
            "authorization_url": authorization_url
        }

    def verify_payment(self, reference: str) -> Response:
        url = f"{self.base_url}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }
        response = requests.get(url, headers=headers)
        res = response.json()
        if response.status_code != 200:
            raise Exception(res["message"])

        return res
