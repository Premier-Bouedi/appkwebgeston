import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
const_block_match = re.search(r'(?ms)^APP_NAME = .*?^app_icon = icon_path if os\.path\.exists\(icon_path\) else "🛒"\n', content)
if const_block_match:
    content = content[:const_block_match.start()] + "from config import *\n" + content[const_block_match.end():]

# 2. Init
init_block_match = re.search(r'(?ms)^def _init_session_state.*?_init_session_state\(\)\n', content)
if init_block_match:
    content = content[:init_block_match.start()] + "from src.ui_components import init_session_state\ninit_session_state()\n" + content[init_block_match.end():]

# 3. Processor
proc_block_match = re.search(r'(?ms)^def _upload_fingerprint.*?return out_path\n    except OSError:\n        return None\n\n', content)
if proc_block_match:
    content = content[:proc_block_match.start()] + "import src.processor as proc\n\n" + content[proc_block_match.end():]

# 4. Model
model_block_match = re.search(r'(?ms)^def load_persisted_model.*?return pickle\.load\(f\)\n    except Exception:\n        return None\n\n', content)
if model_block_match:
    new_model_block = """@st.cache_resource(show_spinner=False)
def get_model_engine():
    from src.model_manager import ModelManager
    from config import MODEL_PATH
    return ModelManager(MODEL_PATH)

"""
    content = content[:model_block_match.start()] + new_model_block + content[model_block_match.end():]

# 5. UI Bot
bot_block_match = re.search(r'(?ms)^with bot_col:\n    st\.markdown\("""\n        <style>\n        /\* 1\. Mettre la colonne.*?        for msg in st\.session_state\.get\("shoppy_messages", \[\]\):\n            with st\.chat_message\(msg\["role"\]\):\n                st\.markdown\(msg\["content"\]\)\n', content)
if bot_block_match:
    new_bot_block = """with bot_col:
    from src.ui_components import render_shoppy_bot
    model_engine = get_model_engine()
    render_shoppy_bot(model_engine)
"""
    content = content[:bot_block_match.start()] + new_bot_block + content[bot_block_match.end():]

for func in [
    '_upload_fingerprint', '_read_uploaded_csv_bytes', '_read_csv_from_text',
    '_fetch_url_dataframe', '_load_sqlite_dataframe', '_load_sqlalchemy_dataframe',
    'prepare_ecommerce_dataframe', '_archiver_nettoyage_sur_disque'
]:
    content = re.sub(r'(?<!proc\.)' + func, 'proc.' + func, content)

content = content.replace('model = load_persisted_model()', 'model = get_model_engine()')
content = content.replace('if model is None:', 'if model.model is None:')
content = content.replace('float(model.predict(input_data)[0])', 'model.predict_amount(st.session_state["age_input"], st.session_state["quantite_input"])')

with open('app_new.py', 'w', encoding='utf-8') as f:
    f.write(content)
