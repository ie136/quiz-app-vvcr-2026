import os
import random
import math
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
QUESTIONS_PER_PAGE = 10

# ================== HELPERS ==================
@st.cache_data(show_spinner=False)
def load_csv_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Không tìm thấy file: {path}")
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(path)
    return df.fillna("")


@st.cache_data(show_spinner=False)
def get_prepared_data(path: str) -> pd.DataFrame:
    df = load_csv_safe(path).copy()

    for col in ["question", "A", "B", "C", "D", "correct_answer", "category"]:
        if col not in df.columns:
            df[col] = ""

    df["question"] = df["question"].astype(str).str.strip()
    df["A"] = df["A"].astype(str).str.strip()
    df["B"] = df["B"].astype(str).str.strip()
    df["C"] = df["C"].astype(str).str.strip()
    df["D"] = df["D"].astype(str).str.strip()
    df["correct_answer"] = df["correct_answer"].astype(str).str.strip().str.upper()
    df["category"] = df["category"].astype(str).str.strip()

    df = df[df["question"] != ""].copy()
    df.loc[df["category"] == "", "category"] = UNCATEGORIZED_LABEL
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)

    return df


def clear_question_keys():
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]


def sample_with_category(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """
    Mỗi category >= 1 câu, sau đó random phần còn lại, không trùng.
    """
    rng = random.Random(seed)
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)

    if len(df) <= n:
        return df.sample(frac=1, random_state=seed).reset_index(drop=True)

    cats = df["category"].unique().tolist()
    rng.shuffle(cats)

    selected_parts = []
    for idx, cat in enumerate(cats):
        g = df[df["category"] == cat]
        if len(g) > 0:
            selected_parts.append(g.sample(n=1, replace=False, random_state=seed + idx + 1))

    selected = pd.concat(selected_parts, ignore_index=True).drop_duplicates(subset=["question"])

    if len(selected) > n:
        return selected.sample(n=n, replace=False, random_state=seed + 999).reset_index(drop=True)

    remain = df[~df["question"].isin(selected["question"])].copy()
    need = n - len(selected)

    if need > 0 and len(remain) > 0:
        extra = remain.sample(n=min(need, len(remain)), replace=False, random_state=seed + 2024)
        selected = pd.concat([selected, extra], ignore_index=True)

    return selected.drop_duplicates(subset=["question"]).reset_index(drop=True)


def build_quiz(quiz_type: str, mode: str, seed: int) -> pd.DataFrame:
    df_main = get_prepared_data(FILES[quiz_type]).copy()
    df_ltcs = get_prepared_data(FILES["LTCS"]).copy()

    if mode == "Tất cả câu hỏi":
        df_final = pd.concat([df_main, df_ltcs], ignore_index=True)
        return df_final.drop_duplicates(subset=["question"]).reset_index(drop=True)

    main_n = min(35, len(df_main))
    ltcs_n = min(15, len(df_ltcs))

    main = sample_with_category(df_main, main_n, seed=seed)
    ltcs = sample_with_category(df_ltcs, ltcs_n, seed=seed + 5000)

    # loại trùng giữa 2 phần
    ltcs = ltcs[~ltcs["question"].isin(main["question"])].reset_index(drop=True)

    # bù LTCS nếu thiếu
    if len(ltcs) < ltcs_n:
        pool = df_ltcs[~df_ltcs["question"].isin(main["question"])].copy()
        pool = pool[~pool["question"].isin(ltcs["question"])].copy()
        need = ltcs_n - len(ltcs)
        if len(pool) > 0:
            extra = pool.sample(n=min(need, len(pool)), replace=False, random_state=seed + 8000)
            ltcs = pd.concat([ltcs, extra], ignore_index=True)
            ltcs = ltcs.drop_duplicates(subset=["question"]).reset_index(drop=True)

    # giữ đúng thứ tự: 35 LTC trước, 15 LTCS sau
    final = pd.concat([main, ltcs], ignore_index=True)
    final = final.drop_duplicates(subset=["question"]).reset_index(drop=True)

    return final.head(min(50, len(final))).reset_index(drop=True)


def get_option_map(row):
    return {
        "A": str(row.get("A", "")).strip(),
        "B": str(row.get("B", "")).strip(),
        "C": str(row.get("C", "")).strip(),
        "D": str(row.get("D", "")).strip(),
    }


def get_option_labels(row):
    opts = get_option_map(row)
    labels = []
    for k, v in opts.items():
        if v != "":
            labels.append(f"{k}. {v}")
    return labels


def render_review_option(opt, text, chosen, correct):
    if opt == correct and opt == chosen:
        bg, border, note = "#d1fadf", "#15803d", "✅ Bạn chọn đúng"
    elif opt == correct:
        bg, border, note = "#dcfce7", "#16a34a", "✅ Đáp án đúng"
    elif opt == chosen:
        bg, border, note = "#fee2e2", "#dc2626", "❌ Bạn đã chọn"
    else:
        bg, border, note = "#ffffff", "#d1d5db", ""

    note_html = f"<div style='margin-top:4px;font-size:13px;font-weight:600;'>{note}</div>" if note else ""

    return f"""
    <div style="
        background:{bg};
        border:2px solid {border};
        padding:10px;
        margin-bottom:6px;
        border-radius:8px;
        color:#111;">
        <b>{opt}. {text}</b>
        {note_html}
    </div>
    """


def get_pass_mark(qt):
    return PASS_RULES.get(qt, 35)


def go_to_page(page_number: int):
    st.session_state["page"] = page_number


