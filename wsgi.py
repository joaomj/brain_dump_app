# Importa a instância 'app' do seu arquivo principal (app.py)
# A variável DEVE se chamar 'application' para o PythonAnywhere encontrar
from app import app as application

import sys
import os

# path no PythonAnywhere
path = '/home/joaomj/braindump_app'
if path not in sys.path:
    sys.path.insert(0, path)

# Importa a instância 'app' do seu arquivo principal (app.py)
# A variável DEVE se chamar 'application' para o PythonAnywhere encontrar
from app import app as application