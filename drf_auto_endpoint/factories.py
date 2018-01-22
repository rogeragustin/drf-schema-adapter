from rest_framework import pagination, serializers
from rest_framework.filters import OrderingFilter, SearchFilter

try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    # Older versions of DRF and django_filters
    from rest_framework.filters import DjangoFilterBackend
from django.core.exceptions import FieldDoesNotExist

try:
    from django.db.models.fields.reverse_related import ManyToOneRel, OneToOneRel
except ImportError:
    # Django 1.8
    from django.db.models.fields.related import ManyToOneRel, OneToOneRel

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import NOT_PROVIDED


# ADDED IMPORT
from rest_framework_recursive.fields import RecursiveField
from drf_writable_nested import WritableNestedModelSerializer
from datetime import datetime



class NullToDefaultMixin(object):

    def __init__(self, *args, **kwargs):
        super(NullToDefaultMixin, self).__init__(*args, **kwargs)
        for field in self.Meta.fields:
            try:
                model_field = self.Meta.model._meta.get_field(field)
                if hasattr(model_field, 'default') and model_field.default != NOT_PROVIDED:
                    self.fields[field].allow_null = True
            except FieldDoesNotExist:
                pass

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
        #TODO que això no exploti en el cas que l'usuari hagi definit un related_name
        # Alt: no es poden definir related_name i sempre s'ha de treballar en automàtic.

        if field.field.related_model != field.field.model:
            return field.field.remote_field.name
        else:
            return "from_"+field.field.remote_field.name

    elif attr == 'related_name':
        if field.rel.related_name is not None:
            # Case where a related_name has specifically being defined.
            return field.rel.related_name

        elif field.field.related_model == field.field.model:
            # Case autogen related_name of a model related to itself
            return field.field.model.__name__.lower()+"_set"
        else:
            # Case autogen related_name of a model related to another model.
            return field.through.__name__.lower()+"_set"

    elif attr == 'through_model':
        return field.through.__name__

    elif attr == 'related_model':
        return field.field.related_model.__name__

    elif attr == 'related_serializer':
        return field.through.__name__+"Serializer"



