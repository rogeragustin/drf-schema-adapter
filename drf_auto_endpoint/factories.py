from rest_framework import pagination, serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from django.contrib.postgres.fields import JSONField

try:
    #from django_filters.rest_framework import DjangoFilterBackend
    from config.custom_files.DjangoFilterCustomBackend import DjangoFilterCustomBackend as DjangoFilterBackend
except ImportError:
    # Older versions of DRF and django_filters
    from rest_framework.filters import DjangoFilterBackend
from django.core.exceptions import FieldDoesNotExist

from django_filters import FilterSet

try:
    from django.db.models.fields.reverse_related import ManyToOneRel, OneToOneRel, ManyToManyRel, ForeignObjectRel
except ImportError:
    # Django 1.8
    from django.db.models.fields.related import ManyToOneRel, OneToOneRel, ManyToManyRel

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import NOT_PROVIDED


# ADDED IMPORT
from rest_framework_recursive.fields import RecursiveField
from drf_writable_nested import WritableNestedModelSerializer
from datetime import datetime

from drf_aggregates.renderers import AggregateRenderer
from drf_aggregates.exceptions import AggregateException
from rest_framework.response import Response


class NullToDefaultMixin(object):

    def __init__(self, *args, **kwargs):
        super(NullToDefaultMixin, self).__init__(*args, **kwargs)
        #for field in self.Meta.fields:
        #    try:
        #        model_field = self.Meta.model._meta.get_field(field)
        #        if hasattr(model_field, 'default') and model_field.default != NOT_PROVIDED:
        #            self.fields[field].allow_null = True
                    # TODO S'ha de crear el metode fields en el serpy serilaizer per tal que aixo funcioni.
        #    except FieldDoesNotExist:
        #        pass

    def validate(self, data):
        for field in self.Meta.fields:
            try:
                model_field = self.Meta.model._meta.get_field(field)
                if hasattr(model_field, 'default') and model_field.default != NOT_PROVIDED and \
                        data.get(field, NOT_PROVIDED) is None:
                    data.pop(field)
            except FieldDoesNotExist:
                pass

        return super(NullToDefaultMixin, self).validate(data)

#####################################
### SERIALIZER FACTORY ###
#####################################
from django.db import models
import serpy

class ForeignKeyField(serpy.Field):
   def to_value(self, value):
       if value != None:
           if '__str__' in dir(value):
               return value.__str__()
           else:
               return value.pk
       else:
           return value



def get_serpy_type(model_field_type):
    model_serpy_map = {
        models.AutoField: serpy.IntField(required=False),
        models.BigIntegerField: serpy.IntField(required=False),
        models.BooleanField: serpy.BoolField(required=False),
        models.CharField: serpy.StrField(required=False),
        models.CommaSeparatedIntegerField: serpy.StrField(required=False),
        models.DateField: serpy.StrField(required=False),
        models.DateTimeField: serpy.StrField(required=False),
        models.DecimalField: serpy.FloatField(required=False),
        models.EmailField: serpy.StrField(required=False),
        models.Field: serpy.StrField(required=False),
        models.FileField: serpy.StrField(required=False),
        models.FloatField: serpy.FloatField(required=False),
        models.ImageField: serpy.StrField(required=False),
        models.IntegerField: serpy.IntField(required=False),
        models.NullBooleanField: serpy.StrField(required=False),
        models.PositiveIntegerField: serpy.IntField(required=False),
        models.PositiveSmallIntegerField: serpy.IntField(required=False),
        models.SlugField: serpy.StrField(required=False),
        models.SmallIntegerField: serpy.IntField(required=False),
        models.TextField: serpy.StrField(required=False),
        models.TimeField: serpy.StrField(required=False),
        models.URLField: serpy.StrField(required=False),
        models.GenericIPAddressField: serpy.StrField(required=False),
        models.FilePathField: serpy.StrField(required=False),
        models.ForeignKey: ForeignKeyField(),
        models.fields.reverse_related.ManyToOneRel: ForeignKeyField(),
        models.OneToOneField: ForeignKeyField(),
        models.fields.related.ManyToManyField: ForeignKeyField(),
        JSONField: serpy.StrField(required=False),
    }
    return model_serpy_map[model_field_type]



