import os
import time
import schedule
import threading

import chromadb
import chromadb.utils.embedding_functions as embedding_functions

from restaurant_attendant.database import Products


client = chromadb.PersistentClient(path="./embeddings.db")
google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=os.environ.get("GEMINI_API_KEY", ""),
)

collection = client.create_collection(
    name="products",
    get_or_create=True,
    embedding_function=google_ef,
)


def job():
    print("Generating embeddings...")
    products = Products.all()

    ids = [str(product.id) for product in products]
    data = [f"Name: {product.name}\nDescription: {product.description}"
            for product in products]

    collection.upsert(
        ids=ids,
        documents=data,
    )
    print("Done generating embeddings.")


schedule.every(40).seconds.do(job)


def background_task():
    while True:
        schedule.run_pending()
        time.sleep(1)


job_thread = threading.Thread(target=background_task)
