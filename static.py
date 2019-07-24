import yaml
import sys
from easymapping import HaproxyConfigGenerator

if len(sys.argv) != 2:
    print("You need to pass the easyconfig.yml path")
    exit(1)


with open(sys.argv[1], 'r') as content_file:
    parsed = yaml.load(content_file.read(), Loader=yaml.FullLoader)

cfg = HaproxyConfigGenerator(parsed)
print(cfg.generate())

exit(0)
