"""WooCommerce production bindings and offline input validation; no paid calls."""
import importlib.util
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from nexscope_cli import tools
from nexscope_cli.core.errors import Failure

ROUTES = {
    'woocommerce-products': '/woocommerce/products',
    'woocommerce-product-detail': '/woocommerce/productDetail',
    'woocommerce-product-variations': '/woocommerce/productVariations',
    'woocommerce-product-categories': '/woocommerce/productCategories',
    'woocommerce-product-tags': '/woocommerce/productTags',
    'woocommerce-product-brands': '/woocommerce/productBrands',
    'woocommerce-product-attributes': '/woocommerce/productAttributes',
    'woocommerce-product-attribute-detail': '/woocommerce/productAttributeDetail',
    'woocommerce-product-attribute-terms': '/woocommerce/productAttributeTerms',
    'woocommerce-product-reviews': '/woocommerce/productReviews',
    'woocommerce-product-collection-data': '/woocommerce/productCollectionData',
}
HAS_SCHEMA = importlib.util.find_spec('jsonschema') is not None


class WooCommerceTools(unittest.TestCase):
    def test_discovery_and_production_bindings_are_complete(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), \
                patch('nexscope_cli.tools.context', side_effect=AssertionError('Auth forbidden')):
            result = tools.command(SimpleNamespace(tool_action='list', catalog=None, live=False, search='woocommerce'))
            self.assertEqual(result['total'], 576)
            self.assertEqual(result['matched'], 11)
            for slug, route in ROUTES.items():
                detail = tools.command(SimpleNamespace(tool_action='describe', catalog=None, live=False, tool=slug))
                self.assertEqual(detail['tool']['name'], 'nexscope_' + slug.replace('-', '_'))
                self.assertIs(detail['tool']['annotations']['readOnlyHint'], False)
                self.assertEqual(detail['bundledBinding']['publicEndpoint'], route)
                self.assertTrue(detail['bundledBinding']['registeredInProductionDocs'])
                self.assertEqual(detail['bundledBinding']['billing']['creditsPerRequest'], 10)
                self.assertTrue(detail['bundledBinding']['billing']['failedRequestsRefunded'])

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_all_eleven_dry_runs_validate_without_credentials_or_network(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), \
                patch('nexscope_cli.tools.context', side_effect=AssertionError('Auth forbidden')):
            for slug in ROUTES:
                params = ['storeUrl=https://cipherskincare.com']
                if slug in ('woocommerce-product-detail', 'woocommerce-product-variations'):
                    params.append('productId=20183')
                if slug in ('woocommerce-product-attribute-detail', 'woocommerce-product-attribute-terms'):
                    params.append('attributeId=2')
                args = SimpleNamespace(tool_action='call', catalog=None, tool=slug, params=params,
                                       input=None, out=None, dry_run=True, auth_mode='env-api-key', api_base=None)
                with self.subTest(slug=slug):
                    plan = tools.command(args)
                    self.assertEqual(plan['status'], 'PLAN_READY')
                    self.assertEqual(plan['networkCalls'], 0)
                    self.assertTrue(plan['requiresWriteApproval'])

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_missing_store_and_invalid_resource_ids_are_rejected(self):
        for slug in ROUTES:
            tool = tools.selected(tools.catalog()['tools'], slug)
            with self.subTest(slug=slug), self.assertRaises(Failure):
                tools.validate(tool, {})
        for slug, field in [('woocommerce-product-detail', 'productId'),
                            ('woocommerce-product-attribute-detail', 'attributeId')]:
            with self.subTest(slug=slug), self.assertRaises(Failure):
                tools.validate(tools.selected(tools.catalog()['tools'], slug),
                               {'storeUrl':'https://cipherskincare.com', field:'0'})


if __name__ == '__main__':
    unittest.main()
