from jinja2 import Environment, FileSystemLoader


class HaproxyConfigGenerator:
    def __init__(self, mapping):
        self.mapping = mapping

    def generate(self):
        file_loader = FileSystemLoader('templates')
        env = Environment(loader=file_loader)
        template = env.get_template('haproxy.cfg.j2')
        return template.render(data=self.mapping)
