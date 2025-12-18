"""
TERRAF - Streamlit Cloud Version
==================================
Minimal version for cloud deployment with informational message.
"""

import streamlit as st

st.set_page_config(
    page_title="TERRAF - Local Installation Required",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ TERRAF Geospatial Analysis Platform")

st.error("⚠️ This application requires local installation")

st.markdown("""
## 🚀 Run TERRAF Locally

TERRAF is designed to run on your local machine with direct access to geospatial data files and custom processing modules.

### Quick Start:

1. **Clone the repository:**
```bash
git clone https://github.com/terraf360/terraf.git
cd terraf
```

2. **Install dependencies:**
```bash
conda env create -f conda/environment.yml
conda activate terrasf
```

Or with pip:
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
streamlit run app/terraf_app.py
```

### ✨ Features:

- 🛰️ **Landsat 9** multi-spectral analysis
- 🧲 **Magnetometry** data processing
- 📊 Interactive mapping with Folium
- 🎯 Target identification for mineral exploration
- 📥 Data download from multiple sources

### 📌 Why Local?

TERRAF requires:
- Custom Python modules from `src/` directory
- Direct file system access for large raster datasets
- Local processing of geospatial data

### 🔗 Resources:

- **Repository:** [github.com/terraf360/terraf](https://github.com/terraf360/terraf)
- **Documentation:** Check the README.md in the repository
- **Issues:** Report problems on GitHub Issues

---

**Note:** The web version on Streamlit Cloud is intentionally minimal. Please install locally for full functionality.
""")

st.info("💡 **Tip:** Make sure you have at least 4GB of RAM and GDAL properly configured for rasterio support.")
