from sqlalchemy import DateTime

from flask_rest_orm.serialization.serializer import Serializer, DateTimeSerializer


class ModelSerializer(Serializer):
    """
    Serializer for SQLAlchemy Declarative classes
    """

    def __init__(self, declarative_class):
        """
        :param Type[DeclarativeMeta] declarative_class: the declarative class to be serialized
        """
        self._mapper_class = declarative_class
        self._fields = {}
        columns = declarative_class.__mapper__.c
        if self.__class__ is not ModelSerializer:
            # Collect Fields defined in subclasses
            for attr_name in dir(self.__class__):
                if attr_name.startswith('_'):
                    continue
                value = getattr(self, attr_name)
                if isinstance(value, Field):
                    self._fields[attr_name] = value
        # Collect columns not declared in the serializer
        for column in columns.keys():
            field = self._fields.setdefault(column, Field())
            # Set a serializer for fields that can not be serialized by default
            if field.serializer is None and type(columns[column].type) is DateTime:
                field.serializer = DateTimeSerializer()

    def dump(self, model):
        serial = {}
        for attr, field in self._fields.items():
            if field is None:
                serial[attr] = getattr(model, attr)
                continue
            if field.load_only:
                continue
            value = getattr(model, attr) if hasattr(model, attr) else None
            if value is None:
                serialized = None
            elif field.serializer:
                serialized = field.serializer.dump(value)
            else:
                serialized = value
            serial[attr] = serialized
        return serial

    def load(self, serialized, existing_model=None):
        """
        Instancialize a Declarative model from a serialized dict

        :param dict serialized: the serialized object.

        :param None|DeclarativeMeta existing_model: If given, the model will be updated with the serialized data.

        :rtype: DeclarativeMeta
        """
        if existing_model:
            model = existing_model
            # If deserialization must update an existing model, check if primary key is the same
            primary_keys = existing_model.__mapper__.primary_key
            assert len(primary_keys) == 1, "Nested object must have exactly one primary key"
            pk_name = primary_keys[0].key
            assert getattr(existing_model, pk_name) == serialized[pk_name], \
                "Primary key value of serialized nested object is inconsistent"
        else:
            model = self._mapper_class()
        for field_name, value in serialized.items():
            field = self._fields[field_name]
            if field.dump_only:
                continue
            if value is None:
                deserial_value = value
            elif field.serializer:
                if isinstance(field.serializer, ModelSerializer) and existing_model:
                    existing_nested = getattr(existing_model, field_name)
                    deserial_value = field.serializer.load(value, existing_nested)
                else:
                    deserial_value = field.serializer.load(value)
            else:
                deserial_value = value
            setattr(model, field_name, deserial_value)
        return model


class Field(object):
    """
    Configure a ModelSerializer field
    """

    def __init__(self, dump_only=False, load_only=False, serializer=None):
        self.dump_only = dump_only
        self.load_only = load_only
        self.serializer = serializer


class NestedModelField(Field):
    """
    A field to Dump and Update nested models.
    """

    def __init__(self, declarative_class, **kw):
        super().__init__(**kw)
        if self.serializer is None:
            self.serializer = ModelSerializer(declarative_class)


class NestedAttributesField(Field):
    """
    A read-only field that dump nested object attributes.
    """

    class NestedAttrsSerializer(Serializer):

        def __init__(self, attr_list):
            self._attr_list = attr_list

        def dump(self, value):
            if isinstance(value, list):
                serialized = [self._dump_item(item) for item in value]
            else:
                return self._dump_item(value)
            return serialized

        def _dump_item(self, item):
            serialized = {}
            for attr_name in self._attr_list:
                serialized[attr_name] = getattr(item, attr_name)
            return serialized

        def load(self, serialized):
            raise NotImplementedError()


    def __init__(self, attr_list, **kw):
        super().__init__(serializer=self.NestedAttrsSerializer(attr_list), **kw)
        assert 'serializer' not in kw, "NestedAttrsField does not support custom Serializer"