def M2MRelations(field, attr):
    """
    Given a M2M field and a desired output, return the string containing the result.
    :param field:
    :param attr:
    :return:
    """
    if attr == 'name':
        return field.field.name

    elif attr == 'related_field':
        # TODO que això no exploti en el cas que l'usuari hagi definit un related_name
        # Alt: no es poden definir related_name i sempre s'ha de treballar en automàtic.
        return field.field.remote_field.name

        # if field.field.related_model != field.field.model:
        #    return field.field.remote_field.name
        # else:
        #    #return "from_"+field.field.remote_field.name
        #    return field.field.remote_field.name
        #    #return field.field.remote_field.name

    elif attr == 'related_field_target':
        if field.field.related_model != field.field.model:
            return field.field.related_model.__name__.lower()
        else:
            return "from_"+field.field.related_model.__name__.lower()
            #return field.field.remote_field.name
            #return field.field.remote_field.name

    elif attr == 'related_name':
        if field.field.related_model == field.field.model:
            # Case autogen related_name of a model related to itself
            return eval("field.through.{}.field.remote_field.related_name".format(field.field.remote_field.name))
            # return field.field.model.__name__.lower() + "_set"

        elif field.rel.related_name is not None:
            # Case where a related_name has specifically being defined.
            return field.rel.related_name

        else:
            # Case autogen related_name of a model related to another model.
            return field.through.__name__.lower() + "_set"

    elif attr == 'source':
        if field.field.related_model == field.field.model:
            # Case autogen related_name of a model related to itself
            # return eval("field.through.{}.field.remote_field.related_name".format(field.field.remote_field.name))
            return field.field.model.__name__.lower() + "_set"

        elif field.rel.related_name is not None:
            # Case where a related_name has specifically being defined.
            return field.rel.related_name

        else:
            # Case autogen related_name of a model related to another model.
            return field.through.__name__.lower() + "_set"

    elif attr == 'through_model':
        return field.through.__name__

    elif attr == 'related_model':
        return field.field.related_model.__name__

    elif attr == 'related_serializer':
        return field.through.__name__ + "Serializer"


def create(self, validated_data):
    model = self.Meta.model

    # 1. Take out from the validated_data all the many to many fields information (it should be stored into the
    # intermediate model instance) and store it temporarily in auxiliary variables.
    #for field in [rel]
    for f in [f for f in model._meta.get_fields() if f.many_to_many and not f.auto_created]:
        field = eval("model.{}".format(f.name))

        # Assign relfield_data = None
        exec ("{0}{1} = {2}".format(f.name, "_data", None))  # E.g: ingredients_data = None

        #if validated_data.get(M2MRelations(field, 'related_name'), None) is not None:
        if M2MRelations(field, 'related_name') in validated_data.keys():
            exec (
            "{0}{1} = validated_data.pop('{2}')".format(f.name, "_data", M2MRelations(field, 'related_name')))
            # E.g:
            # if validated_data.get("productingredient_set", None) is not None:
            #    ingredients_data = validated_data.pop('productingredient_set')
        else:
            "{0}{1} = None".format(f.name, "_data")

            # 2. Create an instance of the model with the base validated_data
    model_instance = model.objects.create(**validated_data)
    # E.g: product = Product.objects.create(**validated_data)

    # 3. For each auxiliary variable, fill the corresponding intermediate model with this information.
    for f in [f for f in model._meta.get_fields() if f.many_to_many and not f.auto_created]:
        field = eval("model.{}".format(f.name))

        if vars()[f.name + "_data"] is not None:
            for rel_model_instance in vars()[f.name + "_data"]:
                # Import the submodel before calling it.
                through_model_name = M2MRelations(field, 'through_model')
                app = model._meta.app_label
                exec ("from {0}.models import {1}".format(app, through_model_name))
                exec (
                "{0}.objects.create({1}={2}, **rel_model_instance)".format(through_model_name,
                                                                           M2MRelations(field, 'related_field'),
                                                                           'model_instance'))
                # E.g:
                # if ingredients_data is not None:
                #    for ingredient in ingredients_data:
                #        ProductIngredient.objects.create(product=product, **ingredient)
                #        # la comanda **ingredient el que fa es, donat un diccionari, treure-li els corxets i
                #        # transformar els : en =.

    return model_instance


