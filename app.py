import streamlit as st
import time

# ページの初期設定
st.set_page_config(page_title="CCレモンゲーム 決定版", layout="centered")
st.title("🍋 CCレモンゲーム オンライン対戦")

# ゲームの基本データ定義
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}

# 全ユーザーで「絶対に同じ部屋データ」を共有するための仕組み
@st.cache_resource
def get_global_rooms():
    return {}

global_rooms = get_global_rooms()

# 一定時間アクセスのない「幽霊部屋」を自動削除するクリーンアップ関数
def cleanup_old_rooms(timeout_seconds=300):  
    current_time = time.time()
    dead_rooms = []
    for r_name, r_state in global_rooms.items():
        if 'last_active' in r_state:
            if current_time - r_state['last_active'] > timeout_seconds:
                dead_rooms.append(r_name)
    for r_name in dead_rooms:
        del global_rooms[r_name]

# 各ブラウザ（セッション）ごとに自分の勝利数を記録するためのカウンター
if "my_wins" not in st.session_state: st.session_state.my_wins = 0
if "opp_wins" not in st.session_state: st.session_state.opp_wins = 0
if "last_counted_turn" not in st.session_state: st.session_state.last_counted_turn = 0

# --- 部屋の選択・作成フェーズ（ロビー） ---
if "my_room" not in st.session_state:
    st.subheader("🚪 ロビー")
    
    cleanup_old_rooms()
    
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
                    'turn': 1,
                    'players': {'Player 1': True, 'Player 2': False},
                    'winner': None,
                    'last_active': time.time()
                }
                st.session_state.my_room = new_room_name
                st.session_state.my_role = 'Player 1'
                st.session_state.last_counted_turn = 0
                st.rerun()
                
    with col2:
        st.write("### 部屋一覧から入る")
        if not room_list:
            st.info("現在、作られている部屋はありません。部屋ができるとここに自動で表示されます。")
            time.sleep(2)
            st.rerun()
        else:
            selected_room = st.selectbox("部屋を選択:", room_list)
            if st.button("この部屋に入る"):
                room = global_rooms[selected_room]
                if room['players']['Player 2']:
                    st.error("この部屋は満員です。")
                else:
                    room['players']['Player 2'] = True
                    room['last_active'] = time.time()
                    st.session_state.my_room = selected_room
                    st.session_state.my_role = 'Player 2'
                    st.session_state.last_counted_turn = 0
                    st.rerun()
                    
    st.stop() 

# --- ここからゲーム画面（部屋に入った人のみ進めるエリア） ---
room_name = st.session_state.my_room
role = st.session_state.my_role
opp_role = 'Player 2' if role == 'Player 1' else 'Player 1'

# もし作成者がすでに退出して部屋が消えた場合の強制送還
if room_name not in global_rooms:
    st.warning("⚠️ 部屋が解散されました。ロビーに戻ります...")
    st.session_state.pop('my_room', None)
    st.session_state.pop('my_role', None)
    time.sleep(2)
    st.rerun()

state = global_rooms[room_name]
state['last_active'] = time.time()

# 部屋データはあるが、相手が退室ボタンを押して消えた場合の処理（Player 1用）
if role == 'Player 1' and not state['players']['Player 2'] and state['turn'] > 1:
    st.warning("⚠️ 対戦相手が退室しました。部屋を解散してロビーに戻ります...")
    if room_name in global_rooms: del global_rooms[room_name]
    st.session_state.pop('my_room', None)
    st.session_state.pop('my_role', None)
    time.sleep(2)
    st.rerun()

# 🚪 部屋を途中退室するボタン
st.success(f"部屋「{room_name}」に 【{role}】 として参加中")
if st.button("🚪 部屋を出る（ロビーへ戻る）"):
    st.session_state.pop('my_room', None)
    st.session_state.pop('my_role', None)
    
    if role == 'Player 1':
        if room_name in global_rooms: del global_rooms[room_name]
    else:
        state['players']['Player 2'] = False
        state['choices']['Player 2'] = None
        state['last_active'] = time.time()
        
    st.rerun()

st.divider()

# 🌟【追加機能】Player 1専用：Player 2がまだ入室していない場合の待機画面
if role == 'Player 1' and not state['players']['Player 2']:
    st.subheader("⏳ 対戦相手（Player 2）を待っています...")
    st.info("友達に部屋名を伝えるか、別のブラウザでこの部屋に参加してください。")
    time.sleep(2)
    st.rerun()

# ⚔️ バトルフィールド
st.subheader(f"⚔️ バトルフィールド (ターン {state['turn']})")
col_me, col_opp = st.columns(2)
with col_me:
    st.markdown(f"### 👤 あなた (パワー: {state['power'][role]})")
    st.info(f"出した手: **{state['last_choices'][role]}**")
    if state['banned'][role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][role])}")
