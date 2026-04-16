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
        st.error(f"❌ Không tìm thấy file: {path}")
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


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # đảm bảo đủ cột
    for col in ["question","A","B","C","D","correct_answer","category"]:
        if col not in df.columns:
            df[col] = ""

    # chuẩn hóa
    df["question"] = df["question"].astype(str).str.strip()
    df["A"] = df["A"].astype(str).str.strip()
    df["B"] = df["B"].astype(str).str.strip()
    df["C"] = df["C"].astype(str).str.strip()
    df["D"] = df["D"].astype(str).str.strip()
    df["correct_answer"] = df["correct_answer"].astype(str).str.strip().str.upper()
    df["category"] = df["category"].astype(str).str.strip()

    # loại câu trống
    df = df[df["question"] != ""].copy()

    # category trống -> 1 category riêng
    df.loc[df["category"] == "", "category"] = UNCATEGORIZED_LABEL

    # bỏ trùng theo câu hỏi
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)
    return df


def sample_with_category(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Mỗi category ≥ 1 câu, sau đó random phần còn lại, không trùng."""
    df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)

    if len(df) <= n:
        return df.sample(frac=1).reset_index(drop=True)

    cats = df["category"].unique().tolist()
    random.shuffle(cats)

    picks = []
    for cat in cats:
        g = df[df["category"] == cat]
        if len(g) > 0:
            picks.append(g.sample(n=1, replace=False))

    selected = pd.concat(picks, ignore_index=True).drop_duplicates(subset=["question"])

    # nếu nhiều hơn n thì cắt
    if len(selected) > n:
        return selected.sample(n=n, replace=False).reset_index(drop=True)

    # bù thêm
    remain = df[~df["question"].isin(selected["question"])].copy()
    need = n - len(selected)
    if need > 0 and len(remain) > 0:
        extra = remain.sample(n=min(need, len(remain)), replace=False)
        selected = pd.concat([selected, extra], ignore_index=True)

    return selected.drop_duplicates(subset=["question"]).reset_index(drop=True)


def build_quiz(quiz_type: str, mode: str) -> pd.DataFrame:
    df_main = prepare_df(load_csv_safe(FILES[quiz_type]))
    df_ltcs = prepare_df(load_csv_safe(FILES["LTCS"]))

    if mode == "Tất cả câu hỏi":
        df_final = pd.concat([df_main, df_ltcs], ignore_index=True)
        return df_final.drop_duplicates(subset=["question"]).reset_index(drop=True)

    # 35 LTC + 15 LTCS (không trộn)
    main_n = min(35, len(df_main))
    ltcs_n = min(15, len(df_ltcs))

    main = sample_with_category(df_main, main_n)
    ltcs = sample_with_category(df_ltcs, ltcs_n)

    # loại trùng giữa 2 phần
    ltcs = ltcs[~ltcs["question"].isin(main["question"])].reset_index(drop=True)

    # bù LTCS nếu thiếu
    if len(ltcs) < ltcs_n:
        pool = df_ltcs[~df_ltcs["question"].isin(main["question"])].copy()
        pool = pool[~pool["question"].isin(ltcs["question"])].copy()
        need = ltcs_n - len(ltcs)
        if len(pool) > 0:
            extra = pool.sample(n=min(need, len(pool)), replace=False)
            ltcs = pd.concat([ltcs, extra], ignore_index=True).drop_duplicates(subset=["question"]).reset_index(drop=True)

    # ghép theo thứ tự: LTC trước, LTCS sau
    final = pd.concat([main, ltcs], ignore_index=True).drop_duplicates(subset=["question"]).reset_index(drop=True)

    # đảm bảo tối đa 50 (nếu dữ liệu đủ)
    return final.head(min(50, len(final))).reset_index(drop=True)


def get_option_map(row):
    return {
        "A": row.get("A", ""),
        "B": row.get("B", ""),
        "C": row.get("C", ""),
        "D": row.get("D", ""),
    }


def get_option_labels(row):
    opts = get_option_map(row)
    labels = []
    for k, v in opts.items():
        if str(v).strip() != "":
            labels.append(f"{k}. {v}")
    return labels


def render_review_option(opt, text, chosen, correct):
    if opt == correct and opt == chosen:
        bg, border = "#d1fadf", "#15803d"  # đúng & đã chọn
    elif opt == correct:
        bg, border = "#dcfce7", "#16a34a"  # đúng
    elif opt == chosen:
        bg, border = "#fee2e2", "#dc2626"  # bạn chọn sai
    else:
        bg, border = "#ffffff", "#d1d5db"  # bình thường

    return f"""
    <div style="
        background:{bg};
        border:2px solid {border};
        padding:10px;
        margin-bottom:6px;
        border-radius:8px;
        color:#111;">
        <b>{opt}. {text}</b>
    </div>
    """

def get_pass_mark(qt):
    return PASS_RULES.get(qt, 35)

# ================== UI ==================
st.title("🧠 LUYỆN TRẮC NGHIỆM")

col1, col2 = st.columns(2)
with col1:
    quiz_type = st.selectbox("Loại đề", ["APP","TWR","SUP"])
with col2:
    mode = st.selectbox("Chế độ", ["Tất cả câu hỏi","Luyện tập","Thi thử"])

if st.button("🎲 Tạo đề"):
    clear_question_keys()
    st.session_state["questions"] = build_quiz(quiz_type, mode)
    st.session_state["answers"] = {}
    st.session_state["submitted"] = False

# ================== SHOW QUESTIONS ==================
if "questions" in st.session_state:
    df = st.session_state["questions"]

    st.progress(len(st.session_state.get("answers", {})) / max(1, len(df)))

    for i, row in df.iterrows():
        st.markdown(f"**Câu {i+1}: {row['question']}**")

        labels = get_option_labels(row)
        ans = st.radio(
            " ",
            labels,
            index=None,
            key=f"q_{i}",
            label_visibility="collapsed",
            disabled=st.session_state.get("submitted", False)
        )

        if ans:
            st.session_state["answers"][i] = ans.split(".",1)[0].strip()

        # feedback ngay trong Luyện tập / Tất cả
        if mode != "Thi thử" and ans:
            chosen = ans.split(".",1)[0].strip()
            if chosen == row["correct_answer"]:
                st.success("✅ Chính xác!")
            else:
                st.error(f"❌ Sai! Đáp án đúng là {row['correct_answer']}")

        st.markdown("---")

    if not st.session_state.get("submitted", False):
        if st.button("📤 Nộp bài"):
            st.session_state["submitted"] = True

# ================== RESULT ==================
if st.session_state.get("submitted", False):
    df = st.session_state["questions"]
    correct = 0

    st.markdown("## 🎯 Kết quả")

    for i, row in df.iterrows():
        chosen = st.session_state["answers"].get(i)
        correct_ans = row["correct_answer"]

        if chosen == correct_ans:
            correct += 1

    total = len(df)
    percent = round(correct / max(1,total) * 100, 2)
    st.info(f"{correct}/{total} đúng ({percent}%)")

    pass_mark = get_pass_mark(quiz_type)
    st.caption(f"Điều kiện đạt: ≥ {pass_mark} câu")
    if correct >= pass_mark:
        st.success("🎉 ĐẠT")
    else:
        st.error("❌ CHƯA ĐẠT")

    # REVIEW chi tiết cho Thi thử
    if mode == "Thi thử":
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
                if str(v).strip() != "":
                    st.markdown(
                        render_review_option(k, v, chosen, correct_ans),
                        unsafe_allow_html=True
                    )

            st.markdown("---")