def update(self, instance, validated_data):
    model = self.Meta.model

    # 1. Pop data from validated.
    for f in [f for f in model._meta.get_fields() if f.many_to_many and not f.auto_created]:
        field = eval("model.{}".format(f.name))

        # Assign relfield_data = None
        exec ("{0}{1} = {2}".format(f.name, "_data", None))  # E.g: ingredients_data = None

        #if validated_data.get(M2MRelations(field, 'related_name'), None) is not None:
        if M2MRelations(field, 'related_name') in validated_data.keys():
            exec (
                "{0}{1} = validated_data.pop('{2}')".format(f.name, "_data", M2MRelations(field, 'related_name')))
        else:
            "{0}{1} = None".format(f.name, "_data")

    for item in validated_data:
        if model._meta.get_field(item):
            setattr(instance, item, validated_data[item])

    # 2. Load previous data and either update it with the new one. In case no data existed, create a new record.
    for f in [f for f in model._meta.get_fields() if f.many_to_many and not f.auto_created]:
        field = eval("model.{}".format(f.name))

        # Delete subinstances that are not present anymore
        through_model_name = M2MRelations(field, 'through_model')
        app = model._meta.app_label
        exec ("from {0}.models import {1}".format(app, through_model_name))
        field_queryset = eval("{0}.objects.filter({1}=instance)".format(M2MRelations(field, 'through_model'),
                                                                        M2MRelations(field, 'related_field')))
        field_validated_data_ids = [getattr(k['instance'], 'id') for k in
                                        eval(f.name + "_data") if 'instance' in k.keys()]

        for i in field_queryset:
            i_id = getattr(i, 'id')

            if i_id not in field_validated_data_ids:
                exec (
                    "{0}.objects.filter(id={1}).delete()".format(
                        M2MRelations(field, 'through_model'),
                        i_id
                    )
                )

        # Set new content for intermediary model
        if eval(f.name + "_data") is not None:
            for rel_model_instance in eval(f.name + "_data"):
                related_instance = rel_model_instance.pop('instance') if 'instance' in rel_model_instance.keys() else None
                if related_instance:
                    field_instance = eval("{0}.objects.filter(id={1})".format(
                        M2MRelations(field, 'through_model'),
                        related_instance.id)
                    )
                    field_instance.update(id=related_instance.id, updated_at=datetime.now(), **rel_model_instance)
                else:
                    exec ("{0}.objects.create({1}={2}, **rel_model_instance)".format(
                        M2MRelations(field, 'through_model'),
                        M2MRelations(field, 'related_field'),
                        'instance'))

    instance.save()
    return instance


def to_internal_value(self, data):
    """
    Dict of native values <- Dict of primitive datatypes.
    Add instance key to values if `id` present in primitive dict
    :param data:
    """
    obj = super(self.__class__, self).to_internal_value(data)
    instance_id = data.get('id', None)
    if instance_id:
        obj['instance'] = self.Meta.model.objects.get(id=instance_id)
    return obj


