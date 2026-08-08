import streamlit as st
import time
import random
import json
import os
from datetime import datetime

# 1. ページの初期設定
st.set_page_config(page_title="CCレモンゲーム", layout="centered")

# --- データをファイルに永久保存するための仕組み（永続化） ---
DATA_FILE = "game_data.json"

@st.cache_resource
def get_global_data():
    # もし過去に保存したJSONファイルがあれば読み込む
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 最低限必要なキーが存在するか確認
                if 'rooms' not in data: data['rooms'] = {}
                if 'users' not in data: data['users'] = {}
                if 'reports' not in data: data['reports'] = []
                return data
        except Exception:
            pass
            
    # ファイルがない、または破損している場合は初期データを作る
    return {
        'rooms': {},         # 部屋データ
        'users': {},         # 登録ユーザーデータ
        'reports': []        # 問い合わせ内容保存用
    }

global_data = get_global_data()
global_rooms = global_data['rooms']
global_users = global_data['users']
global_reports = global_data['reports']

# データをJSONファイルに書き出す関数
def save_global_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 管理者アカウントの初期作成（問い合わせ確認用） ---
if "admin" not in global_users:
    global_users["admin"] = {
        "password": "adminpassword123", 
        "wins": 0, "losses": 0, "matches": 0, "history": [],
        "crowns": {"gold": 0, "silver": 0, "bronze": 0}
    }
    save_global_data()

# 同率順位に対応した週間ランキング集計関数（型安全性を強化してエラーを防止）
def get_ranked_players():
    if not global_users:
        return []
    
    players = []
    for name, data in global_users.items():
        if name == "admin":
            continue
        # データ構造が不完全だった場合の安全対策
        wins = data.get('wins', 0)
        players.append((name, data, wins))
        
    # 確実な勝利数(wins)ベースでのソート
    sorted_players = sorted(players, key=lambda x: x[2], reverse=True)
    
    ranked_results = []
    current_rank = 1
    
    for i, (name, data, wins) in enumerate(sorted_players):
        if i > 0 and wins == sorted_players[i-1][2]:
            pass
        else:
            current_rank = i + 1
            
        ranked_results.append((current_rank, name, data))
        
    return ranked_results

# --- セッション状態の初期化 ---
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# ゲームの基本アクションとコストの定義
actions = ['溜め', '攻撃', 'ミラー', '封印', 'レーザー', 'バリア']
action_cost = {'溜め': 0, '攻撃': 1, 'ミラー': 2, '封印': 3, 'レーザー': 5, 'バリア': 0}


