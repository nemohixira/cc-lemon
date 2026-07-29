import streamlit as st
import time
import uuid
import datetime

# ページ基本設定
st.set_page_config(page_title="CCレモンオンライン", layout="wide")

# ==========================================
# 1. グローバルデータの初期化 (全ユーザーで共有)
# ==========================================
if "global_rooms" not in st.cache_resource:
    st.cache_resource.global_rooms = {}

if "global_leaderboard" not in st.cache_resource:
    # 初期データとしてモック（偽データ）を2つ入れておきます（ランキングの確認用）
    st.cache_resource.global_leaderboard = {
        "mock_id_1": {"name": "タロウ", "wins": 8, "losses": 2, "total": 10, "history": []},
        "mock_id_2": {"name": "ハナコ", "wins": 5, "losses": 5, "total": 10, "history": []},
    }

rooms = st.cache_resource.global_rooms
leaderboard = st.cache_resource.global_leaderboard

# ==========================================
# 2. 個人のセッション初期化 (アクセスしたブラウザごと)
# ==========================================
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.my_room = None
    st.session_state.chosen_action = None
    st.session_state.game_logged = False  # 2重に戦績が記録されるのを防ぐフラグ

uid = st.session_state.user_id

# データベースにユーザーがいなければ初期登録
if uid not in leaderboard:
    leaderboard[uid] = {
        "name": f"プレイヤー_{uid[:4]}",
        "wins": 0,
        "losses": 0,
        "total": 0,
        "history": []
    }

# ==========================================
# 3. サイドバーナビゲーション (ページ切り替え)
# ==========================================
st.sidebar.title("メニュー")
st.sidebar.write(f"ログイン中: **{leaderboard[uid]['name']}**")
page = st.sidebar.radio("ページを選択", ["ゲームプレイ", "マイページ", "ランキング"])

# ==========================================
# 【ページA】マイページ
# ==========================================
if page == "マイページ":
    st.title("👤 マイページ")
    
    # ニックネームの確認と変更
    current_name = leaderboard[uid]["name"]
    st.subheader(f"現在のニックネーム: {current_name}")
    
    # 横並びで変更フォームを配置
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        new_name = st.text_input("新しいニックネーム（10文字以内）", value=current_name, max_chars=10, label_visibility="collapsed")
    with col_btn:
        if st.button("変更を確定", use_container_width=True):
            if new_name.strip():
                leaderboard[uid]["name"] = new_name.strip()
                st.success("ニックネームを変更しました！")
                st.rerun()

    st.divider()

    # 戦績表示
    stats = leaderboard[uid]
    win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("対戦回数", f"{stats['total']} 回")
    c2.metric("勝利数", f"{stats['wins']} 勝")
    c3.metric("敗北数", f"{stats['losses']} 敗")
    c4.metric("勝率", f"{win_rate:.1f} %")

    st.divider()

    # 新しい順に対戦履歴を表示
    st.subheader("⚔️ 最新の対戦履歴")
    if stats["history"]:
        for h in reversed(stats["history"]):
            res_icon = "🟢【勝利】" if h["result"] == "WIN" else "🔴【敗北】"
            st.write(f"{res_icon} vs **{h['opponent']}** ({h['time']})")
    else:
        st.info("対戦履歴はまだありません。試合を行うとここに記録されます。")

# ==========================================
# 【ページB】ランキング
# ==========================================
elif page == "ランキング":
    st.title("🏆 勝率ランキング")
    st.write("対戦回数が1回以上のプレイヤーを、勝率が高い順に表示しています。")
    
    ranking_list = []
    for u_id, data in leaderboard.items():
        w = data["wins"]
        t = data["total"]
        wr = (w / t * 100) if t > 0 else 0.0
        # 1回以上対戦している人のみランキングに乗せる（初期モックは表示用として含む）
        if t > 0 or u_id.startswith("mock_"):
            ranking_list.append({
                "name": data["name"],
                "win_rate": wr,
                "total": t,
                "wins": w
            })
    
    # 勝率 -> 対戦回数 の順で降順ソート
    ranking_list = sorted(ranking_list, key=lambda x: (x["win_rate"], x["total"]), reverse=True)
    
    if ranking_list:
        for i, rank in enumerate(ranking_list, 1):
            # 上位3名にはメダルをつける
            medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else f"第 {i} 位: "
            st.subheader(f"{medal} **{rank['name']}**")
            st.write(f"勝率: **{rank['win_rate']:.1f}%** | 勝利数: {rank['wins']}勝 | 総対戦数: {rank['total']}回")
            st.write("---")
    else:
        st.info("まだ対戦データがありません。")

