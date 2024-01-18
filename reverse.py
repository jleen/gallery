import os
import sys

prefix = sys.argv[1]
files = [f for f in os.listdir(os.getcwd()) if f.endswith('.jpg')]

#for old, new in zip(files, range(len(files), 0, -1)):
for new, old in enumerate(files, start=1):
    os.rename(old, f'{prefix}{new:02}.jpeg')
