import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Quiz App", layout="centered")

FILES = {
    "APP": "data/question_LTC_APP.csv",
    "TWR": "data/question_LTC_TWR.csv",
    "SUP": "data/question_LTC_SUP.csv",
    "LTCS": "data/question_LTCS.csv",
}

st.title("🧠 LUYỆN TRẮC NGHIỆM VVCR 2026")

# ================== STYLE ==================
st.markdown("""
<style>
.question-box {
    background-color: #ffffff;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
    color: #000;
}
.answer {
    padding: 6px;
    border-radius: 5px;
    margin-bottom: 3px;
}
.correct {
    background-color: #d4edda;
    border: 1px solid #2ecc71;
}
.wrong {
    background-color: #f8d7da;
    border: 1px solid #e74c3c;
}
</style>
""", unsafe_allow_html=True)

# ================== SELECT ==================
col1, col2 = st.columns(2)
with col1:
    quiz_type = st.selectbox("Loại đề", ["APP", "TWR", "SUP"])
with col2:
    mode = st.selectbox("Chế độ", ["Tất cả câu hỏi", "Luyện tập", "Thi thử"])

# ================== CREATE QUIZ ==================
if st.button("🎲 Tạo đề mới"):
    df_main = pd.read_csv(FILES[quiz_type])
    df_ltcs = pd.read_csv(FILES["LTCS"])

    if mode == "Tất cả câu hỏi":
        df_final = pd.concat([df_main, df_ltcs], ignore_index=True)
    else:
        # ===== RANDOM THEO CATEGORY =====
        categories = df_main["category"].dropna().unique()

        if len(categories) > 35:
            selected_categories = random.sample(list(categories), 35)
        else:
            selected_categories = categories

        df_each_cat = pd.concat([
            df_main[df_main["category"] == cat].sample(1)
            for cat in selected_categories
        ])

        remaining = 35 - len(df_each_cat)

        if remaining > 0:
            remaining_pool = df_main.drop(df_each_cat.index)
            df_remaining = remaining_pool.sample(n=min(remaining, len(remaining_pool)))
            df_main_sample = pd.concat([df_each_cat, df_remaining])
        else:
            df_main_sample = df_each_cat

        df_main_sample = df_main_sample.sample(frac=1).reset_index(drop=True)

        df_ltcs_sample = df_ltcs.sample(n=min(15, len(df_ltcs)))

        df_final = pd.concat([df_main_sample, df_ltcs_sample], ignore_index=True)

    df_final.reset_index(drop=True, inplace=True)

    st.session_state["questions"] = df_final
    st.session_state["answers"] = {}
    st.session_state["submitted"] = False

    # reset radio
    for k in list(st.session_state.keys()):
        if k.startswith("q"):
            del st.session_state[k]

# ================== SHOW QUESTIONS ==================
if "questions" in st.session_state:
    st.divider()
    st.subheader(f"📋 {len(st.session_state['questions'])} câu hỏi")

    for i, row in st.session_state["questions"].iterrows():
        st.markdown(
            f"<div class='question-box'><b>Câu {i+1}:</b> {row['question']}</div>",
            unsafe_allow_html=True
        )

        options = {
            "A": row["A"],
            "B": row["B"],
            "C": row["C"],
            "D": row["D"]
        }

        labels = [f"{k}. {v}" for k, v in options.items() if str(v) != "nan"]

        key = f"q{i}"
        disabled = st.session_state.get("submitted", False)

        answer = st.radio("", labels, index=None, key=key, disabled=disabled)

        if answer:
            st.session_state["answers"][i] = answer.split(".")[0]

        if mode == "Luyện tập" and answer:
            if answer[0] == row["correct_answer"]:
                st.success("✅ Đúng")
            else:
                st.error(f"❌ Sai - Đáp án: {row['correct_answer']}")

        st.markdown("---")

    # ================== SUBMIT ==================
    if st.button("📤 Nộp bài"):
        correct = 0
        total = len(st.session_state["questions"])

        for i, row in st.session_state["questions"].iterrows():
            if st.session_state["answers"].get(i) == row["correct_answer"]:
                correct += 1

        percent = round(correct / total * 100, 2)

        st.session_state["submitted"] = True
        st.session_state["score"] = (correct, total, percent)

# ================== RESULT ==================
if st.session_state.get("submitted", False):
    correct, total, percent = st.session_state["score"]

    st.markdown("## 🎯 Kết quả")
    st.info(f"{correct}/{total} ({percent}%)")

    if quiz_type == "SUP":
        passed = correct >= 42
    else:
        passed = correct >= 35

    if passed:
        st.success("🎉 ĐẠT")
    else:
        st.error("❌ CHƯA ĐẠT")

    # ================== REVIEW ==================
    if mode == "Thi thử":
        st.markdown("### 🧩 Xem lại bài làm")

        show_only_wrong = st.checkbox("Chỉ hiện câu sai", value=True)

        for i, row in st.session_state["questions"].iterrows():
            chosen = st.session_state["answers"].get(i)
            correct_ans = row["correct_answer"]

            is_wrong = chosen != correct_ans

            if show_only_wrong and not is_wrong:
                continue

            st.markdown(f"**Câu {i+1}: {row['question']}**")

            for opt in ["A", "B", "C", "D"]:
                text = row[opt]
                if str(text) == "nan":
                    continue

                css = "answer"

                if opt == correct_ans:
                    css += " correct"
                elif opt == chosen:
                    css += " wrong"

                st.markdown(
                    f"<div class='{css}'><b>{opt}.</b> {text}</div>",
                    unsafe_allow_html=True
                )

            st.markdown("---")