# ==========================================
# 🔑 認証フェーズ（未ログイン時）
# ==========================================
if st.session_state.logged_in_user is None:
    st.title("🍋 CCレモンゲーム")
    st.subheader("🚪 ゲームへの入り口")
    
    tab1, tab2 = st.tabs(["📝 新規登録", "🔑 ログイン"])
    
    with tab1:
        st.write("### アカウントを作成する")
        st.caption("⚠️ ニックネームはランキングなどで全体に表示されます。ご注意ください。")
        reg_name = st.text_input("希望するニックネーム:", key="reg_name").strip()
        
        show_reg_pwd = st.checkbox("パスワードを表示する", key="show_reg_pwd")
        reg_pwd = st.text_input("パスワード:", type="default" if show_reg_pwd else "password", key="reg_pwd")
        
        if st.button("新規登録してプレイ開始"):
            if not reg_name or not reg_pwd:
                st.error("ニックネームとパスワードを両方入力してください。")
            elif reg_name in global_users:
                # 💥 修正点: 赤文字エラーをタブ内に閉じ込めるため、ここでクリアして即座にリラン
                st.error("このニックネームは使用されています")
                st.session_state.reg_name = ""
                time.sleep(1.5)
                st.rerun()
            else:
                global_users[reg_name] = {
                    "password": reg_pwd,
                    "wins": 0, "losses": 0, "matches": 0,
                    "history": [],
                    "crowns": {"gold": 0, "silver": 0, "bronze": 0}
                }
                save_global_data() # JSONファイルに永久保存
                st.session_state.logged_in_user = reg_name
                st.success("ユーザー登録が完了しました！")
                time.sleep(1)
                st.rerun()
                
    with tab2:
        st.write("### 登録済みアカウントでログイン")
        login_name = st.text_input("ニックネーム:", key="login_name").strip()
        
        show_login_pwd = st.checkbox("パスワードを表示する", key="show_login_pwd")
        login_pwd = st.text_input("パスワード:", type="default" if show_login_pwd else "password", key="login_pwd")
        
        if st.button("ログインする"):
            if login_name in global_users and global_users[login_name]["password"] == login_pwd:
                st.session_state.logged_in_user = login_name
                st.success(f"おかえりなさい、{login_name} さん！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("このニックネームとパスワードの組み合わせはありません")
                st.session_state.login_name = ""
                st.session_state.login_pwd = ""
                time.sleep(1.5)
                st.rerun()
                
    st.stop()
# ==========================================
# 📱 ログイン後：共通ナビゲーション
# ==========================================
my_name = st.session_state.logged_in_user
u_data = global_users[my_name]

# サイドバーメニューの構築
st.sidebar.title(f"👤 {my_name}")
st.sidebar.markdown(f"👑 獲得王冠  \n🥇 金: {u_data['crowns']['gold']} | 🥈 銀: {u_data['crowns']['silver']} | 🥉 銅: {u_data['crowns']['bronze']}")

menu_options = ["🎮 ゲームロビー", "👤 マイページ", "🏆 週間ランキング", "📩 お問い合わせ"]
if my_name == "admin":
    menu_options.append("🛠️ 管理者ダッシュボード")

page = st.sidebar.radio("メニュー移動", menu_options)

# ログアウト処理
if st.sidebar.button("🚪 ログアウト"):
    st.session_state.logged_in_user = None
    st.session_state.pop('my_room', None)
    st.session_state.pop('my_role', None)
    st.rerun()


# ==========================================
# 🎮 ゲームロビー / プレイ ページ
# ==========================================
if page == "🎮 ゲームロビー":
    
    # --- 部屋の選択・作成フェーズ（ロビー） ---
    if "my_room" not in st.session_state:
        st.title("🍋 CCレモンゲーム")
        st.subheader("🚪 対戦ロビー")
        
        # 3人目が入るのを防ぐため、Player 2が未参加の空き部屋だけを一覧に抽出
        active_rooms = {k: v for k, v in global_rooms.items() if not v['players']['Player 2']}
        room_list = list(active_rooms.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### 部屋を作る")
            new_room_name = st.text_input("部屋名を入力:", placeholder="例: ぼくの部屋")
            
            show_room_pwd = st.checkbox("部屋にパスワードを設定する")
            room_pwd = ""
            if show_room_pwd:
                room_pwd = st.text_input("部屋のパスワード:", type="password")
                st.caption("⚠️ パスワードを設定すると、パスワードを知っている人しか部屋に入れなくなります。")
                
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
                        'chat': [f"📢 [{datetime.now().strftime('%H:%M')}] システム: {my_name} が部屋を作成しました。"],
                        'turn': 1,
                        'players': {'Player 1': True, 'Player 2': False},
                        'names': {'Player 1': my_name, 'Player 2': None},
                        'password': room_pwd if show_room_pwd else None,
                        'winner': None
                    }
                    save_global_data()
                    st.session_state.my_room = new_room_name
                    st.session_state.my_role = 'Player 1'
                    st.session_state.last_counted_turn = 0
                    st.rerun()
                    
        with col2:
            st.write("### 部屋一覧から入る")
            
            # 🔀 ランダム入室機能
            if st.button("🔀 ランダムで部屋に入る"):
                open_rooms = [k for k, v in active_rooms.items() if v['password'] is None or v['password'] == ""]
                if open_rooms:
                    chosen_room = random.choice(open_rooms)
                    room = global_rooms[chosen_room]
                    room['players']['Player 2'] = True
                    room['names']['Player 2'] = my_name
                    room['chat'].append(f"📢 [{datetime.now().strftime('%H:%M')}] システム: {my_name} が入室しました。")
                    save_global_data()
                    st.session_state.my_room = chosen_room
                    st.session_state.my_role = 'Player 2'
                    st.session_state.last_counted_turn = 0
                    st.success(f"{chosen_room} にマッチングしました！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("現在、すぐに設定なしで入れる空き部屋がありません。")
            
            st.divider()
            
            if not room_list:
                st.info("現在、募集中の部屋はありません。部屋ができるとここに自動で表示されます。")
                time.sleep(2)
                st.rerun()
            else:
                selected_room = st.selectbox("部屋を選択:", room_list)
                room = global_rooms[selected_room]
                
                input_room_pwd = ""
                if room['password']:
                    input_room_pwd = st.text_input("🔑 鍵付きの部屋です。パスワードを入力:", type="password", key=f"pwd_{selected_room}")
                
                if st.button("この部屋に入る"):
                    if room['players']['Player 2']:
                        st.error("この部屋は満員です。")
                    elif room['password'] and room['password'] != input_room_pwd:
                        st.error("❌ パスワードが違います")
                    else:
                        room['players']['Player 2'] = True
                        room['names']['Player 2'] = my_name
                        # 💥 改善点：Player 2が入る前の会話ログもすべて維持された共通配列(room['chat'])へ入室通知を追記
                        room['chat'].append(f"📢 [{datetime.now().strftime('%H:%M')}] システム: {my_name} が入室しました。")
                        save_global_data()
                        st.session_state.my_room = selected_room
                        st.session_state.my_role = 'Player 2'
                        st.session_state.last_counted_turn = 0
                        st.rerun()
                        
        st.stop() 


    # --- ここからゲーム画面（部屋に入った人のみ進めるエリア） ---
    room_name = st.session_state.my_room
    role = st.session_state.my_role
    opp_role = 'Player 2' if role == 'Player 1' else 'Player 1'

    # 部屋が解散・上書き削除された場合の即時検知
    if room_name not in global_rooms:
        st.warning("⚠️ 部屋が解散されました。ロビーに戻ります...")
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

    state = global_rooms[room_name]
    
    # キック（退出）させられていないか確認
    if role == 'Player 2' and not state['players']['Player 2']:
        st.error("❌ 部屋主（Player 1）によって退出させられました。")
        st.session_state.pop('my_room', None)
        st.session_state.pop('my_role', None)
        time.sleep(2)
        st.rerun()

    my_display_name = state['names'][role]
    opp_display_name = state['names'][opp_role] if state['names'][opp_role] else "（待機中...）"

    st.success(f"部屋「{room_name}」に参加中")
    
    col_leave, col_kick = st.columns(2)
    with col_leave:
        if st.button("🚪 部屋を出る（ロビーへ戻る）"):
            if role == 'Player 1':
                if room_name in global_rooms: 
                    del global_rooms[room_name]
            else:
                state['players']['Player 2'] = False
                state['names']['Player 2'] = None
                state['choices']['Player 2'] = None
                state['chat'].append(f"📢 [{datetime.now().strftime('%H:%M')}] システム: {my_display_name} が退室しました。")
            
            save_global_data()
            st.session_state.pop('my_room', None)
            st.session_state.pop('my_role', None)
            st.rerun()

    with col_kick:
        if role == 'Player 1' and state['players']['Player 2']:
            if st.button("💥 相手プレイヤーを退室させる"):
                state['chat'].append(f"📢 [{datetime.now().strftime('%H:%M')}] システム: {state['names']['Player 2']} がキックされました。")
                state['players']['Player 2'] = False
                state['names']['Player 2'] = None
                state['choices']['Player 2'] = None
                save_global_data()
                st.rerun()

    st.divider()

    # ⚔️ バトルフィールド表示
    st.subheader(f"⚔️ バトルフィールド (ターン {state['turn']})")
    col_me, col_opp = st.columns(2)
    with col_me:
        st.markdown(f"### 👤 あなた: {my_display_name}")
        st.metric(label="パワー", value=state['power'][role])
        st.info(f"出した手: **{state['last_choices'][role]}**")
        if state['banned'][role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][role])}")
    with col_opp:
        st.markdown(f"### 🤖 相手: {opp_display_name}")
        if state['names'][opp_role]:
            st.metric(label="パワー", value=state['power'][opp_role])
        else:
            st.write("⚠️ 相手の入室を待っています...")
        st.info(f"出した手: **{state['last_choices'][opp_role]}**")
        if state['banned'][opp_role]: st.warning(f"🔒 封印中: {', '.join(state['banned'][opp_role])}")

    st.divider()
    # 🏆 決着判定フェーズ
    if state['winner']:
        if state['winner'] == '引き分け':
            st.header("🤝 両者行動不能により引き分け！")
        elif state['winner'] == role:
            st.header("🎉 勝利！！！")
            st.balloons()
        else:
            st.header("💀 敗北...")
            
        # 通算戦績・戦績履歴のグローバル書き込み処理（1度だけ実行）
        if state['turn'] != st.session_state.get("last_counted_turn", 0):
            global_users[my_name]["matches"] += 1
            if state['winner'] == role:
                global_users[my_name]["wins"] += 1
                global_users[my_name]["history"].insert(0, {"opp": opp_display_name, "result": "勝ち"})
            elif state['winner'] == opp_role:
                global_users[my_name]["losses"] += 1
                global_users[my_name]["history"].insert(0, {"opp": opp_display_name, "result": "負け"})
            else:
                global_users[my_name]["history"].insert(0, {"opp": opp_display_name, "result": "引き分け"})
                
            save_global_data() # ファイルに即時保存
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
            save_global_data()
            st.rerun()
        st.stop()

    # ✨ 改善点：バトルフィールドのすぐ下に行動コマンド入力を配置
    if state['choices'][role] is None:
        if not state['names'][opp_role]:
            st.warning("⏳ 対戦相手が参加するまで行動を選択できません。")
            
            # 土台コードと同じ、裏で相手の入室を待つための自動センサー
            @st.fragment
            def wait_for_player2():
                time.sleep(1)
                st.rerun()
            wait_for_player2()
            st.stop()
            
        st.subheader("👇 次の手を選んでください（相手には見えません）")
        available_actions = [a for a in actions if a not in state['banned'][role] and action_cost[a] <= state['power'][role]]
        
        if not available_actions:
            state['choices'][role] = "行動不能"
            save_global_data()
            st.rerun()
        else:
            cols = st.columns(len(available_actions))
            for idx, act in enumerate(available_actions):
                with cols[idx]:
                    cost_label = f" ({action_cost[act]})" if action_cost[act] > 0 else ""
                    if st.button(f"{act}{cost_label}", key=f"btn_{act}", use_container_width=True):
                        state['choices'][role] = act
                        save_global_data()
                        st.rerun()
    else:
        st.info(f"あなたは「{state['choices'][role]}」を選択済みです。")
        st.warning("⏳ 相手の入力を待っています...（自動更新中）")
        
        # 💥 修正点：土台コードに書かれていた「自動更新センサー（裏でループを回して相手の手を待つ構造）」を完全に復元
        @st.fragment
        def wait_for_opponent():
            while True:
                if room_name not in global_rooms:
                    break
                if global_rooms[room_name]['choices'][opp_role]:
                    break
                time.sleep(1)
                st.rerun()
        wait_for_opponent()

    # ⚖️ 両者が揃ったら即時ジャッジ（メインループ上で確実に検知し、進行バグを解消）
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
            
        turn_log = f"【ターン {state['turn']}】 {state['names']['Player 1']}: {action1} vs {state['names']['Player 2']}: {action2}"
        
        if action1 == '封印' and action2 not in state['banned']['Player 2'] and action2 != "行動不能":
            state['banned']['Player 2'].append(action2)
            turn_log += f" ｜ 🔒 P1がP2の「{action2}」を封印！"
        if action2 == '封印' and action1 not in state['banned']['Player 1'] and action1 != "行動不能":
            state['banned']['Player 1'].append(action1)
            turn_log += f" ｜ 🔒 P2がP1「{action1}」を封印！"
            
        round_winner = None
        if action1 == "行動不能" and action2 == "行動不能": round_winner = '引き分け'
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
            winner_name = state['names'][round_winner] if round_winner != '引き分け' else '引き分け'
            turn_log += f" 🏆 {winner_name} の勝利！"
        
        state['log'].insert(0, turn_log)
        
        state['choices']['Player 1'] = None
        state['choices']['Player 2'] = None
        if not state['winner']:
            state['turn'] += 1
        save_global_data()
        st.rerun()

    # ✨ 改善点：行動コマンド入力の下に部屋内チャットを配置
    st.subheader("💬 部屋内チャット")
    chat_box = st.container(height=180, border=True)
    with chat_box:
        for msg in state['chat']:
            st.write(msg)
            
    # チャット送信（Enterキー送信対応・入力欄自動クリア）
    with st.form(key="chat_form", clear_on_submit=True):
        chat_input = st.text_input("メッセージを入力:", placeholder="対戦よろしくお願いします！ (Enterで送信)")
        submit_chat = st.form_submit_button("送信")
        if submit_chat and chat_input.strip():
            timestamp = datetime.now().strftime('%H:%M')
            state['chat'].append(f"💬 [{timestamp}] {my_display_name}: {chat_input.strip()}")
            save_global_data()
            st.rerun()

    # 📜 履歴の表示
    st.divider()
    st.subheader("📜 対戦履歴")
    for log in state['log']: 
        st.write(log)


