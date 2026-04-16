import os
import random
import pandas as pd
import streamlit as st

# ================== SETTINGS ==================
st.set_page_config(page_title="Quiz App", layout="centered")

FILES = {
    "APP": "data/question_LTC_APP.csv",
    "TWR": "data/question_LTC_TWR.csv",
    "SUP": "data/question_LTC_SUP.csv",
    "LTCS": "data/question_LTCS.csv",
}

PASS_RULES = {
    "APP": 35,
    "TWR": 35,
    "SUP": 42,
}

# ================== HELPERS ==================
def load_csv_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        st.error(f"❌ Không tìm thấy file dữ liệu: {path}")
        st.stop()

    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path)

def clear_question_keys():
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]

def build_quiz(selected_quiz_type: str, selected_mode: str) -> pd.DataFrame:
    df_main = load_csv_safe(FILES[selected_quiz_type])
    df_ltcs = load_csv_safe(FILES["LTCS"])

    if selected_mode == "Tất cả câu hỏi":
        df_final = pd.concat([df_main, df_ltcs], ignore_index=True)
    else:
        main_n = min(35, len(df_main))
        ltcs_n = min(15, len(df_ltcs))

        df_main_sample = df_main.sample(
            n=main_n,
            replace=False,
            random_state=random.randint(1, 999999)
        )
        df_ltcs_sample = df_ltcs.sample(
            n=ltcs_n,
            replace=False,
            random_state=random.randint(1, 999999)
        )

        df_final = pd.concat([df_main_sample, df_ltcs_sample], ignore_index=True)

    df_final = df_final.fillna("")
    df_final = df_final.reset_index(drop=True)
    return df_final

def get_pass_mark(quiz_type: str) -> int:
    return PASS_RULES.get(quiz_type, 35)

