import streamlit as st

st.set_page_config(page_title="TERRAF Test", layout="wide")

st.title("🗺️ TERRAF - Test Minimal")
st.success("✅ La app está funcionando correctamente!")

st.markdown("## Test de Módulos")

# Test imports
try:
    import folium
    st.success("✅ folium importado")
except Exception as e:
    st.error(f"❌ folium: {e}")

try:
    from streamlit_folium import st_folium
    st.success("✅ streamlit_folium importado")
except Exception as e:
    st.error(f"❌ streamlit_folium: {e}")

try:
    import rasterio
    st.success("✅ rasterio importado")
except Exception as e:
    st.error(f"❌ rasterio: {e}")

try:
    from pathlib import Path
    import sys
    src_path = Path(__file__).parent.parent / 'src'
    st.info(f"📂 Ruta src/: {src_path}")
    st.info(f"📂 Existe: {src_path.exists()}")
    if src_path.exists():
        files = list(src_path.glob("*.py"))
        st.info(f"📄 Archivos en src/: {[f.name for f in files]}")
except Exception as e:
    st.error(f"❌ Error verificando src/: {e}")

st.markdown("---")
st.info("Si ves este mensaje, la app básica funciona. El problema está en terraf_app.py")
