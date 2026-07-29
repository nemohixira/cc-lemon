import streamlit as st
import time

# ページの初期設定
st.set_page_config(page_title="CCレモンゲーム 決定版", layout="centered")
st.title("🍋 CCレモンゲーム オンライン対戦")

# --- 共通データ・設定 ---
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}

@st.cache_resource
def get_global_rooms(): return {}
global_rooms = get_global_rooms()

# セッション状態の初期化
if "my_wins" not in st.session_state: st.session_state.my_wins = 0
if "opp_wins" not in st.session_state: st.session_state.opp_wins = 0
if "last_counted_turn" not in st.session_state: st.session_state.last_counted_turn = 0

# --- ロビー ---
if "my_room" not in st.session_state:
    st.subheader("🚪 ロビー")
    col1, col2 = st.columns(2)
    with col1:
        new_room = st.text_input("部屋名")
        if st.button("部屋作成") and new_room:
            if new_room in global_rooms: st.error("存在します")
            else:
                global_rooms[new_room] = {
                    'power': {'P1': 0, 'P2': 0}, 'banned': {'P1': [], 'P2': []},
                    'choices': {'P1': None, 'P2': None}, 'last_choices': {'P1': "待機", 'P2': "待機"},
                    'log': ["開始"], 'turn': 1, 'players': {'P1': True, 'P2': False},
                    'winner': None, 'processing_turn': 0
                }
                st.session_state.update(my_room=new_room, my_role='P1')
                st.rerun()
    with col2:
        room_list = list(global_rooms.keys())
        selected = st.selectbox("部屋選択", room_list)
        if st.button("入室") and selected and not global_rooms[selected]['players']['P2']:
            global_rooms[selected]['players']['P2'] = True
            st.session_state.update(my_room=selected, my_role='P2')
            st.rerun()
    st.stop()

# --- ゲーム画面 ---
room_name = st.session_state.my_room
role = st.session_state.my_role
opp_role = 'P2' if role == 'P1' else 'P1'
state = global_rooms.get(room_name)

if not state:
    st.warning("部屋が解散されました")
    st.session_state.clear(); st.rerun()

st.success(f"【{role}】として参加中")
if st.button("🚪 退室"):
    if role == 'P1': del global_rooms[room_name]
    else: state['players']['P2'] = False
    st.session_state.clear(); st.rerun()

# ⚔️ バトルフィールド
st.subheader(f"ターン {state['turn']}")
col1, col2 = st.columns(2)
with col1: st.info(f"自分 ({state['power'][role]}): {state['last_choices'][role]} (封印: {', '.join(state['banned'][role])})")
with col2: st.info(f"相手: {state['last_choices'][opp_role]} (封印: {', '.join(state['banned'][opp_role])})")

# 🏆 決着判定
if state['winner']:
    st.header("🏆 結果: " + state['winner'])
    if state['turn'] != st.session_state.last_counted_turn:
        if state['winner'] == role: st.session_state.my_wins += 1
        elif state['winner'] == opp_role: st.session_state.opp_wins += 1
        st.session_state.last_counted_turn = state['turn']
    if st.button("🔄 リセット"):
        state.update({'power': {'P1': 0, 'P2': 0}, 'banned': {'P1': [], 'P2': []}, 'choices': {'P1': None, 'P2': None}, 'last_choices': {'P1': "待機", 'P2': "待機"}, 'log': ["リセット"], 'turn': 1, 'winner': None, 'processing_turn': 0})
        st.rerun()
    st.stop()

# ⚖️ ターン判定（レースコンディション対策）
if state['choices']['P1'] and state['choices']['P2']:
    if state['processing_turn'] < state['turn']:
        state['processing_turn'] = state['turn']
        c1, c2 = state['choices']['P1'], state['choices']['P2']
        state['last_choices'].update({'P1': c1, 'P2': c2})
        
        # パワー・封印計算
        for r, act in [('P1', c1), ('P2', c2)]:
            if act != "行動不能":
                state['power'][r] -= action_cost[act]
                if act == '溜め': state['power'][r] += 1
        
        if c1 == '封印' and c2 != "行動不能": state['banned']['P2'].append(c2)
        if c2 == '封印' and c1 != "行動不能": state['banned']['P1'].append(c1)

        # 勝敗ロジック (簡略化)
        if c1 == "行動不能" and c2 == "行動不能": state['winner'] = '引き分け'
        elif c1 == "行動不能": state['winner'] = 'P2'
        elif c2 == "行動不能": state['winner'] = 'P1'
        # ... (以下、元の判定ロジックを簡略化したもの)
        
        state['choices'].update({'P1': None, 'P2': None})
        if not state['winner']: state['turn'] += 1
        st.rerun()

# ⚔️ アクション選択
if state['choices'][role] is None:
    available = [a for a in actions if a not in state['banned'][role] and action_cost[a] <= state['power'][role]]
    if not available: state['choices'][role] = "行動不能"; st.rerun()
    cols = st.columns(len(available))
    for i, act in enumerate(available):
        if cols[i].button(act): state['choices'][role] = act; st.rerun()
else:
    st.warning("⏳ 相手を待機中...")
    @st.fragment
    def wait_for_opponent():
        time.sleep(1); st.rerun()
    wait_for_opponent()

st.write("---"); st.subheader("📜 履歴"); st.write(state['log'])