# ================== UI HEADER ==================
st.title("🧠 LUYỆN TRẮC NGHIỆM ONLINE")
st.markdown(
    """
    <style>
    * { word-wrap: break-word; }

    .stRadio > div {
        flex-direction: column;
        align-items: flex-start;
    }

    div.row-widget.stRadio > div[role='radiogroup'] label {
        display: block;
        white-space: normal !important;
        line-height: 1.5;
    }

    .question-box {
        background-color: #2b2b3c;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        color: #f0f0f0;
        font-size: 17px;
    }

    .review-box {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        color: #111111;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    .review-question {
        color: #111111;
        font-weight: 700;
        margin-bottom: 8px;
        line-height: 1.5;
    }

    .review-your-answer {
        color: #b00020;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .review-correct-answer {
        color: #0f7b0f;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== SELECTION PANEL ==================
col1, col2 = st.columns(2)
with col1:
    quiz_type = st.selectbox("Loại đề", ["APP", "TWR", "SUP"])
with col2:
    mode = st.selectbox("Chế độ", ["Tất cả câu hỏi", "Luyện tập", "Thi thử"])

# ================== CREATE QUIZ ==================
if st.button("🎲 Tạo đề mới"):
    clear_question_keys()

    df_final = build_quiz(quiz_type, mode)

    st.session_state["quiz_type"] = quiz_type
    st.session_state["mode"] = mode
    st.session_state["questions"] = df_final
    st.session_state["answers"] = {}
    st.session_state["submitted"] = False
    st.session_state["wrong_answers"] = []
    st.session_state["score"] = (0, 0, 0)

# ================== DISPLAY QUESTIONS ==================
if "questions" in st.session_state:
    current_mode = st.session_state.get("mode", mode)
    current_quiz_type = st.session_state.get("quiz_type", quiz_type)
    questions_df = st.session_state["questions"]

    st.divider()
    st.subheader(f"📋 {len(questions_df)} câu hỏi | Đề: {current_quiz_type}")

    total_answered = len(st.session_state.get("answers", {}))
    total_questions = len(questions_df)

    if total_questions > 0:
        st.progress(total_answered / total_questions)
        st.caption(f"Đã chọn: {total_answered}/{total_questions} câu")

    disabled_after_submit = st.session_state.get("submitted", False)

    for i, row in questions_df.iterrows():
        st.markdown(
            f"<div class='question-box'><b>Câu {i+1}:</b> {row['question']}</div>",
            unsafe_allow_html=True
        )

        option_map = {
            "A": row.get("A", ""),
            "B": row.get("B", ""),
            "C": row.get("C", ""),
            "D": row.get("D", ""),
        }

        labels = []
        for key, value in option_map.items():
            if str(value).strip() != "":
                labels.append(f"{key}. {value}")

        radio_key = f"q_{i}"
        answer = st.radio(
            " ",
            labels,
            index=None,
            key=radio_key,
            label_visibility="collapsed",
            disabled=disabled_after_submit
        )

        if answer:
            chosen_key = answer.split(".", 1)[0].strip()
            st.session_state["answers"][i] = chosen_key

        if current_mode != "Thi thử" and answer:
            chosen_key = answer.split(".", 1)[0].strip()
            if chosen_key == row["correct_answer"]:
                st.success("✅ Chính xác!")
            else:
                st.error(f"❌ Sai! Đáp án đúng là {row['correct_answer']}")

        st.markdown("---")

    # ================== SUBMIT ==================
    if not st.session_state.get("submitted", False):
        if st.button("📤 Nộp bài"):
            correct = 0
            total = len(questions_df)
            wrong_answers = []

            for i, row in questions_df.iterrows():
                chosen = st.session_state["answers"].get(i)
                correct_ans = row["correct_answer"]

                if chosen == correct_ans:
                    correct += 1
                else:
                    wrong_answers.append({
                        "index": i,
                        "Câu": i + 1,
                        "Câu hỏi": row["question"],
                        "Đáp án của bạn": chosen if chosen else "Không chọn",
                        "Đáp án đúng": correct_ans
                    })

            percent = round(correct / total * 100, 2) if total > 0 else 0
            st.session_state["submitted"] = True
            st.session_state["wrong_answers"] = wrong_answers
            st.session_state["score"] = (correct, total, percent)

# ================== SHOW RESULT ==================
if st.session_state.get("submitted", False):
    current_quiz_type = st.session_state.get("quiz_type", quiz_type)
    current_mode = st.session_state.get("mode", mode)
    pass_mark = get_pass_mark(current_quiz_type)

    correct, total, percent = st.session_state["score"]

    st.markdown("## 🎯 Kết quả")
    st.info(f"**{correct}/{total} câu đúng ({percent}%)**")

    if current_quiz_type == "SUP":
        st.caption(f"Điều kiện đạt đề SUP: từ {pass_mark} câu đúng trở lên")
    else:
        st.caption(f"Điều kiện đạt đề {current_quiz_type}: từ {pass_mark} câu đúng trở lên")

    if correct >= pass_mark:
        st.success("🎉 ĐẠT")
    else:
        st.error("❌ CHƯA ĐẠT")

    # ================== REVIEW FOR MOCK EXAM ==================
    if current_mode == "Thi thử":
        st.markdown("---")
        st.markdown("### 🧩 Xem lại bài làm")

        show_only_wrong = st.checkbox("🔍 Chỉ hiển thị các câu sai", value=True)

        for i, row in st.session_state["questions"].iterrows():
            chosen = st.session_state["answers"].get(i)
            correct_ans = row["correct_answer"]
            is_wrong = (chosen != correct_ans)

            if show_only_wrong and not is_wrong:
                continue

            border_color = "#d93025" if is_wrong else "#188038"
            chosen_text = chosen if chosen else "Không chọn"

            st.markdown(
                f"""
                <div class='review-box' style='border-left: 6px solid {border_color};'>
                    <div class='review-question'>Câu {i+1}: {row['question']}</div>
                    <div class='review-your-answer'>Bạn chọn: {chosen_text}</div>
                    <div class='review-correct-answer'>Đáp án đúng: {correct_ans}</div>
                </div>
                """,
                unsafe_allow_html=True
            )