def related_serializer_factory(endpoint=None, fields=None, base_class=None, model=None):
    if model is not None:
        assert endpoint is None, "You cannot specify both a model and an endpoint"
        from .endpoints import Endpoint
        endpoint = Endpoint(model=model)
    else:
        assert endpoint is not None, "You have to specify either a model or an endpoint"

    if base_class is None:
        base_class = endpoint.base_serializer

    meta_attrs = {
        'model': endpoint.model,
        'fields': fields if fields is not None else endpoint.get_fields_for_serializer()
    }

    meta_parents = (object, )
    if hasattr(base_class, 'Meta'):
        meta_parents = (base_class.Meta, ) + meta_parents


    Meta = type('Meta', meta_parents, meta_attrs)

    cls_name = '{}Serializer'.format(endpoint.model.__name__)
    cls_attrs = {
        'Meta': Meta,
    }

    for meta_field in meta_attrs['fields']:
        #if meta_field not in base_class._declared_fields:
        try:
            model_field = endpoint.model._meta.get_field(meta_field)
            if isinstance(model_field, OneToOneRel):
                cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(read_only=True)
            elif isinstance(model_field, ManyToOneRel):
                cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
        except FieldDoesNotExist:
            cls_attrs[meta_field] = serializers.ReadOnlyField()

    cls_attrs['to_internal_value'] = to_internal_value

    return type(cls_name, (NullToDefaultMixin, base_class,), cls_attrs)



def serializer_factory(endpoint=None, fields=None, base_class=None, model=None):
    if model is not None:
        assert endpoint is None, "You cannot specify both a model and an endpoint"
        from .endpoints import Endpoint
        endpoint = Endpoint(model=model)
    else:
        assert endpoint is not None, "You have to specify either a model or an endpoint"

    if base_class is None:
        base_class = endpoint.base_serializer

    meta_attrs = {
        'model': endpoint.model,
        'fields': fields if fields is not None else endpoint.get_fields_for_serializer()
    }
    meta_parents = (object, )
    if hasattr(base_class, 'Meta'):
        meta_parents = (base_class.Meta, ) + meta_parents

    Meta = type('Meta', meta_parents, meta_attrs)
    cls_name = '{}Serializer'.format(endpoint.model.__name__)
    cls_attrs = {
        'Meta': Meta,
    }

    ######
    # BEGINNING - ADDED CODE
    ######
    # Special treatment for particular cases of foreignkey fields.
    # Send neseted recursive field with all the info in the case of a "children" file (typical for categories)

    for f in [f for f in list(filter(lambda x: x!= '__str__', meta_attrs['fields'])) if endpoint.model._meta.get_field(f).name == 'children']:
        try:
            cls_attrs[endpoint.model._meta.get_field(f).name] = RecursiveField(required=False, allow_null=True, many=True)
        except FieldDoesNotExist:
            pass

    # Special treatment for many to many fields.
    for f in [f for f in endpoint.model._meta.get_fields() if f.many_to_many and not f.auto_created and
              f.name in meta_attrs['fields']]:
        field = eval("endpoint.model.{}".format(f.name))

        try:
            through_model_name = M2MRelations(field, 'through_model')
            if '_' not in through_model_name:
                app = endpoint.model._meta.app_label
                exec("from {0}.models import {1}".format(app,through_model_name))
                through_model = eval(through_model_name)
                through_fields = [
                    f.name
                    for f in through_model._meta.get_fields()
                    if f.name != 'created_at' and f.name != 'updated_at' #and f.name != 'id'
                       and f.name != M2MRelations(field,'related_field')
                ]
                through_fields.append('__str__')
                SubSerializer = related_serializer_factory(model=through_model, fields = through_fields)

                cls_attrs[field.field.name] = SubSerializer(source=M2MRelations(field, 'related_name'), many=True, required=False, allow_null=True)

                cls_attrs["create"] = create
                cls_attrs["update"] = update

        except FieldDoesNotExist:
            pass

    ######
    # END - ADDED CODE
    ######
    for meta_field in meta_attrs['fields']:
        # if meta_field not in base_class._declared_fields:
        try:
            model_field = endpoint.model._meta.get_field(meta_field)
            if isinstance(model_field, OneToOneRel):
                cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(read_only=True)
            elif isinstance(model_field, ManyToOneRel) and model_field.name != "children": # This part of the code has been modified too, as otherwise it was destroying the "children" case.
                cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
            elif isinstance(model_field, ManyToManyRel):
                # related ManyToMany should not be required
                cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(
                    many=True,
                    required=False,
                    queryset=model_field.related_model.objects.all()
                )
            elif (model_field.__class__.__name__ == 'ForeignKey') \
                    and (endpoint.base_serializer.__name__ != 'ModelSerializer'):
                # For serpy models (fast read), we automatize the StringRelated pattern
                # For normal drf (used when both read/write is required) we don't use it.
                cls_attrs[meta_field] = serializers.StringRelatedField()

            if endpoint.base_serializer.__name__ != 'ModelSerializer':
                cls_attrs[meta_field] = get_serpy_type(model_field.__class__)

        except FieldDoesNotExist:
            cls_attrs[meta_field] = serializers.ReadOnlyField()
    try:
        return type(cls_name, (NullToDefaultMixin, base_class, ), cls_attrs)
    except TypeError:
        # MRO issue, let's try the other way around
        return type(cls_name, (base_class, NullToDefaultMixin, ), cls_attrs)