# ==========================================
# 👤 マイページ ページ
# ==========================================
elif page == "👤 マイページ":
    st.title("👤 マイページ")
    
    st.subheader("ユーザープロフィール")
    col_name, col_btn = st.columns(2)
    with col_name:
        new_nick = st.text_input("ニックネーム変更:", value=my_name)
    with col_btn:
        st.write("  ") 
        st.write("  ")
        if st.button("変更"):
            new_nick = new_nick.strip()
            if not new_nick:
                st.error("空欄にはできません。")
            elif new_nick in global_users and new_nick != my_name:
                st.error("その名前は既に使用されています。")
            else:
                global_users[new_nick] = global_users.pop(my_name)
                save_global_data()
                st.session_state.logged_in_user = new_nick
                st.success("ニックネームを変更しました！")
                time.sleep(1)
                st.rerun()
                
    st.divider()
    
    wins = u_data.get("wins", 0)
    losses = u_data.get("losses", 0)
    matches = u_data.get("matches", 0)
    win_rate = round((wins / matches * 100), 1) if matches > 0 else 0.0
    
    st.write("### 📊 あなたの戦績")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("総対戦回数", f"{matches} 回")
    c2.metric("勝利数", f"{wins} 勝")
    c3.metric("敗北数", f"{losses} 敗")
    c4.metric("勝率", f"{win_rate} %")
    
    st.write("### 👑 獲得した王冠")
    cr1, cr2, cr3 = st.columns(3)
    crowns_data = u_data.get("crowns", {"gold": 0, "silver": 0, "bronze": 0})
    cr1.markdown(f"🥇 **金の王冠 (1位)**: {crowns_data.get('gold', 0)} 個")
    cr2.markdown(f"🥈 **銀の王冠 (2位)**: {crowns_data.get('silver', 0)} 個")
    cr3.markdown(f"🥉 **銅の王冠 (3位)**: {crowns_data.get('bronze', 0)} 個")
    
    st.divider()
    
    st.write("### 📜 過去の対戦履歴一覧")
    history_list = u_data.get("history", [])
    if not history_list:
        st.info("まだ対戦履歴はありません。")
    else:
        for idx, h in enumerate(history_list):
            st.write(f"{idx+1}. 対戦相手: **{h.get('opp', '不明')}** ｜ 結果: **{h.get('result', '不明')}**")


