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

UNCATEGORIZED_LABEL = "Không phân loại"

# ================== HELPERS ==================
def load_csv_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        st.error(f"❌ Không tìm thấy file dữ liệu: {path}")
        st.stop()

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(path)

    return df.fillna("")


def clear_question_keys():
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]


def prepare_df(df: pd.DataFrame, default_type: str = "") -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    required_cols = ["question", "A", "B", "C", "D", "correct_answer", "category", "type"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    df["question"] = df["question"].astype(str).str.strip()
    df["A"] = df["A"].astype(str).str.strip()
    df["B"] = df["B"].astype(str).str.strip()
    df["C"] = df["C"].astype(str).str.strip()
    df["D"] = df["D"].astype(str).str.strip()
    df["correct_answer"] = df["correct_answer"].astype(str).str.strip().str.upper()
    df["category"] = df["category"].astype(str).str.strip()
    df["type"] = df["type"].astype(str).str.strip()

    if default_type:
        df.loc[df["type"] == "", "type"] = default_type

    # bỏ câu trống
    df = df[df["question"] != ""].copy()

    # category trống -> gom thành 1 category riêng
    df.loc[df["category"] == "", "category"] = UNCATEGORIZED_LABEL

    # bỏ trùng theo câu hỏi
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)

    return df