#####################################
### PAGINATION FACTORY ###
#####################################
def pagination_factory(endpoint):
    pg_cls_name = '{}Pagination'.format(endpoint.model.__name__)

    page_size = getattr(endpoint, 'page_size', None)
    pg_cls_attrs = {
        'page_size': page_size if page_size is not None else settings.REST_FRAMEWORK.get('PAGE_SIZE', 50),
    }

    if hasattr(endpoint, 'pagination_template'):
        pg_cls_attrs['template'] = endpoint.pagination_template

    BasePagination = getattr(endpoint, 'base_pagination_class', pagination.PageNumberPagination)
    if issubclass(BasePagination, pagination.PageNumberPagination):
        pg_cls_attrs['page_size_query_param'] = getattr(endpoint, 'page_size_query_param', 'page_size')
        for param in ('django_paginator_class', 'page_query_param', 'max_page_size', 'last_page_string',
                      'page_size'):
            if getattr(endpoint, param, None) is not None:
                pg_cls_attrs[param] = getattr(endpoint, param)
    elif issubclass(BasePagination, pagination.LimitOffsetPagination):
        pg_cls_attrs.pop('page_size')
        for param in ('default_limit', 'limit_query_param', 'offset_query_param', 'max_limit'):
            if getattr(endpoint, param, None) is not None:
                pg_cls_attrs[param] = getattr(endpoint, param)
    elif issubclass(BasePagination, pagination.CursorPagination):
        for param in ('page_size', 'cursor_query_param', 'ordering'):
            if getattr(endpoint, param, None) is not None:
                pg_cls_attrs[param] = getattr(endpoint, param)
    else:
        raise ImproperlyConfigured('base_pagination_class needs to be a subclass of one of the following:'
                                   'PageNumberPagination, LimitOffsetPagination, CursorPagination')

    return type(pg_cls_name, (BasePagination, ), pg_cls_attrs)


def filter_factory(endpoint):

    base_class = endpoint.base_filter_class

    cls_name = '{}FilterSet'.format(endpoint.model.__name__)

    meta_attrs = {
        'model': endpoint.model,
        'fields': [field if not isinstance(field, dict) else field.get('key', field['name'])
                   for field in endpoint.filter_fields]
    }

    meta_parents = (object, )
    if hasattr(base_class, 'Meta'):
        meta_parents = (base_class.Meta, ) + meta_parents

    Meta = type('Meta', meta_parents, meta_attrs)

    cls_attrs = {
        'Meta': Meta,
    }

    return type(cls_name, (base_class, ), cls_attrs)