def related_serializer_factory(endpoint=None, fields=None, base_class=None, model=None, remote_field=None):
    if model is not None:
        assert endpoint is None, "You cannot specify both a model and an endpoint"
        from .endpoints import Endpoint
        endpoint = Endpoint(model=model)
    else:
        assert endpoint is not None, "You have to specify either a model or an endpoint"

    if base_class is None:
        base_class = endpoint.base_serializer

    fields = [
        f.name
        for f in endpoint.model._meta.get_fields()
        if f.name != 'created_at' and f.name != 'updated_at' and f.name != 'id'
           and f.name != remote_field
    ]

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
        if meta_field not in base_class._declared_fields:
            try:
                model_field = endpoint.model._meta.get_field(meta_field)
                if isinstance(model_field, OneToOneRel):
                    cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(read_only=True)
                elif isinstance(model_field, ManyToOneRel):
                    cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
            except FieldDoesNotExist:
                cls_attrs[meta_field] = serializers.ReadOnlyField()
    print(type(cls_name, (NullToDefaultMixin, base_class,), cls_attrs))
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

    print(endpoint.model.__name__)

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
    """
    When constructing a serializer, which envolves a fk, return the __str__(self) set in the model,
    instead of the id. If we detect a children model_field, we will return a tree-shaped serializer.
    """
    """
    for field in meta_attrs['fields']:
        try:
            model_field = endpoint.model._meta.get_field(field)
            if model_field.name == 'children':
                cls_attrs[model_field.name] = RecursiveField(required=False, allow_null=True, many=True)

            elif str(model_field.get_internal_type()) == "ForeignKey":
                cls_attrs[model_field.name] = serializers.StringRelatedField(many=False)
            elif str(model_field.get_internal_type()) == "ManyToManyField":
                cls_attrs[model_field.name] = serializers.StringRelatedField(many=True)
        except FieldDoesNotExist:
            pass
    """
    # Special treatment for particular cases of foreignkey fields.
    # Send neseted recursive field with all the info in the case of a "children" file (typical for categories)
    for f in [f for f in list(filter(lambda x: x!= '__str__', meta_attrs['fields'])) if endpoint.model._meta.get_field(f).name == 'children']:
        try:
            cls_attrs[endpoint.model._meta.get_field(f).name] = RecursiveField(required=False, allow_null=True, many=True)
            print(endpoint.model._meta.get_field(f).name)
        except FieldDoesNotExist:
            pass

    # Special treatment for many to many fields.
    for f in [f for f in endpoint.model._meta.get_fields() if f.many_to_many and not f.auto_created and
              f.name in meta_attrs['fields']]:
        field = eval("endpoint.model.{}".format(f.name))

        try:

            exec ("from endpoint.model._meta.app_label import M2MRelations(field, 'through_model')")
            through_model = eval(M2MRelations(field, 'through_model'))
            print(through_model)
            print(field.field.remote_field.name)
            related_serializer_factory(model=through_model, remote_field = field.field.remote_field.name)

            print (
                "cls_attrs[field.field.name] = {0}(source=M2MRelations(field, 'related_name'), "
                "many=True, required=False, allow_null=True)".format(M2MRelations(field, 'related_serializer'))
            )
            exec(
                "cls_attrs[field.field.name] = {0}(source=M2MRelations(field, 'related_name'), "
                "many=True, required=False, allow_null=True)".format(M2MRelations(field,'related_serializer'))
            )

        except FieldDoesNotExist:
            pass
    """
    INITIAL APPROACH
    ctrl = False
    for field in meta_attrs['fields']:
        try:
            model_field = endpoint.model._meta.get_field(field)
            if model_field.name == 'children' or str(model_field.get_internal_type()) == "ForeignKey" \
                    or str(model_field.get_internal_type()) == "ManyToManyField":
                nested_serializer = True
                serializer_factory(model=model_field.related_model)

                cls_attrs[model_field.name] = '{}Serializer()'.format(model_field.related_model.__name__)
                cls_attrs[model_field.name] = serializers.StringRelatedField(many=False)

        except FieldDoesNotExist:
            pass
    """
    ######
    # END - ADDED CODE
    ######

    for meta_field in meta_attrs['fields']:
        if meta_field not in base_class._declared_fields:
            try:
                model_field = endpoint.model._meta.get_field(meta_field)
                if isinstance(model_field, OneToOneRel):
                    cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(read_only=True)
                elif isinstance(model_field, ManyToOneRel) and model_field.name != "children": # This part of the code has been modified too, as otherwise it was destroying the "children" case.
                    cls_attrs[meta_field] = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
            except FieldDoesNotExist:
                cls_attrs[meta_field] = serializers.ReadOnlyField()



    ##print(cls_name)
    #print(cls_attrs)
    """
    if ctrl == False:
        return type(cls_name, (NullToDefaultMixin, base_class, ), cls_attrs)
    else:
        return type(cls_name, (NullToDefaultMixin, WritableNestedModelSerializer, ), cls_attrs)
    """

    return type(cls_name, (NullToDefaultMixin, base_class,), cls_attrs)


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


def viewset_factory(endpoint):
    from .endpoints import BaseEndpoint

    base_viewset = endpoint.get_base_viewset()

    cls_name = '{}ViewSet'.format(endpoint.model.__name__)
    tmp_cls_attrs = {
        'serializer_class': endpoint.get_serializer(),
        'queryset': endpoint.model.objects.all(),
        'endpoint': endpoint,
        '__doc__': base_viewset.__doc__
    }

    cls_attrs = {
        key: value
        for key, value in tmp_cls_attrs.items() if key == '__doc__' or
        getattr(base_viewset, key, None) is None
    }

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

        if getattr(endpoint, filter_type, None) is not None:
            filter_backends.append(backend)
            cls_attrs[filter_type] = getattr(endpoint, filter_type)

    if hasattr(endpoint, 'filter_class'):
        if DjangoFilterBackend not in filter_backends:
            filter_backends.append(DjangoFilterBackend)
        cls_attrs['filter_class'] = endpoint.filter_class
    elif hasattr(base_viewset, 'filter_class') and DjangoFilterBackend not in filter_backends:
        filter_backends.append(DjangoFilterBackend)

    if len(filter_backends) > 0:
        cls_attrs['filter_backends'] = filter_backends

    if hasattr(endpoint, 'pagination_class'):
        cls_attrs['pagination_class'] = endpoint.pagination_class
    else:
        cls_attrs['pagination_class'] = pagination_factory(endpoint)

    rv = type(cls_name, (endpoint.get_base_viewset(),), cls_attrs)

    black_list = dir(BaseEndpoint)
    for method_name in dir(endpoint):
        if method_name not in black_list:
            method = getattr(endpoint, method_name)
            if getattr(method, 'action_type', None) in ['custom', 'bulk', 'list']:
                setattr(rv, method_name, method)

    return rv