def sample_unique_with_category(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Quy tắc:
    - Không trùng câu trong cùng 1 lần lấy mẫu
    - Mỗi category có ít nhất 1 câu
    - Category trống đã được chuẩn hóa thành 'Không phân loại'
    - Sau đó random các câu còn lại
    """
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)

    if len(df) == 0:
        return df

    if len(df) <= n:
        return df.sample(frac=1).reset_index(drop=True)

    categories = df["category"].dropna().astype(str).str.strip().unique().tolist()
    random.shuffle(categories)

    selected_parts = []

    # Lấy 1 câu cho mỗi category
    first_round = []
    for cat in categories:
        group = df[df["category"] == cat]
        if len(group) > 0:
            first_round.append(group.sample(n=1, replace=False))

    if first_round:
        first_pick = pd.concat(first_round, ignore_index=True)
        first_pick = first_pick.drop_duplicates(subset=["question"]).reset_index(drop=True)

        # Nếu số category > n thì cắt ngẫu nhiên về n
        if len(first_pick) > n:
            first_pick = first_pick.sample(n=n, replace=False).reset_index(drop=True)

        selected_parts.append(first_pick)

    selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame(columns=df.columns)
    selected = selected.drop_duplicates(subset=["question"]).reset_index(drop=True)

    remaining_need = n - len(selected)

    if remaining_need > 0:
        remaining_pool = df[~df["question"].isin(selected["question"])].copy()

        if len(remaining_pool) > 0:
            extra = remaining_pool.sample(
                n=min(remaining_need, len(remaining_pool)),
                replace=False
            )
            selected = pd.concat([selected, extra], ignore_index=True)

    selected = selected.drop_duplicates(subset=["question"]).sample(frac=1).reset_index(drop=True)

    return selected.head(min(n, len(selected))).reset_index(drop=True)


def build_quiz(selected_quiz_type: str, selected_mode: str) -> pd.DataFrame:
    df_main = prepare_df(load_csv_safe(FILES[selected_quiz_type]), default_type=f"LTC_{selected_quiz_type}")
    df_ltcs = prepare_df(load_csv_safe(FILES["LTCS"]), default_type="LTC_LTCS")

    if selected_mode == "Tất cả câu hỏi":
        df_final = pd.concat([df_main, df_ltcs], ignore_index=True)
        df_final = df_final.drop_duplicates(subset=["question"]).reset_index(drop=True)
        return df_final

    # Luyện tập / Thi thử = 50 câu
    main_n = min(35, len(df_main))
    ltcs_n = min(15, len(df_ltcs))

    df_main_sample = sample_unique_with_category(df_main, main_n)
    df_ltcs_sample = sample_unique_with_category(df_ltcs, ltcs_n)

    # Ghép lại và chống trùng lần cuối
    df_final = pd.concat([df_main_sample, df_ltcs_sample], ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["question"]).reset_index(drop=True)

    # Nếu sau khi ghép mà bị thiếu do trùng giữa MAIN và LTCS, bù thêm từ pool còn thiếu
    target_total = min(50, len(pd.concat([df_main, df_ltcs], ignore_index=True).drop_duplicates(subset=["question"])))
    current_total = len(df_final)

    if current_total < target_total:
        combined_pool = pd.concat([df_main, df_ltcs], ignore_index=True)
        combined_pool = combined_pool.drop_duplicates(subset=["question"]).reset_index(drop=True)

        missing_pool = combined_pool[~combined_pool["question"].isin(df_final["question"])].copy()
        need_more = target_total - current_total

        if len(missing_pool) > 0:
            extra = missing_pool.sample(n=min(need_more, len(missing_pool)), replace=False)
            df_final = pd.concat([df_final, extra], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=["question"]).reset_index(drop=True)

    df_final = df_final.sample(frac=1).reset_index(drop=True)
    return df_final


def get_pass_mark(quiz_type: str) -> int:
    return PASS_RULES.get(quiz_type, 35)


def get_option_map(row):
    return {
        "A": str(row.get("A", "")).strip(),
        "B": str(row.get("B", "")).strip(),
        "C": str(row.get("C", "")).strip(),
        "D": str(row.get("D", "")).strip(),
    }


def get_option_labels(row):
    option_map = get_option_map(row)
    labels = []
    for key, value in option_map.items():
        if value != "":
            labels.append(f"{key}. {value}")
    return labels


def render_review_option(opt_key: str, opt_text: str, chosen: str, correct: str) -> str:
    label = f"{opt_key}. {opt_text}"

    is_chosen = (chosen == opt_key)
    is_correct = (correct == opt_key)

    if is_correct and is_chosen:
        bg = "#d1fadf"
        border = "#15803d"
        note = "✅ Bạn chọn đúng"
    elif is_correct:
        bg = "#dcfce7"
        border = "#16a34a"
        note = "✅ Đáp án đúng"
    elif is_chosen:
        bg = "#fee2e2"
        border = "#dc2626"
        note = "❌ Bạn đã chọn"
    else:
        bg = "#ffffff"
        border = "#d1d5db"
        note = ""

    note_html = f"<div style='margin-top:4px;font-size:14px;font-weight:600;'>{note}</div>" if note else ""

    return f"""
    <div style="
        background:{bg};
        border:2px solid {border};
        border-radius:10px;
        padding:10px 12px;
        margin-bottom:8px;
        color:#111111;
        line-height:1.5;">
        <div style="font-weight:600;">{label}</div>
        {note_html}
    </div>
    """

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
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
        color: #111111;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }

    .review-question {
        color: #111111;
        font-weight: 700;
        margin-bottom: 10px;
        line-height: 1.6;
        font-size: 16px;
    }

    .review-meta {
        color: #374151;
        font-size: 14px;
        margin-bottom: 10px;
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

        labels = get_option_labels(row)

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
                correct_ans = str(row["correct_answer"]).strip().upper()

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
            correct_ans = str(row["correct_answer"]).strip().upper()
            is_wrong = (chosen != correct_ans)

            if show_only_wrong and not is_wrong:
                continue

            border_color = "#dc2626" if is_wrong else "#16a34a"
            chosen_text = chosen if chosen else "Không chọn"

            st.markdown(
                f"""
                <div class='review-box' style='border-left: 6px solid {border_color};'>
                    <div class='review-question'>Câu {i+1}: {row['question']}</div>
                    <div class='review-meta'>
                        <b>Bạn chọn:</b> {chosen_text} &nbsp; | &nbsp;
                        <b>Đáp án đúng:</b> {correct_ans}
                    </div>
                """,
                unsafe_allow_html=True
            )

            option_map = get_option_map(row)
            for opt_key, opt_text in option_map.items():
                if opt_text != "":
                    st.markdown(
                        render_review_option(opt_key, opt_text, chosen, correct_ans),
                        unsafe_allow_html=True
                    )

            st.markdown("</div>", unsafe_allow_html=True)