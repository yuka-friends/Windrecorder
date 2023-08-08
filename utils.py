import os
import shutil
import json


def empty_directory(path):
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)


# 统计文件夹大小
def get_dir_size(dir):
    size = 0
    for root, _, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size


# 更写 config.json
def config_set(name, value):
    with open('config.json') as f:
        config = json.load(f)

    config[name] = value

    with open('config.json', 'w') as f:
        json.dump(config, f)