# ==========================================
# 【ページC】ゲームプレイ（メインロジック）
# ==========================================
elif page == "ゲームプレイ":
    st.title("🎮 CCレモンゲーム オンライン")
    
    # 部屋に入っていない場合
    if st.session_state.my_room is None:
        st.subheader("部屋の作成 または 入室")
        room_id_input = st.text_input("部屋ID（半角英数字など自由な文字列）を入力してください:")
        
        if st.button("入室する / 部屋を作る"):
            if room_id_input.strip():
                rid = room_id_input.strip()
                st.session_state.my_room = rid
                st.session_state.game_logged = False
                
                # 部屋が存在しない場合は新規作成（自分がP1）
                if rid not in rooms:
                    rooms[rid] = {
                        "p1_id": uid, "p1_name": leaderboard[uid]["name"], "p1_action": None, "p1_charge": 0,
                        "p2_id": None, "p2_name": None, "p2_action": None, "p2_charge": 0,
                        "chat": [f"📢 プレイヤー {leaderboard[uid]['name']} が部屋を作成しました。"],
                        "turn": 1, "winner": None
                    }
                # 部屋が存在し、P2が空いているなら参加（自分がP2）
                elif rooms[rid]["p1_id"] != uid and rooms[rid]["p2_id"] is None:
                    rooms[rid]["p2_id"] = uid
                    rooms[rid]["p2_name"] = leaderboard[uid]["name"]
                    rooms[rid]["chat"].append(f"📢 プレイヤー {leaderboard[uid]['name']} が入室しました。対戦を始められます！")
                
                st.rerun()
    
    # 部屋に入っている場合
    else:
        rid = st.session_state.my_room
        
        # 部屋データが消えていた場合のセーフティ
        if rid not in rooms:
            st.error("部屋のデータが見つかりません。")
            if st.button("ロビーに戻る"):
                st.session_state.my_room = None
                st.rerun()
            st.stop()
            
        room = rooms[rid]
        
        # 自分がP1かP2かを判定
        is_p1 = (room["p1_id"] == uid)
        my_role = "p1" if is_p1 else "p2"
        opp_role = "p2" if is_p1 else "p1"
        
        # 画面を2分割（左：ゲーム画面、右：チャット欄）
        col_game, col_chat = st.columns([2, 1])
        
        # --- 左側：ゲームメイン画面 ---
        with col_game:
            st.subheader(f"部屋ID: {rid} (ターン {room['turn']})")
            
            # 相手の入室待ち画面
            if room["p2_id"] is None:
                st.warning("⏳ 対戦相手の入室を待っています...")
                st.write("友達にこの部屋IDを教えて参加してもらってください。")
                if st.button("部屋を解散して戻る"):
                    del rooms[rid]
                    st.session_state.my_room = None
                    st.rerun()
                
                time.sleep(2)
                st.rerun()
            
            # 対戦相手情報
            opp_name = room[f"{opp_role}_name"]
            my_charge = room[f"{my_role}_charge"]
            opp_charge = room[f"{opp_role}_charge"]
            
            st.write(f"🤝 対戦相手: **{opp_name}**")
            
            # ステータス表示
            c_me, c_opp = st.columns(2)
            c_me.metric("あなたのチャージ数", f"{my_charge} 個")
            c_opp.metric(f"{opp_name} のチャージ数", f"{opp_charge} 個")
            
            st.divider()
            
            # 勝敗が決まっていない場合、行動選択
            if room["winner"] is None:
                # 自分がすでに行動を選択しているかチェック
                if room[f"{my_role}_action"] is None:
                    st.write("### 🫵 あなたの手を選んでください:")
                    
                    # チャージがないと攻撃系は選べないルール例
                    btn_charge = st.button("🍋 CCレモン (タメ)")
                    btn_guard = st.button("🛡️ ガード")
                    btn_attack = st.button("⚡ コウゲキ (1チャージ消費)", disabled=(my_charge < 1))
                    btn_laser = st.button("☄️ レーザー (2チャージ消費)", disabled=(my_charge < 2))
                    
                    if btn_charge: room[f"{my_role}_action"] = "タメ"; st.rerun()
                    if btn_guard: room[f"{my_role}_action"] = "ガード"; st.rerun()
                    if btn_attack: room[f"{my_role}_action"] = "コウゲキ"; st.rerun()
                    if btn_laser: room[f"{my_role}_action"] = "レーザー"; st.rerun()
                else:
                    st.info(f"⏳ あなたは「{room[f'{my_role}_action']}」を選択しました。相手の入力を待っています...")
                    
                    # 両者が選択し終えたか確認
                    if room[f"{opp_role}_action"] is not None:
                        # --- 勝敗・ターン処理ロジック ---
                        p1_act = room["p1_action"]
                        p2_act = room["p2_action"]
                        
                        # チャージの増減を仮適用
                        if p1_act == "タメ": room["p1_charge"] += 1
                        if p1_act == "コウゲキ": room["p1_charge"] -= 1
                        if p1_act == "レーザー": room["p1_charge"] -= 2
                        
                        if p2_act == "タメ": room["p2_charge"] += 1
                        if p2_act == "コウゲキ": room["p2_charge"] -= 1
                        if p2_act == "レーザー": room["p2_charge"] -= 2
                        
                        # システムログに手の結果を書き込み
                        room["chat"].append(f"🎬 ターン {room['turn']}: {room['p1_name']}={p1_act} vs {room['p2_name']}={p2_act}")
                        
                        # 判定
                        p1_lose = False
                        p2_lose = False
                        
                        # レーザーはガード不能、レーザー同士は相殺、コウゲキには勝つ
                        if p1_act == "レーザー" and p2_act != "レーザー": p2_lose = True
                        if p2_act == "レーザー" and p1_act != "レーザー": p1_lose = True
                        
                        # 通常攻撃の判定
                        if p1_act == "コウゲキ" and p2_act == "タメ": p2_lose = True
                        if p2_act == "コウゲキ" and p1_act == "タメ": p1_lose = True
                        
                        # 結果の適用