#####################################
### VIEWSET FACTORY ###
#####################################
def list_method(self, request, *args, **kwargs):
    renderer = request.accepted_renderer
    if isinstance(renderer, AggregateRenderer):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            data = request.accepted_renderer.render({
                'queryset': queryset, 'request': request
            })
        except AggregateException as e:
            # Raise other types of aggregate errors
            return Response(str(e), status=400)
        return Response(data, content_type=f'application/json')
    return super(self.__class__, self).list(request, *args, **kwargs)
    #return super().list(request, *args, **kwargs)

def viewset_factory(endpoint):
    from .endpoints import BaseEndpoint

    base_viewset = endpoint.get_base_viewset()
    cls_name = '{}ViewSet'.format(endpoint.model.__name__)
    tmp_cls_attrs = {
        'serializer_class': endpoint.get_serializer(),
        # 'serializer_class': serializer_class,
        'queryset': endpoint.queryset if getattr(endpoint, 'queryset', None) is not None \
            else endpoint.model.objects.all(),
        'endpoint': endpoint,
        '__doc__': base_viewset.__doc__
    }

    cls_attrs = {
        key: value
        for key, value in tmp_cls_attrs.items() if key == '__doc__' or
        getattr(base_viewset, key, None) is None
    }

    if 'filter_class' in cls_attrs or 'base_filter_class' in cls_attrs:
        cls_attrs.pop('filter_fields', None)

    if endpoint.permission_classes is not None:
        cls_attrs['permission_classes'] = endpoint.permission_classes

    filter_backends = getattr(endpoint.get_base_viewset(), 'filter_backends', ())
    if filter_backends is None:
        filter_backends = []
    else:
        filter_backends = list(filter_backends)

    for filter_type, backend in (
        ('filter_fields', DjangoFilterBackend),
        ('search_fields', SearchFilter),
        ('ordering_fields', OrderingFilter),
    ):
        if hasattr(endpoint, 'get_{}'.format(filter_type)):
            method = getattr(endpoint, 'get_{}'.format(filter_type))
            try:
                val = method(check_viewset_if_none=False)
            except TypeError:
                val = method(request=None, check_viewset_if_none=False)

        else:
            val = []
        if val is not None and val != []:
            filter_backends.append(backend)

            if filter_type == 'filter_fields':
                cls_attrs['filter_fields'] = [field['name'] if isinstance(field, dict) else field
                                              for field in val]
            elif filter_type == 'ordering_fields':
                cls_attrs['ordering_fields'] = [field['filter'] if isinstance(field, dict) else field
                                                for field in val]
            else:
                cls_attrs[filter_type] = getattr(endpoint, filter_type)

    if hasattr(endpoint, 'filter_class'):
        cls_attrs['filter_class'] = endpoint.filter_class
    elif hasattr(endpoint, 'base_filter_class'):
        cls_attrs['filter_class'] = filter_factory(endpoint)

    if DjangoFilterBackend not in filter_backends and (hasattr(endpoint, 'filter_class') or
                                                       hasattr(base_viewset, 'filter_class') or
                                                       hasattr(endpoint, 'base_filter_class')):
        filter_backends.append(DjangoFilterBackend)

    if len(filter_backends) > 0:
        cls_attrs['filter_backends'] = filter_backends

    if hasattr(endpoint, 'pagination_class'):
        cls_attrs['pagination_class'] = endpoint.pagination_class
    else:
        cls_attrs['pagination_class'] = pagination_factory(endpoint)

    cls_attrs['list'] = list_method

    rv = type(cls_name, (endpoint.get_base_viewset(),), cls_attrs)

    black_list = dir(BaseEndpoint)
    for method_name in dir(endpoint):
        if method_name not in black_list:
            method = getattr(endpoint, method_name)
            if getattr(method, 'action_type', None) in ['custom', 'bulk', 'list']:
                setattr(rv, method_name, method)

    return rv
