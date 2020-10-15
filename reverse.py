import os

files = [f for f in os.listdir(os.getcwd()) if f.endswith('.jpg')]

for old, new in zip(files, range(len(files), 0, -1)):
    os.rename(old, f'Maine-2020-{new:02}.jpg')