# ==========================================
# 🏆 ランキング ページ
# ==========================================
elif page == "🏆 週間ランキング":
    st.title("🏆 週間ランキング (Top 10)")
    st.caption("※毎週の勝利数に基づいて集計されます（リアルタイムシミュレーション）")
    
    # 💥 修正点：エラーを完全に防ぐ型安全な関数からランキング情報を取得
    ranked_list = get_ranked_players()
    
    # ✨ 改善点：トップ10の上に「あなたの現在の順位」を常に最新状態で表示
    my_rank = "圏外"
    my_wins = u_data.get("wins", 0)
    for rank, p_name, _ in ranked_list:
        if p_name == my_name:
            my_rank = f"{rank}位"
            break
            
    st.info(f"💡 あなたの現在の順位: **{my_rank}** (現在の勝利数: **{my_wins}勝**)")
    st.divider()
    
    if my_name == "admin":
        if st.button("⚙️ [管理者] 現在の上位3名に今週の王冠を確定付与する"):
            for rank, p_name, _ in ranked_list:
                if 'crowns' not in global_users[p_name]:
                    global_users[p_name]['crowns'] = {"gold": 0, "silver": 0, "bronze": 0}
                
                if rank == 1: global_users[p_name]["crowns"]["gold"] += 1
                elif rank == 2: global_users[p_name]["crowns"]["silver"] += 1
                elif rank == 3: global_users[p_name]["crowns"]["bronze"] += 1
            save_global_data() # 王冠付与をファイルに即時保存
            st.success("上位者のデータへ直接王冠を付与しました！マイページにすぐ反映されます。")
            time.sleep(1)
            st.rerun()

    if not ranked_list:
        st.info("現在データがありません。")
    else:
        # 上位10名のみをピックアップして綺麗に書き出し（(同率含む)の文言は非表示）
        for rank, p_name, p_info in ranked_list[:10]:
            rank_icon = "👑 " if rank <= 3 else "👤 "
            if rank == 1: rank_label = "🥇 1位"
            elif rank == 2: rank_label = "🥈 2位"
            elif rank == 3: rank_label = "🥉 3位"
            else: rank_label = f"{rank}位"
            
            p_crowns = p_info.get("crowns", {"gold": 0, "silver": 0, "bronze": 0})
            st.markdown(f"### {rank_label} : {rank_icon}{p_name}")
            st.write(f"🔥 **勝利数**: {p_info.get('wins', 0)}勝 ｜ 🎮 **総対戦数**: {p_info.get('matches', 0)}回")
            st.write(f"👑 **所持王冠**: 金 {p_crowns.get('gold', 0)} / 銀 {p_crowns.get('silver', 0)} / 銅 {p_crowns.get('bronze', 0)}")
            st.divider()