# ================== CSS ==================
st.markdown(
    """
    <style>
    .question-box {
        background-color: #2b2b3c;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        color: #f0f0f0;
        font-size: 16px;
        line-height: 1.5;
    }

    div.row-widget.stRadio > div[role='radiogroup'] label {
        display: block;
        white-space: normal !important;
        line-height: 1.5;
    }

    .small-note {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== UI HEADER ==================
st.title("🧠 LUYỆN TRẮC NGHIỆM")

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    quiz_type = st.selectbox("Loại đề", ["APP", "TWR", "SUP"])
with col2:
    mode = st.selectbox("Chế độ", ["Tất cả câu hỏi", "Luyện tập", "Thi thử"])
with col3:
    if st.button("♻️ Refresh data"):
        st.cache_data.clear()
        st.success("Đã refresh dữ liệu!")

# ================== CREATE QUIZ ==================
if st.button("🎲 Tạo đề"):
    clear_question_keys()
    seed = random.randint(1, 99999999)

    try:
        questions = build_quiz(quiz_type, mode, seed)
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        st.stop()

    st.session_state["questions"] = questions
    st.session_state["answers"] = {}
    st.session_state["submitted"] = False
    st.session_state["quiz_type"] = quiz_type
    st.session_state["mode"] = mode
    st.session_state["page"] = 1
    st.session_state["seed"] = seed

# ================== SHOW QUESTIONS ==================
if "questions" in st.session_state:
    df = st.session_state["questions"]
    current_mode = st.session_state.get("mode", mode)
    current_quiz_type = st.session_state.get("quiz_type", quiz_type)

    total_questions = len(df)
    total_answered = len(st.session_state.get("answers", {}))
    total_pages = max(1, math.ceil(total_questions / QUESTIONS_PER_PAGE))

    if "page" not in st.session_state:
        st.session_state["page"] = 1

    current_page = max(1, min(st.session_state["page"], total_pages))
    st.session_state["page"] = current_page

    st.caption(f"Đề {current_quiz_type} | Đã trả lời {total_answered}/{total_questions} câu | Trang {current_page}/{total_pages}")

    start_idx = (current_page - 1) * QUESTIONS_PER_PAGE
    end_idx = min(start_idx + QUESTIONS_PER_PAGE, total_questions)
    page_df = df.iloc[start_idx:end_idx]

    for local_idx, (_, row) in enumerate(page_df.iterrows(), start=start_idx):
        st.markdown(
            f"<div class='question-box'><b>Câu {local_idx+1}:</b> {row['question']}</div>",
            unsafe_allow_html=True
        )

        labels = get_option_labels(row)
        ans = st.radio(
            " ",
            labels,
            index=None,
            key=f"q_{local_idx}",
            label_visibility="collapsed",
            disabled=st.session_state.get("submitted", False)
        )

        if ans:
            st.session_state["answers"][local_idx] = ans.split(".", 1)[0].strip()

        if current_mode != "Thi thử" and ans:
            chosen = ans.split(".", 1)[0].strip()
            if chosen == row["correct_answer"]:
                st.success("✅ Chính xác!")
            else:
                st.error(f"❌ Sai! Đáp án đúng là {row['correct_answer']}")

        st.markdown("---")

    # ================== PAGINATION ==================
    nav1, nav2, nav3 = st.columns([1, 1, 1])

    with nav1:
        if current_page > 1:
            if st.button("⬅️ Trang trước"):
                go_to_page(current_page - 1)
                st.rerun()

    with nav2:
        st.markdown(
            f"<div style='text-align:center; padding-top:8px;'>Trang {current_page}/{total_pages}</div>",
            unsafe_allow_html=True
        )

    with nav3:
        if current_page < total_pages:
            if st.button("➡️ Trang sau"):
                go_to_page(current_page + 1)
                st.rerun()

    # ================== SUBMIT ==================
    if not st.session_state.get("submitted", False):
        if st.button("📤 Nộp bài"):
            st.session_state["submitted"] = True
            st.rerun()

# ================== RESULT ==================
if st.session_state.get("submitted", False):
    df = st.session_state["questions"]
    current_mode = st.session_state.get("mode", mode)
    current_quiz_type = st.session_state.get("quiz_type", quiz_type)

    correct = 0
    for i, row in df.iterrows():
        chosen = st.session_state["answers"].get(i)
        correct_ans = row["correct_answer"]
        if chosen == correct_ans:
            correct += 1

    total = len(df)
    percent = round(correct / max(1, total) * 100, 2)

    st.markdown("## 🎯 Kết quả")
    st.info(f"{correct}/{total} đúng ({percent}%)")

    pass_mark = get_pass_mark(current_quiz_type)
    st.caption(f"Điều kiện đạt: ≥ {pass_mark} câu")

    if correct >= pass_mark:
        st.success("🎉 ĐẠT")
    else:
        st.error("❌ CHƯA ĐẠT")

    if current_mode == "Thi thử":
        st.markdown("---")
        st.markdown("### 🧩 Xem lại bài làm")
        only_wrong = st.checkbox("🔍 Chỉ hiển thị câu sai", value=True)

        for i, row in df.iterrows():
            chosen = st.session_state["answers"].get(i)
            correct_ans = row["correct_answer"]
            is_wrong = (chosen != correct_ans)

            if only_wrong and not is_wrong:
                continue

            st.markdown(f"**Câu {i+1}: {row['question']}**")

            opts = get_option_map(row)
            for k, v in opts.items():
                if v != "":
                    st.markdown(
                        render_review_option(k, v, chosen, correct_ans),
                        unsafe_allow_html=True
                    )

            st.markdown("---")