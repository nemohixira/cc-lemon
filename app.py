import streamlit as st
import time
import uuid
import datetime

# ページの初期設定
st.set_page_config(page_title="CCレモンゲーム 決定版", layout="wide")
st.title("🍋 CCレモンゲーム オンライン対戦")

# ゲームの基本データ定義
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}

# ==========================================
# 1. グローバルデータの初期化 (サーバー共通)
# ==========================================
@st.cache_resource
def get_global_systems():
    return {
        "rooms": {},
        # ランキング・マイページ用の戦績データベース
        # 構造: { user_id: {"name": 名前, "wins": 0, "losses": 0, "total": 0, "history": []} }
        "leaderboard": {
            "mock_1": {"name": "CC王者", "wins": 15, "losses": 3, "total": 18, "history": []},
            "mock_2": {"name": "溜めマスター", "wins": 8, "losses": 8, "total": 16, "history": []}
        }
    }

sys_data = get_global_systems()
global_rooms = sys_data["rooms"]
global_leaderboard = sys_data["leaderboard"]

# ==========================================
# 2. ユーザー固有のセッション初期化 & ニックネームのブラウザ保存（永続化）
# ==========================================
# 疑似的なLocalStorage（ブラウザを閉じても、再度開いたときにデータを引き継ぐためのクッキー風処理）
# 完全に外部保存するにはライブラリが必要なため、Streamlit標準機能で最も堅牢にユーザーIDを維持するロジックを構成
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())

uid = st.session_state.user_uuid

# 初めてアクセスしたプレイヤーを戦績DBに初期登録
if uid not in global_leaderboard:
    global_leaderboard[uid] = {
        "name": "", # 最初は空
        "wins": 0,
        "losses": 0,
        "total": 0,
        "history": [] # 履歴要素: {"opponent": 相手名, "result": "WIN/LOSE", "time": 日時}
    }

# 🚨 【初回のみニックネームを聴く壁】 名前が決まるまでゲームを遊ばせない
if global_leaderboard[uid]["name"] == "":
    st.subheader("👤 はじめにニックネームを設定してください")
    st.write("この名前はランキングや対戦相手の画面に表示されます。")
    input_name = st.text_input("ニックネーム（10文字以内）:", max_chars=10, placeholder="例: 伝説のプレイヤー")
    if st.button("ゲームを始める") and input_name.strip():
        global_leaderboard[uid]["name"] = input_name.strip()
        st.success(f"歓迎します、{input_name.strip()} さん！")
        time.sleep(1)
        st.rerun()
    st.stop() # 名前を入力するまでこれ以降の画面は100%出さない

# セッション状態に名前を同期
my_name = global_leaderboard[uid]["name"]

# ==========================================
# 3. ナビゲーション（サイドバーメニュー切り替え）
# ==========================================
st.sidebar.title("メニュー")
st.sidebar.write(f"👤 プレイヤー: **{my_name}**")
page = st.sidebar.radio("ページ切り替え:", ["ゲームプレイ", "マイページ", "ランキング"])

# 各ブラウザごとの勝利数カウンター（元のコードとの互換性維持用）
if "my_wins" not in st.session_state: st.session_state.my_wins = global_leaderboard[uid]["wins"]
if "opp_wins" not in st.session_state: st.session_state.opp_wins = 0
if "last_counted_turn" not in st.session_state: st.session_state.last_counted_turn = 0
if "battle_logged" not in st.session_state: st.session_state.battle_logged = False

