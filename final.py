import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import matplotlib.font_manager as fm
import os
import sqlite3

# -------------------------------
# 初期設定
API_KEY = "YOUR_API_KEY"  # 🔑 ご自身のGemini APIキーを設定してください
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"

st.set_page_config(page_title="学習進捗トラッカー", layout="wide")
st.title("📘 個別学習プランナー")

# 日本語フォント指定（macやWindows環境に合わせて変更可）
if os.name == "nt":
    plt.rcParams['font.family'] = 'Yu Gothic'
else:
    plt.rcParams['font.family'] = 'IPAexGothic'

# -------------------------------
# SQLiteデータベースの初期化
def init_db():
    conn = sqlite3.connect("learning_log.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            subject TEXT,
            topic TEXT,
            score INTEGER
        )
    """)
    conn.commit()
    conn.close()

# データをデータベースに保存
def save_data_to_db(date, subject, topic, score):
    conn = sqlite3.connect("learning_log.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO learning_log (date, subject, topic, score) VALUES (?, ?, ?, ?)",
                   (date, subject, topic, score))
    conn.commit()
    conn.close()

# データベースからデータを読み込む
def load_data_from_db():
    conn = sqlite3.connect("learning_log.db")
    df = pd.read_sql_query("SELECT * FROM learning_log", conn)
    conn.close()
    
    # 列名を修正（必要に応じて変更）
    df.rename(columns={"subject": "科目", "score": "理解度"}, inplace=True)
    return df

# -------------------------------
# データ状態管理
init_db()
if 'df' not in st.session_state:
    st.session_state.df = load_data_from_db()

# -------------------------------
# ユーザー入力セクション
def input_section():
    with st.form("学習記録"):
        st.subheader("📌 学習記録を追加")
        date = st.date_input("日付")
        subject = st.selectbox("科目", ["国語", "数学", "英語", "社会", "理科"])
        topic = st.text_input("内容")
        score = st.slider("理解度 (1〜5)", min_value=1, max_value=5)
        submitted = st.form_submit_button("記録を追加")

    if submitted:
        save_data_to_db(date, subject, topic, score)
        st.session_state.df = load_data_from_db()
        st.success("✅ 記録を追加しました！")

# -------------------------------
# 理解度グラフ表示
def show_progress_chart(df):
    st.subheader("📊 科目別 理解度グラフ")
    if df.empty:
        st.info("まだ学習記録がありません。")
        return None

    avg_scores = df.groupby("科目")["理解度"].mean().sort_values()
    fig, ax = plt.subplots()
    avg_scores.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_ylabel("平均理解度")
    ax.set_title("科目別平均理解度")
    st.pyplot(fig)
    return avg_scores

# -------------------------------
# Gemini APIで課題提案
def suggest_tasks(subject):
    st.subheader("🧠 Geminiによる課題提案")

    if API_KEY == "YOUR_API_KEY":
        st.warning("🔐 Gemini APIキーが未設定です。設定を確認してください。")
        return

    prompt = f"""
    あなたは学習支援AIです。
    ユーザーは「{subject}」の理解度が低めです。
    理解を助けるために、わかりやすく3つのおすすめ課題を提案してください。
    """

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        suggestions = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if suggestions:
            st.markdown(f"**苦手科目: {subject}**")
            st.write(suggestions)
        else:
            st.error("❌ Gemini APIの応答が空でした。")
    except requests.exceptions.RequestException as e:
        st.error(f"API呼び出し中にエラーが発生しました: {e}")
    except Exception as e:
        st.error(f"不明なエラーが発生しました: {e}")



# -------------------------------
# CSV保存（UTF-8 SIGで文字化け防止）
def export_csv(df):
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSVとして保存（文字化け防止）",
        data=csv,
        file_name="learning_log.csv",
        mime="text/csv"
    )

# -------------------------------
# アプリメイン処理
input_section()
df = st.session_state.df
avg_scores = show_progress_chart(df)
if avg_scores is not None:
    weakest_subject = avg_scores.idxmin()
    suggest_tasks(weakest_subject)
export_csv(df)