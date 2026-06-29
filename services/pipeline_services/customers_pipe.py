from  services.api_services.customer_api import get_customers
from  services.db_services.customer_db import add_customers, delete_all_customers
from  services.db_services.models import Customer


def pipe_customers():
    try:
        customers = get_customers()
        customers_db = list[Customer]()
        for customer in customers:
            customer_db = Customer(
                 customer_id = customer.customer_id,
                 customer_age = customer.customer_age,
                 customer_gender = customer.customer_gender,
                 ethnicity = customer.ethnicity
            )
            customers_db.append(customer_db)
        add_customers(customers_db)
    except Exception as e:
            raise e