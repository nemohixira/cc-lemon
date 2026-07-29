import streamlit as st
import time

# ページの初期設定
st.set_page_config(page_title="CCレモンゲーム 決定版", layout="centered")

# --- 全ユーザーで「絶対に同じ部屋データ・ランキング」を共有するための仕組み ---
@st.cache_resource
def get_global_data():
    return {
        'rooms': {},       # 各部屋のデータ
        'rankings': {}     # 全ユーザーのランキング用集計データ
    }

global_data = get_global_data()
global_rooms = global_data['rooms']
global_rankings = global_data['rankings']

# --- URLパラメータを利用したデータの永続化（ブラウザを閉じてもデータを維持する仕組み） ---
if "user_data" not in st.session_state:
    params = st.query_params
    if "p_name" in params:
        st.session_state.user_data = {
            "name": params["p_name"],
            "wins": int(params.get("p_wins", 0)),
            "losses": int(params.get("p_losses", 0)),
            "matches": int(params.get("p_matches", 0)),
            "history": [] # 各要素は {"opp": 相手名, "result": "勝ち"か"負け"か"引き分け"}
        }
    else:
        st.session_state.user_data = None

def sync_data_to_url(u_data):
    """データをURLパラメータに書き込んでブラウザに記憶させる"""
    st.query_params.update(
        p_name=u_data["name"],
        p_wins=u_data["wins"],
        p_losses=u_data["losses"],
        p_matches=u_data["matches"]
    )

# --- 1. ニックネーム登録フェーズ ---
if st.session_state.user_data is None:
    st.title("🍋 CCレモンゲーム オンライン")
    st.subheader("👤 プロフィール登録")
    st.write("ゲームを始める前に、ニックネームを決めてください。")
    name_input = st.text_input("ニックネームを入力（後から変更可能）:", placeholder="例: レモン太郎")
    
    if st.button("登録してプレイ開始") and name_input.strip():
        initial_data = {
            "name": name_input.strip(),
            "wins": 0,
            "losses": 0,
            "matches": 0,
            "history": []
        }
        st.session_state.user_data = initial_data
        sync_data_to_url(initial_data)
        st.rerun()
    st.stop()

# 最新の自分のデータを同期
u_data = st.session_state.user_data
my_name = u_data["name"]

# 各ブラウザ（セッション）ごとに自分の勝利数を記録するためのカウンター（元の変数を維持）
if "my_wins" not in st.session_state: st.session_state.my_wins = u_data["wins"]
if "opp_wins" not in st.session_state: st.session_state.opp_wins = u_data["losses"]
if "last_counted_turn" not in st.session_state: st.session_state.last_counted_turn = 0

# グローバル側のランキング用データを常に最新に更新
global_rankings[my_name] = {
    "name": my_name,
    "wins": u_data["wins"],
    "losses": u_data["losses"],
    "matches": u_data["matches"],
    "win_rate": round((u_data["wins"] / u_data["matches"] * 100), 1) if u_data["matches"] > 0 else 0.0
}

# --- 2. ページ切り替えナビゲーション ---
st.sidebar.title("メニュー")
page = st.sidebar.radio("移動先を選択", ["🎮 ゲームプレイ", "👤 マイページ", "🏆 ランキング"])

# ゲームの基本データ定義
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}

