"""页面选择器集中定义，便于后续二次开发替换。"""

CONVERSATION_ITEM_SELECTOR = '[class*="item-fWZowv"]'
CONVERSATION_NAME_SELECTOR = '[class*="header-name"]'
CONVERSATION_LAST_MESSAGE_SELECTOR = '[class*="item-content"]'
CONVERSATION_TIME_SELECTOR = '[class*="item-time"], [class*="time"]'

LOGIN_BUTTON_SELECTOR = '[class*="login"], [class*="Login"], button:has-text("登录")'
USER_AVATAR_SELECTOR = (
    '[class*="avatar"], [class*="Avatar"], '
    '[class*="user-info"], [class*="header-user"]'
)

CHAT_INPUT_SELECTOR = 'div[contenteditable="true"][class*="chat-input"]'
CHAT_SEND_BUTTON_SELECTOR = 'button[class*="chat-btn"]'
CHAT_PANEL_SELECTOR = '[class*="panel"], [class*="detail"], [class*="chat-main"]'
CHAT_LIST_CONTAINER_SELECTOR = '[class*="list-"][class*="-UuDnnd"]'
CHAT_FALLBACK_CONTAINER_SELECTOR = '[class*="chat-content"]'
