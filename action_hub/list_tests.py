import os
import sys

root = 'tests'
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.endswith('.py'):
            print(os.path.join(dirpath, f))