# ==========================================
# 🎮 ゲームプレイ ページ
# ==========================================
if page == "🎮 ゲームプレイ":
    st.title("🍋 CCレモンゲーム オンライン対戦")

    # --- 部屋の選択・作成フェーズ（ロビー） ---
    if "my_room" not in st.session_state:
        st.subheader("🚪 ロビー")
        
        room_list = list(global_rooms.keys())
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 部屋を作る")
            new_room_name = st.text_input("部屋名を入力:", placeholder="例: ぼくの部屋")
            if st.button("部屋を作成して入る") and new_room_name:
                if new_room_name in global_rooms:
                    st.error("その部屋名はすでに使われています。")
                else:
                    global_rooms[new_room_name] = {
                        'power': {'Player 1': 0, 'Player 2': 0},
                        'banned': {'Player 1': [], 'Player 2': []},
                        'choices': {'Player 1': None, 'Player 2': None},
                        'last_choices': {'Player 1': "まだ行動していません", 'Player 2': "まだ行動していません"},
                        'log': ["ゲームが開始されました。"],
                        'chat': [f"📢 システム: {my_name} が部屋を作成しました。"], # チャット初期化
                        'turn': 1,
                        'players': {'Player 1': True, 'Player 2': False},
                        'names': {'Player 1': my_name, 'Player 2': None}, # プレイヤーニックネームを保存
                        'winner': None
                    }
                    st.session_state.my_room = new_room_name
                    st.session_state.my_role = 'Player 1'
                    st.session_state.last_counted_turn = 0
                    st.rerun()
                    
        with col2:
            st.write("### 部屋一覧から入る")
            if not room_list:
                st.info("現在、作られている部屋はありません。部屋ができるとここに自動で表示されます。")
                time.sleep(1)
                st.rerun()
            else:
                selected_room = st.selectbox("部屋を選択:", room_list)
                if st.button("この部屋に入る"):
                    room = global_rooms[selected_room]
                    if room['players']['Player 2']:
                        st.error("この部屋は満員です。")
                    else:
                        room['players']['Player 2'] = True
                        room['names']['Player 2'] = my_name
                        room['chat'].append(f"📢 システム: {my_name} が入室しました。") # 入室ログ
                        st.session_state.my_room = selected_room
                        st.session_state.my_role = 'Player 2'
                        st.session_state.last_counted_turn = 0
                        st.rerun()
                        
        # 🌟ロビー画面の時は、ここでプログラムを絶対にストップさせる
        st.stop() 

    # --- ここからゲーム画面（部屋に入った人のみ進めるエリア） ---
    room_name = st.session_state.my_room
    role = st.session_state.my_role
    opp_role = 'Player 2' if role == 'Player 1' else 'Player 1'

    # もし作成者がすでに退出して部屋が消えた場合の強制送還（主にPlayer 2用）
    if room_name not in global_rooms:
        st.warning("⚠️ 部屋が解散されました。ロビーに戻ります...")
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

    state = global_rooms[room_name]
    my_display_name = state['names'][role]
    opp_display_name = state['names'][opp_role] if state['names'][opp_role] else "対戦相手"

    # 部屋データはあるが、相手が退室ボタンを押して消えた場合の処理（Player 1用）
    if role == 'Player 1' and not state['players']['Player 2'] and state['turn'] > 1:
        st.warning("⚠️ 対戦相手が退室しました。部屋を解散してロビーに戻ります...")
        if room_name in global_rooms: del global_rooms[room_name]
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

    # 🚪 部屋を途中退室するボタン
    st.success(f"部屋「{room_name}」に 【{role}: {my_display_name}】 として参加中")
    if st.button("🚪 部屋を出る（ロビーへ戻る）"):
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        
        if role == 'Player 1':
            if room_name in global_rooms: del global_rooms[room_name]
        else:
            state['players']['Player 2'] = False
            state['names']['Player 2'] = None
            state['choices']['Player 2'] = None
            state['chat'].append(f"📢 システム: {my_display_name} が退室しました。")
            
        st.rerun()

    st.divider()

    # ⚔️ バトルフィールド
    st.subheader(f"⚔️ バトルフィールド (ターン {state['turn']})")
    col_me, col_opp = st.columns(2)
    with col_me:
        st.markdown(f"### 👤 あなた ({my_display_name})")
        st.write(f"**パワー**: {state['power'][role]}")
        st.info(f"出した手: **{state['last_choices'][role]}**")
        if state['banned'][role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][role])}")
    with col_opp:
        st.markdown(f"### 🤖 相手 ({opp_display_name})")
        if state['names'][opp_role]:
            st.write(f"**パワー**: {state['power'][opp_role]}")
        else:
            st.write("**状態**: 相手の入室を待っています...")
        st.info(f"出した手: **{state['last_choices'][opp_role]}**")
        if state['banned'][opp_role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][opp_role])}")

    st.divider()

    # 💬 自由チャットエリア
    st.subheader("💬 部屋内チャット")
    chat_box = st.container(height=180, border=True)
    with chat_box:
        for msg in reversed(state['chat']):
            st.write(msg)
            
    with st.form(key="chat_form", clear_on_submit=True):
        chat_input = st.text_input("メッセージを入力:", placeholder="対戦よろしくお願いします！")
        submit_chat = st.form_submit_button("送信")
        if submit_chat and chat_input.strip():
            state['chat'].append(f"💬 {my_display_name}: {chat_input.strip()}")
            st.rerun()

    st.divider()

    # 🏆 決着がついたあとの画面
    if state['winner']:
        if state['winner'] == '引き分け':
            st.header("🤝 両者行動不能により引き分け！")
        elif state['winner'] == role:
            st.header("🎉 勝利！！！")
            st.balloons()
        else:
            st.header("💀 敗北...")
            
        st.write("次の行動を選んでください：")
        
        # 通算戦績のカウント処理（永続ストレージとセッション両方に記録）
        if state['turn'] != st.session_state.last_counted_turn:
            u_data["matches"] += 1
            if state['winner'] == role:
                st.session_state.my_wins += 1
                u_data["wins"] += 1
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "勝ち"})
            elif state['winner'] == opp_role:
                st.session_state.opp_wins += 1
                u_data["losses"] += 1
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "負け"})
            else:
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "引き分け"})
                
            st.session_state.user_data = u_data
            sync_data_to_url(u_data) # URLパラメータへ同期
            st.session_state.last_counted_turn = state['turn']
            st.rerun()
            
        if st.button("🔄 もう一度遊ぶ（同じ部屋でリセット）"):
            state['power'] = {'Player 1': 0, 'Player 2': 0}
            state['banned'] = {'Player 1': [], 'Player 2': []}
            state['choices'] = {'Player 1': None, 'Player 2': None}
            state['last_choices'] = {'Player 1': "まだ行動していません", 'Player 2': "まだ行動していません"}
            state['log'] = ["ゲームがリセットされました。"]
            state['turn'] = 1
