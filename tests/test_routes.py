######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from urllib.parse import quote_plus
from unittest import TestCase

from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service Route Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Run after each test"""
        db.session.remove()

    ##################################################################
    # Utility helpers
    ##################################################################
    def _create_products(self, count=1):
        """Create one or more products via the API"""
        products = []
        for _ in range(count):
            product = ProductFactory()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            data = response.get_json()
            product.id = data["id"]
            products.append(product)
        return products

    def _get_product_count(self):
        """Return the number of products in the service"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return len(response.get_json())

    ##################################################################
    # Basic routes
    ##################################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should return a healthy status"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["message"], "OK")

    ##################################################################
    # CREATE
    ##################################################################
    def test_create_product(self):
        """It should create a new Product"""
        product = ProductFactory()
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.get_json()
        self.assertEqual(data["name"], product.name)
        self.assertEqual(Decimal(data["price"]), product.price)

    def test_create_product_no_name(self):
        """It should not create a Product without a name"""
        product = ProductFactory()
        payload = product.serialize()
        del payload["name"]

        response = self.client.post(BASE_URL, json=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not create a Product without Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="text/plain")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_invalid_json(self):
        """It should handle invalid JSON on create"""
        response = self.client.post(
            BASE_URL,
            data="{invalid json}",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # READ
    ##################################################################
    def test_get_product(self):
        """It should retrieve a Product by id"""
        product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_product_not_found(self):
        """It should not retrieve a Product that does not exist"""
        response = self.client.get(f"{BASE_URL}/999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_products(self):
        """It should list all Products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), 5)

    ##################################################################
    # QUERY
    ##################################################################
    def test_query_by_name(self):
        """It should query Products by name"""
        products = self._create_products(5)
        name = products[0].name
        expected = len([p for p in products if p.name == name])

        response = self.client.get(
            BASE_URL, query_string=f"name={quote_plus(name)}"
        )
        self.assertEqual(len(response.get_json()), expected)

    def test_query_by_category(self):
        """It should query Products by category"""
        products = self._create_products(10)
        category = products[0].category

        response = self.client.get(
            BASE_URL, query_string=f"category={category.name}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_query_by_availability(self):
        """It should query Products by availability"""
        products = self._create_products(10)
        available_count = len([p for p in products if p.available])

        response = self.client.get(BASE_URL, query_string="available=true")
        self.assertEqual(len(response.get_json()), available_count)

    ##################################################################
    # UPDATE
    ##################################################################
    def test_update_product(self):
        """It should update an existing Product"""
        product = self._create_products(1)[0]
        payload = product.serialize()
        payload["description"] = "updated"

        response = self.client.put(f"{BASE_URL}/{product.id}", json=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["description"], "updated")

    def test_update_product_not_found(self):
        """It should not update a Product that does not exist"""
        response = self.client.put(f"{BASE_URL}/999", json={"name": "Ghost"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_no_content_type(self):
        """It should not update a Product without Content-Type"""
        product = self._create_products(1)[0]
        response = self.client.put(
            f"{BASE_URL}/{product.id}", data="bad"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_product_invalid_json(self):
        """It should handle invalid JSON on update"""
        product = self._create_products(1)[0]
        response = self.client.put(
            f"{BASE_URL}/{product.id}",
            data="{invalid json}",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # DELETE
    ##################################################################
    def test_delete_product(self):
        """It should delete an existing Product"""
        products = self._create_products(3)
        count_before = self._get_product_count()

        response = self.client.delete(f"{BASE_URL}/{products[0].id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        count_after = self._get_product_count()
        self.assertEqual(count_after, count_before - 1)