# ==========================================
# 📩 お問い合わせ ページ
# ==========================================
elif page == "📩 お問い合わせ":
    st.title("📩 お問い合わせ窓口")
    st.info("⚠️ 開発者より：不具合の報告やご意見ありがとうございます。現在、謝罪ならびに対応に少々お時間をいただく場合がございます。あらかじめご了承ください。")
    
    with st.form("report_form", clear_on_submit=True):
        st.write("### フォーム入力")
        st.text_input("あなたのニックネーム:", value=my_name, disabled=True)
        
        rep_category = st.selectbox("問い合わせの種類:", ["バグ・不具合報告", "ゲームバランスへの意見", "その他"])
        rep_detail = st.text_area("問い合わせの詳細（例：〇〇のボタンが反応しない、など）:", placeholder="具体的な内容をご記入ください")
        
        submitted = st.form_submit_button("送信する")
        if submitted:
            if not rep_detail.strip():
                st.error("詳細が入力されていません。")
            else:
                global_reports.append({
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "user": my_name,
                    "category": rep_category,
                    "detail": rep_detail.strip()
                })
                save_global_data() # お問い合わせを即時保存
                st.success("📩 お問い合わせ内容を送信しました。ありがとうございました！")


# ==========================================
# 🛠️ 管理者専用ページ (adminでのみ表示)
# ==========================================
elif page == "🛠️ 管理者ダッシュボード" and my_name == "admin":
    st.title("🛠️ 管理者専用ログ確認画面")
    st.write("一般ユーザーにはこのタブは見えません。届いた問い合わせ（メール）をここで確認できます。")
    
    if not global_reports:
        st.info("現在届いているお問い合わせはありません。")
    else:
        for idx, rep in enumerate(reversed(global_reports), 1):
            with st.expander(f"✉️ [{rep['time']}] {rep['user']} さんからの届出 - {rep['category']}"):
                st.write(f"**送信者:** {rep['user']}")
                st.write(f"**カテゴリ:** {rep['category']}")
                st.write(f"**詳細内容:**")
                st.info(rep['detail'])
