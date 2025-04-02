# wsgi.py
import sys
import os

# !!! MUDE ESTE CAMINHO DEPOIS PARA O CAMINHO NO PYTHONANYWHERE !!!
# Exemplo: path = '/home/SeuUsuarioPythonAnywhere/analisador_voz'
path = '/home/joao/personal_projects/brain_dump_app' # <-- Placeholder
if path not in sys.path:
    sys.path.insert(0, path)

# Importa a instância 'app' do seu arquivo principal (app.py)
# A variável DEVE se chamar 'application' para o PythonAnywhere encontrar
from app import app as application