# ==========================================
# 【ページA】 マイページ (戦績・履歴・名前変更)
# ==========================================
if page == "マイページ":
    st.title("👤 マイページ")
    
    # ニックネームの変更セクション
    st.subheader("プロフィール編集")
    col_name_view, col_name_edit = st.columns([2, 1])
    with col_name_view:
        st.write(f"現在のニックネーム: **{my_name}**")
    with col_name_edit:
        with st.popover("📝 変更する"):
            edit_name = st.text_input("新しい名前:", value=my_name, max_chars=10)
            if st.button("変更を確定"):
                if edit_name.strip():
                    global_leaderboard[uid]["name"] = edit_name.strip()
                    st.success("変更しました！")
                    time.sleep(0.5)
                    st.rerun()
                    
    st.divider()
    
    # 戦績データの表示
    stats = global_leaderboard[uid]
    win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
    
    st.subheader("📊 あなたの通算戦績")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    col_stat1.metric("総対戦回数", f"{stats['total']} 回")
    col_stat2.metric("勝利数", f"{stats['wins']} 勝")
    col_stat3.metric("敗北数", f"{stats['losses']} 敗")
    col_stat4.metric("勝率", f"{win_rate:.1f} %")
    
    st.divider()
    
    # 新しい順に対戦履歴をすべて並べる
    st.subheader("⚔️ 対戦履歴（新しい順）")
    if stats["history"]:
        for h in reversed(stats["history"]):
            badge = "🟢【勝利】" if h["result"] == "WIN" else "🔴【敗北】"
            st.write(f"{badge} vs **{h['opponent']}** ｜ 📅 {h['time']}")
    else:
        st.info("対戦履歴はまだありません。ゲームプレイで対戦を行うとここに蓄積されます。")
        
    st.stop()

# ==========================================
# 【ページB】 ランキング (勝率順に自動ソート)
# ==========================================
elif page == "ランキング":
    st.title("🏆 勝率ランキング")
    st.write("対戦回数が1回以上の全プレイヤーが、勝率の高い順にリアルタイムで並びます。")
    
    rank_data = []
    for user_key, u_info in global_leaderboard.items():
        w = u_info["wins"]
        t = u_info["total"]
        wr = (w / t * 100) if t > 0 else 0.0
        
        # 名前が入っている、またはデモデータのみ集計
        if u_info["name"] != "":
            rank_data.append({
                "name": u_info["name"],
                "win_rate": wr,
                "total": t,
                "wins": w,
                "losses": u_info["losses"]
            })
            
    # ソート条件: 勝率が最優先（降順）、同率なら対戦回数が多い順（降順）
    rank_data = sorted(rank_data, key=lambda x: (x["win_rate"], x["total"]), reverse=True)
    
    if rank_data:
        for i, player in enumerate(rank_data, 1):
            # 上位3名には装飾アイコン
            prefix = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else f"第 {i} 位: "
            st.markdown(f"### {prefix} **{player['name']}**")
            st.write(f"勝率: **{player['win_rate']:.1f}%** ｜ 対戦回数: {player['total']}回 ({player['wins']}勝 {player['losses']}敗)")
            st.divider()
    else:
        st.info("現在ランキングに表示できるデータがありません。")
        
    st.stop()

# ==========================================
# 【ページC】 ゲームプレイ (メインバトルエリア)
# ==========================================
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
                    'turn': 1,
                    'players': {'Player 1': True, 'Player 2': False},
                    'player_names': {'Player 1': my_name, 'Player 2': "（未入室）"},
                    'player_uids': {'Player 1': uid, 'Player 2': None},
                    'chat': [f"📢 【システム】プレイヤー「{my_name}」が部屋を作成しました。"], # チャット初期化
                    'winner': None
                }
                st.session_state.my_room = new_room_name
                st.session_state.my_role = 'Player 1'
                st.session_state.last_counted_turn = 0
                st.session_state.battle_logged = False
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
                    room['player_names']['Player 2'] = my_name
                    room['player_uids']['Player 2'] = uid
                    # P2が入室したログをチャットに追加
                    room['chat'].append(f"📢 【システム】プレイヤー「{my_name}」が入室しました。対戦可能です！")
                    st.session_state.my_room = selected_room
                    st.session_state.my_role = 'Player 2'
                    st.session_state.last_counted_turn = 0
                    st.session_state.battle_logged = False
                    st.rerun()
                    
    # 🌟ロビー画面の時は、ここでプログラムを絶対にストップさせる
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

# 部屋データはあるが、相手が退室ボタンを押して消えた場合の処理
if role == 'Player 1' and not state['players']['Player 2'] and state['turn'] > 1:
    st.warning("⚠️ 対戦相手が退室しました。部屋を解散してロビーに戻ります...")
    if room_name in global_rooms: del global_rooms[room_name]
    st.session_state.pop('my_room', None)
    st.session_state.pop('my_role', None)
    time.sleep(2)
    st.rerun()

# ユーザー名が途中で変更されても追従できるように更新
state['player_names'][role] = my_name

# 画面レイアウトを2分割に割る (左側: バトルフィールド、右側: リアルタイムチャット)
col_battle_field, col_chat_field = st.columns([5, 3])

