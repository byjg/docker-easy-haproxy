import json

from functions import logger_easyhaproxy


class DockerLabelHandler:
    def __init__(self, label):
        self.__data = None
        self.__label_base = label

    def get_lookup_label(self):
        return self.__label_base

    def create(self, key):
        if isinstance(key, str):
            return f"{self.__label_base}.{key}"

        return "{}.{}".format(self.__label_base, ".".join(key))

    def get(self, label, default_value=""):
        if self.has_label(label):
            return self.__data[label]
        return default_value

    def get_bool(self, label, default_value=False):
        if self.has_label(label):
            return self.__data[label].lower() in ["true", "1", "yes"]
        return default_value

    def get_json(self, label, default_value=None):
        if default_value is None:
            default_value = {}
        if self.has_label(label):
            value = self.__data[label]
            if not value:  # Handle empty strings
                return default_value
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger_easyhaproxy.error(
                    f"Invalid JSON in label '{label}': {value}. Error: {e}. Using default value."
                )
                return default_value
        return default_value

    def set_data(self, data):
        self.__data = data

    def has_label(self, label):
        if label in self.__data:
            return True
        return False