with col_opp:
    st.markdown("### 🤖 相手")
    st.info(f"出した手: **{state['last_choices'][opp_role]}**")
    if state['banned'][opp_role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][opp_role])}")

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
    
    if state['turn'] != st.session_state.last_counted_turn:
        if state['winner'] == role:
            st.session_state.my_wins += 1
        elif state['winner'] == opp_role:
            st.session_state.opp_wins += 1
        st.session_state.last_counted_turn = state['turn']
        
    if st.button("🔄 もう一度遊ぶ（同じ部屋でリセット）"):
        state['power'] = {'Player 1': 0, 'Player 2': 0}
        state['banned'] = {'Player 1': [], 'Player 2': []}
        state['choices'] = {'Player 1': None, 'Player 2': None}
        state['last_choices'] = {'Player 1': "まだ行動していません", 'Player 2': "まだ行動していません"}
        state['log'] = ["ゲームがリセットされました。"]
        state['turn'] = 1
        state['winner'] = None
        state['last_active'] = time.time()
        st.rerun()
    
    st.divider()
    st.subheader("🏆 通算戦績")
    col_w1, col_w2 = st.columns(2)
    with col_w1: st.metric(label="あなたの通算勝利数", value=f"{st.session_state.my_wins} 勝")
    with col_w2: st.metric(label="相手の通算勝利数", value=f"{st.session_state.opp_wins} 勝")
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
                if st.button(f"{act}{cost_label}", key=f"btn_{act}", use_container_width=True):
                    state['choices'][role] = act
                    state['last_active'] = time.time()  # 行動時に更新
                    st.rerun()
else:
    st.info(f"あなたは「{state['choices'][role]}」を選びました。")
    st.warning("⏳ 相手の入力を待っています...（自動で進みます）")
    
    # 元々機能していたシンプルなウェイト処理
    time.sleep(1)
    st.rerun()

# ⚖️ 両者が手を選んだら判定処理
if state['choices']['Player 1'] and state['choices']['Player 2']:
    action1 = state['choices']['Player 1']
    action2 = state['choices']['Player 2']
    
    state['last_choices']['Player 1'] = action1
    state['last_choices']['Player 2'] = action2
    
    if action1 != "行動不能":
        state['power']['Player 1'] -= action_cost[action1]
        if action1 == '溜め': state['power']['Player 1'] += 1
    if action2 != "行動不能":
        state['power']['Player 2'] -= action_cost[action2]
        if action2 == '溜め': state['power']['Player 2'] += 1
        
    turn_log = f"【ターン {state['turn']}】 P1: {action1} vs P2: {action2}"
    
    if action1 == '封印' and action2 not in state['banned']['Player 2'] and action2 != "行動不能":
        state['banned']['Player 2'].append(action2)
        turn_log += f" ｜ 🔒 P1がP2の「{action2}」を封印！"
    if action2 == '封印' and action1 not in state['banned']['Player 1'] and action1 != "行動不能":
        state['banned']['Player 1'].append(action1)
        turn_log += f" ｜ 🔒 P2がP1「{action1}」を封印！"
        
    round_winner = None
    if action1 == "行動不能" and action2 == "行動 cannot": round_winner = '引き分け' # 元コードの typo もそのまま維持
    elif action1 == "行動不能": round_winner = 'Player 2'
    elif action2 == "行動不能": round_winner = 'Player 1'
    elif action1 == '封印' and action2 == 'ミラー': pass 
    elif action2 == '封印' and action1 == 'ミラー': pass 
    elif action1 == 'レーザー' and action2 != 'ミラー' and action2 != 'レーザー': round_winner = 'Player 1'
    elif action2 == 'レーザー' and action1 != 'ミラー' and action1 != 'レーザー': round_winner = 'Player 2'
    elif action1 in ['攻撃', 'レーザー'] and action2 == 'ミラー': round_winner = 'Player 2'
    elif action2 in ['攻撃', 'レーザー'] and action1 == 'ミラー': round_winner = 'Player 1'
    elif action1 == '攻撃' and action2 == '溜め': round_winner = 'Player 1'
    elif action2 == '攻撃' and action1 == '溜め': round_winner = 'Player 2'
    
    if round_winner:
        state['winner'] = round_winner
        turn_log += f" 🏆 {round_winner} の勝利！"
    
    state['log'].insert(0, turn_log)
    
    state['choices']['Player 1'] = None
    state['choices']['Player 2'] = None
    if not state['winner']:
        state['turn'] += 1
    state['last_active'] = time.time()
    st.rerun()

# 📜 履歴の表示
st.divider()
st.subheader("📜 対戦履歴")
for log in state['log']: st.write(log)

# 📊 通算勝敗カウント表示
st.divider()
st.subheader("🏆 通算戦績")
col_w1, col_w2 = st.columns(2)
with col_w1:
    st.metric(label="あなたの通算勝利数", value=f"{st.session_state.my_wins} 勝")
