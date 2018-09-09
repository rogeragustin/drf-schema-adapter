# Quick Start

## Installation

### With pip

`pip install drf-schema-adapter`

### From source

Within the source directory:

`python setup.py install`

## Basic usage

### Auto endpoints

Thanks to `drf_auto_endpoint`, **DRF-schema-adapter** helps you register endpoints as
easily as registering basic admin classes.

In order to register endpoints, you'll have to import `drf_auto_endpoint`'s router as
well as the models you want to register inside your `urls.py`.

```
## urls.py

from drf_auto_endpoint.router import router
from my_app.models import MyModel, OtherModel

router.register(MyModel)
router.register(OtherModel, url='my_custom_url')

urlpatterns = [
    url(r'^api/', include(router.urls)),
]
```

If you don't want to import your models directly in your `urls.py`, you can also take 
advantage of `drf_auto_endpoint`'s auto-discovery capabilities and add your registrations
to an `endpoints.py` file in your app.

```
## urls.py

from drf_auto_endpoint.router import router

urlpatterns = [
    url(r'^api/', include(router.urls)),
]


## my_app/endpoints.py

from drf_auto_endpoint.router import router
from .models import MyModel

router.register(MyModel)
```

For more information on `drf_auto_endpoint`'s router and how to customize endpoints, see
[this section](drf_auto_endpoint/index.md).

### Metadata

**DRF-schema-adapter** also comes with metadata classes and mixins for use with
**[Django REST Framework](http://www.django-rest-framework.org/api-guide/metadata/)**.
These classes and mixins provide extra informations about the api and its fields when
calling the `OPTIONS` method on an endpoint root.

Although these metadata classes and mixin work best with **DRF-schema-adapter**'s
`Endpoint` classes, they are also compatible with regular DRF `(Model)ViewSet` and
`(Model)Serializer`.

To enable this extended metadata, you just have to configure it in your `settings.py`

```
## settings.py

...
REST_FRAMEWORK = {
    ...
    'DEFAULT_METADATA_CLASS': 'drf_auto_endpoint.metadata.AutoMetadata',
}
```

For more information about `drf_auto_endpoint`'s metadata and the available adapters,
see [the metadata section of this documentation](drf_auto_endpoint/metadata.md).

### Exporting serializers definition to frontend models

One of the major burdens when writing applications with a backend and a javascript
frontend is having to re-define, at least part of, your models/serialiers both on the
frontend and backend.

Thanks to **DRF-schema-adapter**'s `export_app`, you can export those definition to your
frontend framework, either "on-the-fly" or as concrete files. in order to do that,
you'll first have to add `export_app` to your `INSTALLED_APPS` as well as your frontend
appalication's root path.
Decpending on your project's directory structure, you may also need to add the
fully-qulified dotted-path to the location of your drf_auto_endpoint router.


```
## settings.py

INSTALLED_APPS = (
    ...
    'export_app',
)
EXPORTER_FRONT_APPLICATION_PATH = '../front/js/src'
EXPORTER_ROUTER_PATH = 'my_app.my_url_file.router'
```

Then, to export models corresponding to an endpoint you can now run:

`./manage.py export <endpoint_base_url>`

ex: `./manage.py export sample/products`

To export those models on-the-fly, you'll need to specify your frontend application
module name instead of its path as well as add a new url to your `urls.py`

```
## settings.py

EXPORTER_FRONT_APPLICATION_NAME: 'my-app'
```

```
## urls.py
...
from export_app import urls as export_urls, settings as export_settings
...

urlpatterns = [
    ...
    url(r'^models/', include(export_urls, namespace=export_settings.URL_NAMESPACE)),
]
```

Depeding on your backend and frontend application setup, you may also need to update
some more parameters. Please, see
[export_app's configuration section](../../export_app/index.md#configuration).

To know more about the configuration of `exporter_app` and the different adapters
available, please see [the export-app's adapters section](../../export_app/index.md#adapters)
