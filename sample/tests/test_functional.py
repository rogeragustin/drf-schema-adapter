from django.test import override_settings, TestCase
from django.core.management import call_command

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import CategoryFactory, ProductFactory, HowItWorksFactory
from .base import EndpointAPITestCase

from ..models import HowItWorks

from urls import router


class ItRendersAPITest(APITestCase):

    def _do_test(self):

        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.options('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get('/api/sample/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.options('/api/sample/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(DRF_AUTO_METADATA_ADAPTER='drf_auto_endpoint.adapters.EmberAdapter')
    def test_ember_adapter(self):
        self._do_test()

    @override_settings(DRF_AUTO_METADATA_ADAPTER='drf_auto_endpoint.adapters.AngularFormlyAdapter')
    def test_formly_adapter(self):
        self._do_test()

    @override_settings(DRF_AUTO_METADATA_ADAPTER='drf_auto_endpoint.adapters.ReactJsonSchemaAdapter')
    def test_jsonschema_adapter(self):
        self._do_test()

    @override_settings(DRF_AUTO_METADATA_ADAPTER='drf_auto_endpoint.adapters.BaseAdapter')
    def test_base_adapter(self):
        self._do_test()


class ItExportsTest(TestCase):

    def _do_test(self):
        call_command('export', all=True, noinput=True)

    @override_settings(EXPORTER_ADAPTER='export_app.adapters.EmberAdapter')
    def test_ember_export(self):
        self._do_test()

    @override_settings(EXPORTER_ADAPTER='export_app.adapters.Angular2Adapter')
    def test_angular2_export(self):
        self._do_test()

    @override_settings(EXPORTER_ADAPTER='export_app.adapters.MetadataAdapter')
    def test_metadata_export(self):
        self._do_test()

    @override_settings(EXPORTER_ADAPTER='export_app.adapters.MetadataES6Adapter')
    def test_metadata_es6_export(self):
        self._do_test()

    @override_settings(EXPORTER_ADAPTER='export_app.adapters.MobxAxiosAdapter')
    def test_mobx_axios_export(self):
        self._do_test()


class CategoryAPITest(EndpointAPITestCase, APITestCase):

    endpoint_url = 'sample/categories'
    model_factory_class = CategoryFactory

    create_requires_login = False
    update_requires_login = False
    delete_requires_login = False


class ProductAPITest(EndpointAPITestCase, APITestCase):

    endpoint_url = 'sample/products'
    model_factory_class = ProductFactory

    create_requires_login = False
    update_requires_login = False
    delete_requires_login = False


class HowItWorksAPITest(EndpointAPITestCase, APITestCase):

    endpoint_url = 'sample/howitworks'
    model_factory_class = HowItWorksFactory

    create_requires_login = False
    update_requires_login = False
    delete_requires_login = False

    def setUp(self):
        super(HowItWorksAPITest, self).setUp()
        self.called = router._endpoints[self.endpoint_url].viewset.called_counter

    def test_list_view(self):
        super(HowItWorksAPITest, self).test_list_view()
        self.assertTrue(self.called < router._endpoints[self.endpoint_url].viewset.called_counter,
                        router._endpoints[self.endpoint_url].viewset.called_counter)

    def test_custom_action(self):
        self.test_model.count = 0
        self.test_model.save()
        response = self.client.post(
            '/api/sample/howitworks/{}/increment/'.format(self.test_model.id),
            {}
        )
        self.assertEqual(response.status_code, 200)

        self.test_model.refresh_from_db()
        self.assertEqual(self.test_model.count, 1)

    def test_bulk_action(self):
        self.test_model.count = 10
        self.test_model.save()

        other_record = HowItWorksFactory(count=23)
        other_record.save()

        record_with_zero = HowItWorks(count=0)
        record_with_zero.save()

        response = self.client.post('/api/sample/howitworks/decrement/', {})
        self.assertEqual(response.status_code, 204)

        for record, expected in ((self.test_model, 9), (other_record, 22), (record_with_zero, 0)):
            record.refresh_from_db()
            self.assertEqual(record.count, expected)

    def test_wizard(self):
        self.test_model.count = 40
        self.test_model.save()

        response = self.client.post(
            '/api/sample/howitworks/{}/add/'.format(self.test_model.id),
            {'amount': 2}
        )
        self.assertEqual(response.status_code, 200)

        self.test_model.refresh_from_db()
        self.assertEqual(self.test_model.count, 42)


class PaginationTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        for i in range(251):
            CategoryFactory().save()
        cls.url = '/api/sample/categories/'

    def get_response_data(self, response):
        import django
        from distutils.version import LooseVersion

        self.assertEqual(200, response.status_code)

        if LooseVersion(django.get_version()) >= LooseVersion('1.9'):
            return response.json()
        return response.data

    def test_default_page_size(self):
        response = self.client.get(self.url, format='json')
        self.assertEqual(len(self.get_response_data(response)['results']), 50)

    def test_custom_page_size(self):
        page_size = 250
        response = self.client.get('{}?page_size={}'.format(self.url, page_size), format='json')
        self.assertEqual(len(self.get_response_data(response)['results']), page_size)
