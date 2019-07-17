import yaml
import sys
from easymapping import HaproxyConfigGenerator

if len(sys.argv) != 2:
    print("You need to pass the easyconfig.cfg path")
    exit(1)


with open(sys.argv[1], 'r') as content_file:
    parsed = yaml.load(content_file.read())

cfg = HaproxyConfigGenerator(parsed)
print(cfg.generate())

exit(0)
