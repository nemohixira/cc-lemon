import streamlit as st
import time

# ページの初期設定
st.set_page_config(page_title="CCレモンゲーム 決定版", layout="centered")

# --- グローバル共有データ（サーバーメモリ） ---
@st.cache_resource
def get_global_data():
    return {
        'rooms': {},       # 各部屋のデータ
        'rankings': {}     # 全ユーザーのランキング用集計データ
    }

global_data = get_global_data()
global_rooms = global_data['rooms']
global_rankings = global_data['rankings']

# --- URLパラメータを利用したデータの擬似永続化 ---
if "user_data" not in st.session_state:
    params = st.query_params
    if "p_name" in params:
        st.session_state.user_data = {
            "name": params["p_name"],
            "wins": int(params.get("p_wins", 0)),
            "losses": int(params.get("p_losses", 0)),
            "matches": int(params.get("p_matches", 0)),
            "history": [] 
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

# --- 1. ニックネーム登録・確認フェーズ ---
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

# グローバル側のランキング用データを常に最新に更新
global_rankings[my_name] = {
    "name": my_name,
    "wins": u_data["wins"],
    "losses": u_data["losses"],
    "matches": u_data["matches"],
    "win_rate": round((u_data["wins"] / u_data["matches"] * 100), 1) if u_data["matches"] > 0 else 0.0
}

# --- 2. ページ切り替え（ナビゲーション） ---
st.sidebar.title("メニュー")
page = st.sidebar.radio("移動先を選択", ["🎮 ゲームプレイ", "👤 マイページ", "🏆 ランキング"])

# 各ゲームの基本データ定義
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}

if "last_counted_turn" not in st.session_state: st.session_state.last_counted_turn = 0

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
                        'chat': [f"📢 システム: {my_name} が部屋を作成しました。"],
                        'turn': 1,
                        'players': {'Player 1': True, 'Player 2': False},
                        'names': {'Player 1': my_name, 'Player 2': None},
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
                        room['chat'].append(f"📢 システム: {my_name} が入室しました。")
                        st.session_state.my_room = selected_room
                        st.session_state.my_role = 'Player 2'
                        st.session_state.last_counted_turn = 0
                        st.rerun()
                        
        st.stop() 

    # --- ここからゲーム画面 ---
    room_name = st.session_state.my_room
    role = st.session_state.my_role
    opp_role = 'Player 2' if role == 'Player 1' else 'Player 1'

    if room_name not in global_rooms:
        st.warning("⚠️ 部屋が解散されました。ロビーに戻ります...")
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

    state = global_rooms[room_name]
    my_display_name = state['names'][role]
    opp_display_name = state['names'][opp_role] if state['names'][opp_role] else "対戦相手"

    if role == 'Player 1' and not state['players']['Player 2'] and state['turn'] > 1:
        st.warning("⚠️ 対戦相手が退室しました。部屋を解散してロビーに戻ります...")
        if room_name in global_rooms: del global_rooms[room_name]
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

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
            st.write("**状態**: 待機中...")
        st.info(f"出した手: **{state['last_choices'][opp_role]}**")
        if state['banned'][opp_role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][opp_role])}")

    st.divider()

    # 💬 チャットエリア
    st.subheader("💬 部屋のチャット履歴")
    chat_box = st.container(height=180, border=True)
    with chat_box:
        for msg in reversed(state['chat']):
            st.write(msg)
            
    with st.form(key="chat_form", clear_on_submit=True):
        chat_input = st.text_input("メッセージを入力:", placeholder="よろしくおねがいします！")
        submit_chat = st.form_submit_button("送信")
        if submit_chat and chat_input.strip():
            state['chat'].append(f"💬 {my_display_name}: {chat_input.strip()}")
            st.rerun()

    st.divider()

    # 🏆 決着判定
    if state['winner']:
        if state['winner'] == '引き分け':
            st.header("🤝 両者行動不能により引き分け！")
        elif state['winner'] == role:
            st.header("🎉 勝利！！！")
            st.balloons()
        else:
            st.header("💀 敗北...")
            
        if state['turn'] != st.session_state.last_counted_turn:
            u_data["matches"] += 1
            if state['winner'] == role:
                u_data["wins"] += 1
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "勝ち"})
            elif state['winner'] == opp_role:
                u_data["losses"] += 1
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "負け"})
            else:
                u_data["history"].insert(0, {"opp": opp_display_name, "result": "引き分け"})
                
            st.session_state.user_data = u_data
            sync_data_to_url(u_data)
            st.session_state.last_counted_turn = state['turn']
            st.rerun()
            
        if st.button("🔄 もう一度遊ぶ（同じ部屋でリセット）"):
            state['power'] = {'Player 1': 0, 'Player 2': 0}
            state['banned'] = {'Player 1': [], 'Player 2': []}
            state['choices'] = {'Player 1': None, 'Player 2': None}
            state['last_choices'] = {'Player 1': "まだ行動していません", 'Player 2': "まだ行動していません"}
            state['log'] = ["ゲームがリセットされました。"]
            state['turn'] = 1
            state['winner'] = None
            st.rerun()
        st.stop()

    # ⚔️ アクションボタン選択フェーズ
    if state['choices'][role] is None:
        st.subheader("👇 次の手を選んでください（相手には見えません）")
        available_actions = [a for a in actions if a not in state['banned'][role] and action_cost[a] <= state['power'][role]]
        
        if not available_actions:
            state['choices'][role] = "行動不能"
            st.rerun()
        else:
            cols = st.columns(len(available_actions))
            for idx, act in enumerate(available_actions):
                with cols[idx]:
                    cost_label = f" ({action_cost[act]})" if action_cost[act] > 0 else ""
