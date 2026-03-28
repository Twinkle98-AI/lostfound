import streamlit as st
from datetime import date
from backend import (
    init_db, register_user, login_user,
    create_item, get_all_items, get_item_by_id, get_user_items,
    mark_item_resolved, delete_item,
    send_message, get_conversations, get_messages_between, get_unread_message_count,
    create_notification, get_notifications, get_unread_notification_count,
    mark_notifications_read, upload_image,
)

# ─── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Lost & Found",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
.item-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.badge-lost  { background:#fee2e2; color:#dc2626; padding:3px 10px; border-radius:20px; font-size:13px; font-weight:600; }
.badge-found { background:#dcfce7; color:#16a34a; padding:3px 10px; border-radius:20px; font-size:13px; font-weight:600; }
.notif-card  { background:#e0f2fe; padding:10px 14px; border-radius:10px; margin-bottom:8px; }
.msg-me      { background:#dbeafe; border-radius:12px 12px 2px 12px; padding:8px 12px; margin:4px 0; text-align:right; }
.msg-them    { background:#f1f5f9; border-radius:12px 12px 12px 2px; padding:8px 12px; margin:4px 0; }
</style>
""", unsafe_allow_html=True)

# ─── Init ────────────────────────────────────────────────────────
init_db()

# ─── Session defaults ───────────────────────────────────────────
for k, v in {
    "user": None,
    "page": "Home",
    "view_item": None,
    "chat_partner": None,
    "show_notifications": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════
#  AUTH PAGES
# ════════════════════════════════════════════════════════════════

def page_login():
    st.title("🔍 Lost & Found — Sign In")
    col, _ = st.columns([1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            username = st.text_input("Username", key="li_user")
            password = st.text_input("Password", type="password", key="li_pass")
            if st.button("Login", use_container_width=True):
                user = login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

        with tab2:
            new_user  = st.text_input("Username",  key="reg_user")
            new_email = st.text_input("Email",     key="reg_email")
            new_pass  = st.text_input("Password",  type="password", key="reg_pass")
            if st.button("Register", use_container_width=True):
                ok, msg = register_user(new_user, new_pass, new_email)
                if ok:
                    st.success(msg + " Please log in.")
                else:
                    st.error(msg)


# ════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════

def sidebar():
    user = st.session_state.user
    notif_count   = get_unread_notification_count(user["id"])
    message_count = get_unread_message_count(user["id"])

    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.divider()

        pages = ["Home", "Browse", "Post Item", "My Items", "Messages", "Profile"]
        for p in pages:
            label = p
            if p == "Messages"     and message_count:  label = f"Messages 💬 ({message_count})"
            if st.button(label, use_container_width=True, key=f"nav_{p}"):
                st.session_state.page      = p
                st.session_state.view_item = None
                st.rerun()

        st.divider()
        bell_label = f"🔔 Notifications ({notif_count})" if notif_count else "🔔 Notifications"
        if st.button(bell_label, use_container_width=True):
            st.session_state.show_notifications = not st.session_state.show_notifications
            if st.session_state.show_notifications:
                mark_notifications_read(user["id"])
            st.rerun()

        if st.button("Logout", use_container_width=True):
            for k in ["user", "page", "view_item", "chat_partner", "show_notifications"]:
                st.session_state[k] = None if k == "user" else (False if k == "show_notifications" else None)
            st.rerun()

        # ── STEP 3: Notification panel ──────────────────────────
        if st.session_state.show_notifications:
            st.divider()
            st.subheader("🔔 Notifications")
            notif_list = get_notifications(user["id"])
            if not notif_list:
                st.info("No notifications yet.")
            for n in notif_list:
                icon = "📩" if n["type"] == "message" else "🙋" if n["type"] == "help" else "ℹ️"
                st.markdown(f"""
                <div class='notif-card'>
                {icon} <b>{n['title']}</b><br>
                <small>{n['message']}</small><br>
                <small style='color:#64748b'>{n['created_at']}</small>
                </div>
                """, unsafe_allow_html=True)
                if n["item_id"]:
                    if st.button(f"🔍 View Item", key=f"notif_view_{n['id']}"):
                        st.session_state.view_item = n["item_id"]
                        st.session_state.page = "Browse"
                        st.session_state.show_notifications = False
                        st.rerun()


# ════════════════════════════════════════════════════════════════
#  HOME
# ════════════════════════════════════════════════════════════════

def page_home():
    st.title("🏠 Welcome to Lost & Found")
    st.markdown("Helping people reconnect with their belongings.")

    col1, col2, col3 = st.columns(3)
    all_items  = get_all_items()
    lost_items = [i for i in all_items if i["type"] == "Lost"]
    found_items = [i for i in all_items if i["type"] == "Found"]

    col1.metric("📋 Total Open Items", len(all_items))
    col2.metric("🔴 Lost",  len(lost_items))
    col3.metric("🟢 Found", len(found_items))

    st.divider()
    st.subheader("🆕 Recent Items")
    for item in all_items[:6]:
        badge = f"<span class='badge-lost'>Lost</span>" if item["type"] == "Lost" else f"<span class='badge-found'>Found</span>"
        st.markdown(f"""
        <div class='item-card'>
        {badge} &nbsp; <b>{item['title']}</b><br>
        📍 {item['location']} &nbsp;|&nbsp; 🗓 {item['date']}<br>
        <small style='color:#64748b'>Posted by {item['username']}</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Details", key=f"home_view_{item['id']}"):
            st.session_state.view_item = item["id"]
            st.session_state.page = "Browse"
            st.rerun()


# ════════════════════════════════════════════════════════════════
#  STEP 1 + 2: BROWSE PAGE
# ════════════════════════════════════════════════════════════════

def page_browse():
    # ── STEP 4: Item detail view ─────────────────────────────────
    if st.session_state.view_item:
        page_item_details(st.session_state.view_item)
        return

    st.title("🔍 Browse Lost & Found Items")
    user = st.session_state.user

    # ── STEP 2: Filters ─────────────────────────────────────────
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_type = st.selectbox("Filter by Type", ["All", "Lost", "Found"])
    with col2:
        search = st.text_input("🔎 Search by title, description, or location", "")

    items = get_all_items(filter_type, search)

    if not items:
        st.info("No items match your search.")
        return

    for item in items:
        is_own = item["user_id"] == user["id"]
        badge  = "<span class='badge-lost'>Lost</span>" if item["type"] == "Lost" else "<span class='badge-found'>Found</span>"

        st.markdown(f"""
        <div class='item-card'>
        {badge} &nbsp; <b>{item['title']}</b><br>
        📍 {item['location']} &nbsp;|&nbsp; 🗓 {item['date']}<br>
        📝 {item['description']}<br>
        <small style='color:#64748b'>Posted by <b>{item['username']}</b> on {item['created_at'][:10]}</small>
        </div>
        """, unsafe_allow_html=True)

        # Show image if present
        if item.get("image_url"):
            st.image(item["image_url"], width=200)

        if is_own:
            st.caption("✅ This is your item.")
        else:
            # ── STEP 1: Action buttons ───────────────────────────
            bcol1, bcol2, bcol3 = st.columns(3)
            with bcol1:
                if st.button(f"💬 Contact Owner", key=f"contact_{item['id']}"):
                    send_message(
                        user["id"],
                        item["user_id"],
                        f"Hi, I saw your {item['type'].lower()} item '{item['title']}'. I can help!"
                    )
                    create_notification(
                        item["user_id"],
                        "message",
                        "New Help Message",
                        f"{user['username']} wants to help with your item '{item['title']}'!",
                        item["id"]
                    )
                    st.success("✅ Message sent to owner!")

            with bcol2:
                btn_label = "🙋 I Found This!" if item["type"] == "Lost" else "🙋 I Lost This!"
                if st.button(btn_label, key=f"help_{item['id']}"):
                    create_notification(
                        item["user_id"],
                        "help",
                        "Someone Found Your Item!" if item["type"] == "Lost" else "Someone Claimed Your Found Item!",
                        f"{user['username']} thinks they {'found' if item['type'] == 'Lost' else 'lost'} your item '{item['title']}'!",
                        item["id"]
                    )
                    st.success("✅ Owner has been notified!")

            with bcol3:
                if st.button(f"📄 View Details", key=f"details_{item['id']}"):
                    st.session_state.view_item = item["id"]
                    st.rerun()

        st.markdown("---")


# ════════════════════════════════════════════════════════════════
#  STEP 4: ITEM DETAILS PAGE
# ════════════════════════════════════════════════════════════════

def page_item_details(item_id):
    item = get_item_by_id(item_id)
    user = st.session_state.user

    if not item:
        st.error("Item not found.")
        if st.button("← Back to Browse"):
            st.session_state.view_item = None
            st.rerun()
        return

    if st.button("← Back to Browse"):
        st.session_state.view_item = None
        st.rerun()

    st.title("📄 Item Details")
    badge = "<span class='badge-lost'>Lost</span>" if item["type"] == "Lost" else "<span class='badge-found'>Found</span>"
    st.markdown(f"""
    <div class='item-card'>
    {badge} &nbsp; <b style='font-size:20px'>{item['title']}</b><br><br>
    📍 <b>Location:</b> {item['location']}<br>
    🗓 <b>Date:</b> {item['date']}<br>
    📝 <b>Description:</b> {item['description']}<br><br>
    <small style='color:#64748b'>Posted by <b>{item['username']}</b> on {item['created_at'][:10]}</small>
    </div>
    """, unsafe_allow_html=True)

    if item.get("image_url"):
        st.image(item["image_url"], caption="Item Photo", use_container_width=True)

    is_own = item["user_id"] == user["id"]

    if is_own:
        st.info("This is your item.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Mark as Resolved"):
                mark_item_resolved(item_id)
                st.success("Marked as resolved!")
                st.session_state.view_item = None
                st.rerun()
        with col2:
            if st.button("🗑️ Delete Item"):
                delete_item(item_id)
                st.success("Item deleted.")
                st.session_state.view_item = None
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💬 Contact Owner", use_container_width=True):
                send_message(
                    user["id"],
                    item["user_id"],
                    f"Hi, I can help with your {item['type'].lower()} item '{item['title']}'!"
                )
                create_notification(
                    item["user_id"],
                    "message",
                    "New Help Message",
                    f"{user['username']} can help with your item '{item['title']}'!",
                    item["id"]
                )
                st.success("✅ Message sent to owner!")
        with col2:
            btn_label = "🙋 I Found This!" if item["type"] == "Lost" else "🙋 I Lost This!"
            if st.button(btn_label, use_container_width=True):
                create_notification(
                    item["user_id"],
                    "help",
                    "Someone Found Your Item!" if item["type"] == "Lost" else "Someone Claimed Your Found Item!",
                    f"{user['username']} thinks they {'found' if item['type'] == 'Lost' else 'lost'} your '{item['title']}'!",
                    item["id"]
                )
                st.success("✅ Owner has been notified!")


# ════════════════════════════════════════════════════════════════
#  POST ITEM
# ════════════════════════════════════════════════════════════════

def page_post_item():
    st.title("📝 Post a Lost or Found Item")
    user = st.session_state.user

    with st.form("post_form"):
        title       = st.text_input("Item Title *")
        item_type   = st.selectbox("Type *", ["Lost", "Found"])
        location    = st.text_input("Location")
        item_date   = st.date_input("Date", value=date.today())
        description = st.text_area("Description")
        photo       = st.file_uploader("Upload Photo (optional)", type=["jpg", "jpeg", "png", "webp"])
        submitted   = st.form_submit_button("Post Item", use_container_width=True)

    if submitted:
        if not title:
            st.error("Title is required.")
            return
        image_url = ""
        if photo:
            with st.spinner("Uploading image..."):
                image_url = upload_image(photo.read(), filename=f"item_{user['id']}_{title}")
        create_item(user["id"], title, item_type, location, str(item_date), description, image_url)
        st.success(f"✅ '{title}' posted as {item_type}!")
        st.session_state.page = "Browse"
        st.rerun()


# ════════════════════════════════════════════════════════════════
#  MY ITEMS
# ════════════════════════════════════════════════════════════════

def page_my_items():
    st.title("📦 My Items")
    user  = st.session_state.user
    items = get_user_items(user["id"])

    if not items:
        st.info("You haven't posted any items yet.")
        if st.button("Post an Item"):
            st.session_state.page = "Post Item"
            st.rerun()
        return

    for item in items:
        badge  = "<span class='badge-lost'>Lost</span>" if item["type"] == "Lost" else "<span class='badge-found'>Found</span>"
        status = "🟢 Open" if item["status"] == "open" else "✅ Resolved"
        st.markdown(f"""
        <div class='item-card'>
        {badge} &nbsp; <b>{item['title']}</b> &nbsp; — {status}<br>
        📍 {item['location']} &nbsp;|&nbsp; 🗓 {item['date']}<br>
        📝 {item['description']}
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if item["status"] == "open" and st.button("✅ Resolve", key=f"res_{item['id']}"):
                mark_item_resolved(item["id"])
                st.success("Marked resolved.")
                st.rerun()
        with col2:
            if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                delete_item(item["id"])
                st.success("Deleted.")
                st.rerun()
        st.markdown("---")


# ════════════════════════════════════════════════════════════════
#  MESSAGES
# ════════════════════════════════════════════════════════════════

def page_messages():
    st.title("💬 Messages")
    user = st.session_state.user
    conversations = get_conversations(user["id"])

    if not conversations and not st.session_state.chat_partner:
        st.info("No conversations yet. Contact an item owner from the Browse page!")
        return

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Conversations")
        for conv in conversations:
            if st.button(f"👤 {conv['partner_name']}", key=f"conv_{conv['partner_id']}", use_container_width=True):
                st.session_state.chat_partner = conv
                st.rerun()

    with col_right:
        partner = st.session_state.chat_partner
        if not partner:
            st.info("Select a conversation.")
            return

        st.subheader(f"Chat with {partner['partner_name']}")
        msgs = get_messages_between(user["id"], partner["partner_id"])

        chat_html = ""
        for m in msgs:
            is_me = m["sender_id"] == user["id"]
            cls   = "msg-me" if is_me else "msg-them"
            who   = "You" if is_me else m["sender_name"]
            chat_html += f"<div class='{cls}'><small><b>{who}</b></small><br>{m['content']}<br><small style='color:#94a3b8'>{m['created_at'][11:16]}</small></div>"

        st.markdown(chat_html, unsafe_allow_html=True)

        with st.form("reply_form", clear_on_submit=True):
            msg_text = st.text_input("Type a message...")
            if st.form_submit_button("Send ➤"):
                if msg_text.strip():
                    send_message(user["id"], partner["partner_id"], msg_text.strip())
                    create_notification(
                        partner["partner_id"],
                        "message",
                        "New Message",
                        f"{user['username']} sent you a message.",
                    )
                    st.rerun()


# ════════════════════════════════════════════════════════════════
#  PROFILE
# ════════════════════════════════════════════════════════════════

def page_profile():
    user  = st.session_state.user
    items = get_user_items(user["id"])
    st.title("👤 My Profile")
    st.markdown(f"""
    | Field | Value |
    |-------|-------|
    | Username | **{user['username']}** |
    | Email | {user.get('email','—')} |
    | Member since | {user.get('created_at','—')[:10]} |
    | Items posted | {len(items)} |
    """)


# ════════════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.user:
        page_login()
        return

    sidebar()

    # ── STEP 5: Connect everything ───────────────────────────────
    page = st.session_state.page

    # If a view_item is set, always show item details regardless of sub-page
    if st.session_state.view_item and page == "Browse":
        page_browse()   # internally calls page_item_details
    elif page == "Home":
        page_home()
    elif page == "Browse":
        page_browse()
    elif page == "Post Item":
        page_post_item()
    elif page == "My Items":
        page_my_items()
    elif page == "Messages":
        page_messages()
    elif page == "Profile":
        page_profile()
    else:
        page_home()


if __name__ == "__main__":
    main()