with col_battle_field:
    # 🚪 部屋を途中退室するボタン
    st.success(f"部屋「{room_name}」に 【{my_name} ({role})】 として参加中")
    if st.button("🚪 部屋を出る（ロビーへ戻る）"):
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        
        if role == 'Player 1':
            if room_name in global_rooms: del global_rooms[room_name]
        else:
            state['players']['Player 2'] = False
            state['player_names']['Player 2'] = "（未入室）"
            state['player_uids']['Player 2'] = None
            state['choices']['Player 2'] = None
コードは注意してご使用ください。state['chat'].append(f"❌ 【システム】{my_name} が退室しました。")st.rerun()st.divider()# ⚔️ バトルフィールドopp_display_name = state['player_names'][opp_role]st.subheader(f"⚔️ バトルフィールド (ターン {state['turn']})")col_me, col_opp = st.columns(2)with col_me:st.markdown(f"### 👤 あなた ({my_name}) \nパワー: {state['power'][role]}")st.info(f"出した手: {state['last_choices'][role]}")if state['banned'][role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][role])}")with col_opp:st.markdown(f"### 🤖 相手 ({opp_display_name}) \nパワー: {state['power'][opp_role]}")st.info(f"出した手: {state['last_choices'][opp_role]}")if state['banned'][opp_role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][opp_role])}")st.divider()# 🏆 決着がついたあ後の画面・戦績記録ロジックif state['winner']:if state['winner'] == '引き分け':st.header("🤝 両者行動不能により引き分け！")elif state['winner'] == role:st.header("🎉 勝利！！！")st.balloons()else:st.header("💀 敗北...")st.write("次の行動を選んでください：")# 通算戦績のカウント処理（元コードの画面用セッションカウント）if state['turn'] != st.session_state.last_counted_turn:if state['winner'] == role:st.session_state.my_wins += 1elif state['winner'] == opp_role:st.session_state.opp_wins += 1st.session_state.last_counted_turn = state['turn']# 👑 【新ロジック】グローバルデータベースへの勝敗・履歴自動書き込み (2重書き込み防止付き)if not st.session_state.battle_logged:now_time = datetime.datetime.now().strftime("%m/%d %H:%M")my_db = global_leaderboard[uid]if state['winner'] == '引き分け':# 引き分けは回数のみ追加（またはカウントしない設定も可、ここでは履歴に記載）my_db["total"] += 1my_db["history"].append({"opponent": opp_display_name, "result": "LOSE(DRAW)", "time": now_time})elif state['winner'] == role:my_db["wins"] += 1my_db["total"] += 1my_db["history"].append({"opponent": opp_display_name, "result": "WIN", "time": now_time})else:my_db["losses"] += 1my_db["total"] += 1my_db["history"].append({"opponent": opp_display_name, "result": "LOSE", "time": now_time})st.session_state.battle_logged = Trueif st.button("🔄 もう一度遊ぶ（同じ部屋でリセット）"):state['power'] = {'Player 1': 0, 'Player 2': 0}state['banned'] = {'Player 1': [], 'Player 2': []}state['choices'] = {'Player 1': None, 'Player 2': None}state['last_choices'] = {'Player 1': "まだ行動していません", 'Player 2': "まだ行動していません"}state['log'] = ["ゲームがリセットされました。"]state['turn'] = 1state['winner'] = Nonest.session_state.battle_logged = Falsest.rerun()st.divider()st.subheader("🏆 通算戦績")col_w1, col_w2 = st.columns(2)with col_w1: st.metric(label="あなたの通算勝利数", value=f"{st.session_state.my_wins} 勝")with col_w2: st.metric(label="相手の通算勝利数", value=f"{st.session_state.opp_wins} 勝")# ログとチャットは下に回すため、ここでストップさせずに右チャットを描画させる# ⚔️ アクションボタン選択フェーズ (未決着時のみ)else:if state['choices'][role] is None:st.subheader("👇 次の手を選んでください（相手には見えません）")available_actions = [a for a in actions if a not in state['banned'][role] and action_cost[a] <= state['power'][role]]if not available_actions:state['choices'][role] = "行動不能"st.rerun()else:cols = st.columns(len(available_actions))for idx, act in enumerate(available_actions):with cols[idx]:cost_label = f" ({action_cost[act]})" if action_cost[act] > 0 else ""if st.button(f"{act}{cost_label}", key=f"btn_{act}", use_container_width=True):state['choices'][role] = actst.rerun()else:st.info(f"あなたは「{state['choices'][role]}」を選びました。")st.warning("⏳ 相手の入力を待っています...（自動で進みます）")# 相手が入力を完了するまで裏で見に行く自動センサー@st.fragmentdef wait_for_opponent():while True:if room_name not in global_rooms:breakif global_rooms[room_name]['choices'][opp_role]:breaktime.sleep(1)st.rerun()wait_for_opponent()# ⚖️ 両者が手を選んだら判定処理 (100%元のロジック通り)if state['choices']['Player 1'] and state['choices']['Player 2']:action1 = state['choices']['Player 1']action2 = state['choices']['Player 2']state['last_choices']['Player 1'] = action1state['last_choices']['Player 2'] = action2# パワー計算if action1 != "行動不能":state['power']['Player 1'] -= action_cost[action1]if action1 == '溜め': state['power']['Player 1'] += 1if action2 != "行動不能":state['power']['Player 2'] -= action_cost[action2]if action2 == '溜め': state['power']['Player 2'] += 1# ログに名前を適用p1_n = state['player_names']['Player 1']p2_n = state['player_names']['Player 2']turn_log = f"【ターン {state['turn']}】 {p1_n}: {action1} vs {p2_n}: {action2}"# 🔒 封印処理if action1 == '封印' and action2 not in state['banned']['Player 2'] and action2 != "行動不能":state['banned']['Player 2'].append(action2)turn_log += f" ｜ 🔒 {p1_n}が{p2_n}の「{action2}」を封印！"if action2 == '封印' and action1 not in state['banned']['Player 1'] and action1 != "行動不能":state['banned']['Player 1'].append(action1)turn_log += f" ｜ 🔒 {p2_n}が{p1_n}の「{action1}」を封印！"# 勝敗判定round_winner = Noneif action1 == "行動不能" and action2 == "行動不能": round_winner = '引き分け'elif action1 == "行動不能": round_winner = 'Player 2'elif action2 == "行動不能": round_winner = 'Player 1'elif action1 == '封印' and action2 == 'ミラー': passelif action2 == '封印' and action1 == 'ミラー': passelif action1 == 'レーザー' and action2 != 'ミラー' and action2 != 'レーザー': round_winner = 'Player 1'elif action2 == 'レーザー' and action1 != 'ミラー' and action1 != 'レーザー': round_winner = 'Player 2'elif action1 in ['攻撃', 'レーザー'] and action2 == 'ミラー': round_winner = 'Player 2'elif action2 in ['攻撃', 'レーザー'] and action1 == 'ミラー': round_winner = 'Player 1'elif action1 == '攻撃' and action2 == '溜め': round_winner = 'Player 1'elif action2 == '攻撃' and action1 == '溜め': round_winner = 'Player 2'if round_winner:state['winner'] = round_winnerw_name = p1_n if round_winner == 'Player 1' else p2_n if round_winner == 'Player 2' else "両者"turn_log += f" 🏆 {w_name} の勝利！"state['log'].insert(0, turn_log)# 次のターンのためのリセットstate['choices']['Player 1'] = Nonestate['choices']['Player 2'] = Noneif not state['winner']:state['turn'] += 1st.rerun()# 📜 履歴の表示st.divider()st.subheader("📜 対戦履歴")for log in state['log']: st.write(log)==========================================右側：リアルタイムルームチャット欄の描画==========================================with col_chat_field:st.subheader("💬 ルームチャット")# スクロール可能なチャットコンテナ（高さを350pxに固定）chat_box = st.container(height=350)with chat_box:for msg in state['chat']:st.write(msg)# メッセージ送信フォームwith st.form("room_chat_form", clear_on_submit=True):input_msg = st.text_input("メッセージを送信...", placeholder="対戦よろしく！", label_visibility="collapsed")submit_chat = st.form_submit_button("送信", use_container_width=True)if submit_chat and input_msg.strip():timestamp = datetime.datetime.now().strftime("%H:%M")# 「[時間] 名前: メッセージ」の形で部屋の配列に保存state['chat'].append(f"[{timestamp}] {my_name}: {input_msg.strip()}")st.rerun()
