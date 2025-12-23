# Copyright 2016, 2023 John J. Rofrano.
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

"""
Test cases for Product Model
"""
import os
import logging
import unittest
from decimal import Decimal

from service import app
from service.models import Product, Category, db
from service.common.error_handlers import DataValidationError
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Run after each test"""
        db.session.remove()

    ##################################################################
    # HAPPY PATH TESTS
    ##################################################################
    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(
            name="Fedora",
            description="A red hat",
            price=12.50,
            available=True,
            category=Category.CLOTHS,
        )
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertIsNone(product.id)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertTrue(product.available)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        self.assertEqual(Product.all(), [])

        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)
        self.assertEqual(len(Product.all()), 1)

    def test_read_a_product(self):
        """It should Read a Product"""
        product = ProductFactory()
        product.create()
        found = Product.find(product.id)
        self.assertEqual(found.id, product.id)

    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        product.create()
        product.description = "updated"
        product.update()
        found = Product.find(product.id)
        self.assertEqual(found.description, "updated")

    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all Products"""
        self.assertEqual(Product.all(), [])
        for _ in range(5):
            ProductFactory().create()
        self.assertEqual(len(Product.all()), 5)

    def test_find_by_name(self):
        """It should Find Products by Name"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        found = Product.find_by_name(products[0].name)
        self.assertGreater(found.count(), 0)

    def test_find_by_availability(self):
        """It should Find Products by Availability"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        found = Product.find_by_availability(products[0].available)
        self.assertGreater(found.count(), 0)

    def test_find_by_category(self):
        """It should Find Products by Category"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        found = Product.find_by_category(products[0].category)
        self.assertGreater(found.count(), 0)

    ##################################################################
    # ERROR / DEFENSIVE CODE COVERAGE
    ##################################################################
    def test_deserialize_with_no_data(self):
        """It should raise DataValidationError when data is None"""
        self.assertRaises(DataValidationError, Product().deserialize, None)

    def test_deserialize_with_wrong_type(self):
        """It should raise DataValidationError when data is not a dict"""
        self.assertRaises(DataValidationError, Product().deserialize, "not a dict")

    def test_deserialize_missing_name(self):
        """It should raise DataValidationError when name is missing"""
        data = {
            "description": "Test",
            "price": "10.0",
            "available": True,
            "category": "CLOTHS",
        }
        self.assertRaises(DataValidationError, Product().deserialize, data)

    def test_deserialize_with_invalid_price(self):
        """It should raise DataValidationError for invalid price"""
        data = {
            "name": "Test",
            "description": "Test",
            "price": "free",
            "available": True,
            "category": "CLOTHS",
        }
        self.assertRaises(DataValidationError, Product().deserialize, data)

    def test_deserialize_with_invalid_available(self):
        """It should raise DataValidationError for invalid available type"""
        data = {
            "name": "Test",
            "description": "Test",
            "price": "10.0",
            "available": "yes",
            "category": "CLOTHS",
        }
        self.assertRaises(DataValidationError, Product().deserialize, data)

    def test_deserialize_with_invalid_category(self):
        """It should raise DataValidationError for invalid category"""
        data = {
            "name": "Test",
            "description": "Test",
            "price": "10.0",
            "available": True,
            "category": "INVALID",
        }
        self.assertRaises(DataValidationError, Product().deserialize, data)

    def test_update_without_id_raises_error(self):
        """It should raise DataValidationError when updating without id"""
        product = Product(
            name="Test",
            description="Test",
            price=Decimal("10.0"),
            available=True,
            category=Category.CLOTHS,
        )
        self.assertRaises(DataValidationError, product.update)
