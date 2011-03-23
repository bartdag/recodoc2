from __future__ import unicode_literals
from django.conf import settings
import os
import shutil

def clean_test_dir():
    basepath = settings.PROJECT_FS_ROOT_TEST
    
    for member in os.listdir(basepath):
        full_path = os.path.join(basepath,member)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
