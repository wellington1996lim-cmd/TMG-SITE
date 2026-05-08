# TMG-SITE

Aplicativo Streamlit do sistema TMG para upload, visualização, marcação de grids e análises de ortomosaicos.

## Deploy no Streamlit Cloud

1. Conecte este repositório no Streamlit Community Cloud.
2. Use a branch `main`.
3. Use `streamlit_app.py` como arquivo principal.
4. O arquivo `requirements.txt` instala as dependências Python.
5. O arquivo `.streamlit/config.toml` aumenta o limite de upload para mosaicos grandes.

## Banco de dados do app

Por padrão, o app usa a pasta `tmg_data` dentro do ambiente do Streamlit. Em ambiente cloud, esse armazenamento é temporário: uploads e mosaicos importados ficam disponíveis durante a execução do app, mas podem ser perdidos se o app for reiniciado ou reconstruído.

Para usar outro caminho em ambiente próprio, configure a variável ou secret `TMG_DATABASE_DIR`.
