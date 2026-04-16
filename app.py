import streamlit as st
import pandas as pd

# ================== CONFIG ==================
st.set_page_config(page_title="Quiz App", layout="centered")

FILES = {
    "APP": "data/question_LTC_APP.csv",
    "TWR": "data/question_LTC_TWR.csv",
    "SUP": "data/question_LTC_SUP.csv",
    "LTCS": "data/question_LTCS.csv",
}

# ================== UI ==================
st.title("🧠 Quiz App VVCR 2026")

quiz_type = st.selectbox("Chọn loại đề", ["APP", "TWR", "SUP"])

# ================== LOAD DATA ==================
try:
    df_main = pd.read_csv(FILES[quiz_type])
    df_ltcs = pd.read_csv(FILES["LTCS"])

    df = pd.concat([df_main, df_ltcs], ignore_index=True)

    st.success(f"✅ Load thành công {len(df)} câu hỏi")

    # Hiển thị preview
    st.subheader("📋 Xem trước dữ liệu")
    st.dataframe(df.head(10))

except Exception as e:
    st.error("❌ Lỗi khi load dữ liệu")
    st.text(str(e))